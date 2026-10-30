"""Propose source-linked topics and record bounded structure decisions."""
import json

from .decisions import assess_topic, judge
from .ingest import ingest


def index_source(db, path, provider=None, max_decisions=10):
    if max_decisions < 0:
        raise ValueError('max_decisions must be nonnegative')
    source_id = ingest(db, path)
    if source_id is None:
        return {'source_id': None, 'structure_judgment': None, 'topic_candidates': 0, 'decision_calls': 0}
    sections = db.execute('SELECT * FROM sections WHERE source_id=? ORDER BY start_line', (source_id,)).fetchall()
    result = {'source_id': source_id, 'structure_judgment': None, 'topic_candidates': 0, 'decision_calls': 0}
    if provider is not None and max_decisions:
        # A compact structure sample is not a complete document-quality assessment.
        state = {'sections': [{'title': s['title'], 'generated': bool(s['generated']), 'text': s['body'][:1000]} for s in sections[:5]], 'section_count': len(sections)}
        judgment = judge(provider, state, 'structure usable')
        result['structure_judgment'] = judgment
        result['decision_calls'] += 1
        with db:
            db.execute('INSERT INTO decision_receipts(provider,model,outcome,detail) VALUES (?,?,?,?)', (judgment.get('provider','unknown'), judgment.get('model'), judgment['outcome'], json.dumps({'source_id': source_id, 'question': 'structure usable', 'probability': judgment.get('probability'), 'usage': judgment.get('usage'), 'request_id': judgment.get('request_id'), 'thresholds': judgment.get('thresholds'), 'reason': judgment.get('reason')})))
    for section in sections:
        if section['generated'] or not section['title'].strip():
            continue
        existing = db.execute('SELECT id,method,status FROM topic_links WHERE section_id=? AND topic=? AND status != ? ORDER BY id DESC LIMIT 1', (section['id'],section['title'],'stale')).fetchone()
        if existing:
            if existing['status'] == 'proposed' and existing['method'] == 'heading' and provider is not None and result['decision_calls'] < max_decisions:
                assess_topic(db, section['id'], section['title'], provider, proposal_id=existing['id'])
                result['decision_calls'] += 1
            continue
        result['topic_candidates'] += 1
        if provider is not None and result['decision_calls'] < max_decisions:
            assess_topic(db, section['id'], section['title'], provider)
            result['decision_calls'] += 1
        else:
            with db:
                db.execute('INSERT INTO topic_links(section_id,topic,method,status) VALUES (?,?,?,?)', (section['id'], section['title'], 'heading', 'proposed'))
    return result
