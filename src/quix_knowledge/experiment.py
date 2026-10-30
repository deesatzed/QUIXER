"""Reproducible comparative runs over an immutable catalog snapshot."""
from datetime import datetime, timezone
import hashlib
import json
import time

from .evaluate import evaluate
from .retrieve import search

_TABLES = ('sources', 'sections', 'section_pages', 'extraction_warnings', 'records', 'evidence', 'topic_links', 'role_annotations')
_VARIANTS = ('baseline', 'topic', 'decision', 'role')


def corpus_fingerprint(db):
    """Hash records and annotations; decision receipts are run output, not corpus."""
    digest = hashlib.sha256()
    for name in _TABLES:
        rows = [dict(row) for row in db.execute(f'SELECT * FROM {name}').fetchall()]
        encoded = sorted(json.dumps(row,sort_keys=True,ensure_ascii=False) for row in rows)
        digest.update(json.dumps([name,encoded],ensure_ascii=False).encode())
    return digest.hexdigest()


def run_experiment(db, tasks, *, provider=None, context_chars=4000, limit=10, label_provenance=None, configuration=None):
    if not tasks or limit < 0 or context_chars < 0:
        raise ValueError('tasks and nonnegative budgets are required')
    ids = [task.get('id') for task in tasks]
    if any(not isinstance(i,str) or not i for i in ids) or len(set(ids)) != len(ids):
        raise ValueError('task IDs must be nonempty and unique')
    if any(not isinstance(task.get('query'),str) or not task['query'].strip() for task in tasks):
        raise ValueError('each task needs a query')
    fingerprint = corpus_fingerprint(db)
    labels = {t['id']:t.get('labels') for t in tasks}
    variants = {}
    for variant in _VARIANTS:
        queries, results = {}, {}
        for task in tasks:
            if corpus_fingerprint(db) != fingerprint:
                raise RuntimeError('catalog changed during experiment')
            previous = db.execute('SELECT COALESCE(MAX(id),0) FROM decision_receipts').fetchone()[0]
            started = time.monotonic()
            rows = search(db, task['query'], variant=variant, role=task.get('role'), role_version=task.get('role_version'), provider=provider, limit=limit, context_chars=context_chars)
            elapsed = time.monotonic() - started
            receipts = [dict(row) for row in db.execute('SELECT * FROM decision_receipts WHERE id>? ORDER BY id',(previous,))]
            details = [json.loads(r['detail']) for r in receipts]
            costs = [(d.get('usage') or {}).get('cost') for d in details]
            cost = sum(costs) if costs and all(isinstance(x,(int,float)) and not isinstance(x,bool) for x in costs) else None
            results[task['id']] = rows
            queries[task['id']] = {'elapsed_seconds': elapsed, 'decision_calls':len(receipts), 'decision_failures':sum(r['outcome']=='unknown' for r in receipts), 'reported_cost':cost, 'returned_body_chars':sum(len(r['body']) for r in rows), 'receipts':receipts, 'results':rows}
        variants[variant] = {'metrics':evaluate(labels,results), 'queries':queries}
    if corpus_fingerprint(db) != fingerprint:
        raise RuntimeError('catalog changed during experiment')
    return {'manifest':{'created_at':datetime.now(timezone.utc).isoformat(), 'corpus_revision':fingerprint, 'tasks':tasks, 'label_provenance':label_provenance, 'provider_configured':provider is not None, 'limit':limit, 'context_chars':context_chars, 'configuration':configuration}, 'variants':variants}
