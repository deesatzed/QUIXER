"""Deterministic lexical retrieval with optional topic and role ranking."""
import re
import json
from .decisions import judge

def tokens(text):
    return set(re.findall(r'[\w]+',text.lower()))

def search(db, query, variant='baseline', role=None, role_version=None, provider=None, limit=10, context_chars=None):
    if variant not in {'baseline','topic','decision','role'}:
        raise ValueError('unknown retrieval variant')
    if limit < 0:
        raise ValueError('limit must be nonnegative')
    if context_chars is not None and context_chars < 0:
        raise ValueError('context_chars must be nonnegative')
    query_tokens = tokens(query)
    rows = db.execute("SELECT sections.*,sources.path,sources.revision,sources.status AS source_status FROM sections JOIN sources ON sources.id=sections.source_id WHERE sources.status='current'").fetchall()
    results = []
    candidates = [dict(row, record_type='section', evidence=[], unsupported=False) for row in rows]
    for record in db.execute("SELECT * FROM records WHERE status IN ('current','proposed')").fetchall():
        item = dict(record)
        refs = db.execute('SELECT evidence.section_id,sources.status FROM evidence JOIN sections ON sections.id=evidence.section_id JOIN sources ON sources.id=sections.source_id WHERE evidence.record_id=? ORDER BY evidence.section_id',(item['id'],)).fetchall()
        evidence = [r[0] for r in refs]
        evidence_status = 'unsupported' if not refs else 'stale' if any(r[1] != 'current' for r in refs) else 'current'
        item.update(record_type='agent_record',title=item['kind'],path=None,revision=None,source_status=item['status'],evidence=evidence,unsupported=not evidence,evidence_status=evidence_status)
        candidates.append(item)
    for item in candidates:
        lexical = len(query_tokens & tokens(item['title']+' '+item['body']))
        column = 'section_id' if item['record_type'] == 'section' else 'record_id'
        topics = [r[0] for r in db.execute(f"SELECT topic FROM topic_links WHERE {column}=? AND status='accepted'",(item['id'],))]
        topic = len(query_tokens & tokens(' '.join(topics))) if variant != 'baseline' else 0
        if not lexical and not topic:
            continue
        item.update(lexical_score=lexical,topic_score=topic,topics=topics,role_score=None,decision=None)
        if variant == 'role' and role and role_version:
            annotation = db.execute(f"SELECT score FROM role_annotations WHERE {column}=? AND role=? AND role_version=? AND source_revision IS ? AND status IN ('accepted','proposed') ORDER BY id DESC LIMIT 1",(item['id'],role,role_version,item['revision'])).fetchone()
            if annotation:
                item['role_score'] = annotation[0]
        item['score'] = lexical + topic + (0.25 * item['role_score'] if item['role_score'] is not None else 0)
        results.append(item)
    results = sorted(results,key=lambda x:(-x['score'],x['id']))[:limit]
    if variant in {'decision','role'} and provider is not None:
        for item in results:
            item['decision'] = judge(provider, {'query':query,'title':item['title'],'text':item['body'][:4000], 'text_truncated':len(item['body']) > 4000}, 'relevant')
            decision = item['decision']
            item['score'] += {'supported':0.1,'unsuitable':-0.1}.get(decision['outcome'],0)
            db.execute('INSERT INTO decision_receipts(provider,model,outcome,detail) VALUES (?,?,?,?)',(decision.get('provider','unknown'),decision.get('model'),decision['outcome'],json.dumps({'item_id':item['id'],'query':query,'reason':decision.get('reason'),'probability':decision.get('probability'),'usage':decision.get('usage'),'request_id':decision.get('request_id'),'thresholds':decision.get('thresholds')})))
    db.commit()
    results = sorted(results,key=lambda x:(-x['score'],x['id']))
    if context_chars is not None:
        remaining = context_chars
        bounded = []
        for item in results:
            if remaining <= 0:
                break
            original = item['body']
            item['body'] = original[:remaining]
            item['context_truncated'] = len(item['body']) < len(original)
            remaining -= len(item['body'])
            bounded.append(item)
        return bounded
    return results
