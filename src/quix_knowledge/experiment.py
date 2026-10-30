"""Reproducible comparative runs over an immutable catalog snapshot."""
from datetime import datetime, timezone
import hashlib
import json
import time

from .evaluate import evaluate
from .retrieve import search

_TABLES = ('sources', 'sections', 'section_pages', 'extraction_warnings', 'generated_index', 'generated_index_reviews', 'records', 'evidence', 'topic_links', 'role_annotations')
_VARIANTS = ('baseline', 'topic', 'decision', 'role')


def corpus_fingerprint(db):
    """Hash records and annotations; decision receipts are run output, not corpus."""
    digest = hashlib.sha256()
    for name in _TABLES:
        rows = [dict(row) for row in db.execute(f'SELECT * FROM {name}').fetchall()]
        encoded = sorted(json.dumps(row,sort_keys=True,ensure_ascii=False) for row in rows)
        digest.update(json.dumps([name,encoded],ensure_ascii=False).encode())
    return digest.hexdigest()


def _indexing_receipts(db, receipt_ids):
    if receipt_ids is None:
        return None
    if len(set(receipt_ids)) != len(receipt_ids):
        raise ValueError('duplicate indexing receipt IDs')
    receipts = []
    for receipt_id in receipt_ids:
        row = db.execute('SELECT * FROM decision_receipts WHERE id=?',(receipt_id,)).fetchone()
        if row is None:
            raise ValueError('missing indexing receipt')
        receipt = dict(row)
        detail = json.loads(receipt['detail'])
        if 'source_id' in detail:
            source = db.execute('SELECT status FROM sources WHERE id=?',(detail['source_id'],)).fetchone()
        elif 'section_id' in detail:
            source = db.execute('SELECT sources.status FROM sections JOIN sources ON sections.source_id=sources.id WHERE sections.id=?',(detail['section_id'],)).fetchone()
        elif 'generated_index_id' in detail:
            source = db.execute('SELECT sources.status FROM generated_index JOIN sections ON generated_index.section_id=sections.id JOIN sources ON sections.source_id=sources.id WHERE generated_index.id=?',(detail['generated_index_id'],)).fetchone()
        else:
            raise ValueError('receipt is not an indexing decision')
        if source is None or source['status'] != 'current':
            raise ValueError('indexing receipt does not refer to a current source')
        receipts.append(receipt)
    details = [json.loads(row['detail']) for row in receipts]
    def total(key):
        values = [(d.get('usage') or {}).get(key) for d in details]
        return sum(values) if values and all(isinstance(v,(int,float)) and not isinstance(v,bool) and v >= 0 for v in values) else None
    return {'decision_calls':len(receipts),'unknown_decisions':sum(r['outcome']=='unknown' for r in receipts),'reported_cost':total('cost'),'input_tokens':total('input_tokens'),'receipts':receipts}


def run_experiment(db, tasks, *, provider=None, context_chars=4000, context_tokens=None, count_tokens=None, tokenizer_name=None, limit=10, label_provenance=None, configuration=None, include_proposed=False, indexing_receipt_ids=None):
    if not tasks or limit < 0 or (context_chars is not None and context_chars < 0):
        raise ValueError('tasks and nonnegative budgets are required')
    if context_tokens is not None and (context_chars is not None or context_tokens < 0 or count_tokens is None or not tokenizer_name):
        raise ValueError('token budget requires a named counter and excludes character budget')
    if context_tokens is None and context_chars is None:
        raise ValueError('a context budget is required')
    ids = [task.get('id') for task in tasks]
    if any(not isinstance(i,str) or not i for i in ids) or len(set(ids)) != len(ids):
        raise ValueError('task IDs must be nonempty and unique')
    if any(not isinstance(task.get('query'),str) or not task['query'].strip() for task in tasks):
        raise ValueError('each task needs a query')
    if any(t.get('labels') is not None and (not isinstance(t['labels'],list) or any(not isinstance(x,str) or not x for x in t['labels'])) for t in tasks):
        raise ValueError('labels must be null or a list of nonempty IDs')
    if any(t.get('split','unassigned') not in ('train','development','held_out','unassigned') for t in tasks):
        raise ValueError('task split must be train, development, held_out or unassigned')
    fingerprint = corpus_fingerprint(db)
    indexing = _indexing_receipts(db,indexing_receipt_ids)
    labels = {t['id']:t.get('labels') for t in tasks}
    available = {row[0] for row in db.execute("SELECT sections.id FROM sections JOIN sources ON sections.source_id=sources.id WHERE sources.status='current'")}
    available.update(row[0] for row in db.execute("SELECT id FROM records WHERE status IN ('current','proposed')"))
    available.update(row[0] for row in db.execute("SELECT generated_index.id FROM generated_index JOIN sections ON generated_index.section_id=sections.id JOIN sources ON sections.source_id=sources.id WHERE sources.status='current' AND generated_index.status IN ('accepted','proposed')"))
    missing = {task['id']:sorted(set(task['labels'])-available) for task in tasks if task.get('labels')}
    missing = {key:value for key,value in missing.items() if value}
    variants = {}
    for variant in _VARIANTS:
        queries, results = {}, {}
        for task in tasks:
            if corpus_fingerprint(db) != fingerprint:
                raise RuntimeError('catalog changed during experiment')
            previous = db.execute('SELECT COALESCE(MAX(id),0) FROM decision_receipts').fetchone()[0]
            started = time.monotonic()
            rows = search(db, task['query'], variant=variant, role=task.get('role'), role_version=task.get('role_version'), provider=provider, limit=limit, context_chars=context_chars, context_tokens=context_tokens,count_tokens=count_tokens,include_proposed=include_proposed)
            elapsed = time.monotonic() - started
            receipts = [dict(row) for row in db.execute('SELECT * FROM decision_receipts WHERE id>? ORDER BY id',(previous,))]
            details = [json.loads(r['detail']) for r in receipts]
            costs = [(d.get('usage') or {}).get('cost') for d in details]
            cost = sum(costs) if costs and all(isinstance(x,(int,float)) and not isinstance(x,bool) for x in costs) else None
            results[task['id']] = rows
            queries[task['id']] = {'elapsed_seconds': elapsed, 'decision_calls':len(receipts), 'decision_failures':sum(r['outcome']=='unknown' for r in receipts), 'reported_cost':cost, 'returned_body_chars':sum(len(r['body']) for r in rows), 'returned_body_tokens':sum(r['context_token_count'] for r in rows) if context_tokens is not None else None, 'missing_label_ids':missing.get(task['id'],[]), 'receipts':receipts, 'results':rows}
        by_split = {}
        for split in sorted({task.get('split','unassigned') for task in tasks}):
            split_ids = {task['id'] for task in tasks if task.get('split','unassigned') == split}
            by_split[split] = evaluate({key:labels[key] for key in split_ids},{key:results[key] for key in split_ids},set(missing) & split_ids)
        variants[variant] = {'metrics':evaluate(labels,results,missing), 'metrics_by_split':by_split, 'queries':queries}
    if corpus_fingerprint(db) != fingerprint:
        raise RuntimeError('catalog changed during experiment')
    return {'manifest':{'created_at':datetime.now(timezone.utc).isoformat(), 'corpus_revision':fingerprint, 'tasks':tasks, 'label_provenance':label_provenance, 'provider_configured':provider is not None, 'limit':limit, 'context_chars':context_chars, 'context_tokens':context_tokens, 'tokenizer':tokenizer_name, 'include_proposed':include_proposed, 'indexing':indexing, 'configuration':configuration}, 'variants':variants}
