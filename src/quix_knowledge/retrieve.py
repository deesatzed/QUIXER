"""Deterministic lexical retrieval with optional topic and role ranking."""
import re
import json
from .decisions import judge

def tokens(text):
    return set(re.findall(r'[\w]+',text.lower()))

def search(db, query, variant='baseline', role=None, role_version=None, provider=None, limit=10, context_chars=None, include_proposed=False, context_tokens=None, count_tokens=None):
    if variant not in {'baseline','topic','decision','role'}:
        raise ValueError('unknown retrieval variant')
    if limit < 0:
        raise ValueError('limit must be nonnegative')
    if context_chars is not None and context_chars < 0:
        raise ValueError('context_chars must be nonnegative')
    if context_tokens is not None and (context_tokens < 0 or count_tokens is None or context_chars is not None):
        raise ValueError('token budget requires a counter and excludes character budget')
    query_tokens = tokens(query)
    rows = db.execute("SELECT sections.*,sources.path,sources.revision,sources.status AS source_status,section_pages.page_start,section_pages.page_end FROM sections JOIN sources ON sources.id=sections.source_id LEFT JOIN section_pages ON sections.id=section_pages.section_id WHERE sources.status='current'").fetchall()
    results = []
    candidates = [dict(row, record_type='section', evidence=[], unsupported=False) for row in rows]
    warning_pages = {}
    for row in db.execute('SELECT source_id,page FROM extraction_warnings ORDER BY page'):
        warning_pages.setdefault(row['source_id'],[]).append(row['page'])
    for item in candidates:
        item['source_warning_pages'] = warning_pages.get(item['source_id'],[])
    if variant != 'baseline':
        statuses = ('accepted','proposed') if include_proposed else ('accepted',)
        entries = db.execute("SELECT g.*,s.source_id,s.start_line,s.end_line,s.generated,src.path,src.revision,src.status AS source_status,p.page_start,p.page_end FROM generated_index g JOIN sections s ON s.id=g.section_id JOIN sources src ON src.id=s.source_id LEFT JOIN section_pages p ON p.section_id=s.id WHERE src.status='current' AND g.status IN (%s)" % ','.join('?'*len(statuses)), statuses).fetchall()
        for entry in entries:
            item = dict(entry)
            item.update(record_type='generated_index',source_section_id=item.pop('section_id'),index_status=item.pop('status'),evidence=[],unsupported=False,source_warning_pages=warning_pages.get(item['source_id'],[]))
            candidates.append(item)
    for record in db.execute("SELECT * FROM records WHERE status IN ('current','proposed')").fetchall():
        item = dict(record)
        refs = db.execute('SELECT evidence.section_id,sources.status FROM evidence JOIN sections ON sections.id=evidence.section_id JOIN sources ON sources.id=sections.source_id WHERE evidence.record_id=? ORDER BY evidence.section_id',(item['id'],)).fetchall()
        evidence = [r[0] for r in refs]
        evidence_status = 'unsupported' if not refs else 'stale' if any(r[1] != 'current' for r in refs) else 'current'
        item.update(record_type='agent_record',title=item['kind'],path=None,revision=None,source_status=item['status'],evidence=evidence,unsupported=not evidence,evidence_status=evidence_status)
        candidates.append(item)
    for item in candidates:
        lexical = len(query_tokens & tokens(item['title']+' '+item['body']))
        column = 'record_id' if item['record_type'] == 'agent_record' else 'section_id'
        annotation_id = item['source_section_id'] if item['record_type'] == 'generated_index' else item['id']
        topics = [r[0] for r in db.execute(f"SELECT topic FROM topic_links WHERE {column}=? AND status='accepted'",(annotation_id,))]
        if item['record_type'] == 'generated_index':
            topics.append(item['title'])
        topic = len(query_tokens & tokens(' '.join(topics))) if variant != 'baseline' else 0
        if not lexical and not topic:
            continue
        item.update(lexical_score=lexical,topic_score=topic,topics=topics,role_score=None,role_score_status=None,role_score_method=None,role_score_model=None,decision=None)
        if variant == 'role' and role and role_version:
            annotation = db.execute(f"SELECT score,status,method,model FROM role_annotations WHERE {column}=? AND role=? AND role_version=? AND source_revision IS ? AND status IN ('accepted','proposed') ORDER BY id DESC LIMIT 1",(annotation_id,role,role_version,item['revision'])).fetchone()
            if annotation:
                item['role_score'] = annotation['score']
                item['role_score_status'] = annotation['status']
                item['role_score_method'] = annotation['method']
                item['role_score_model'] = annotation['model']
        item['score'] = lexical + topic + (0.25 * item['role_score'] if item['role_score'] is not None else 0)
        results.append(item)
    results = sorted(results,key=lambda x:(-x['score'],x['id']))[:limit]
    if variant in {'decision','role'} and provider is not None:
        for item in results:
            item['decision'] = judge(provider, {'query':query,'title':item['title'],'text':item['body'][:4000], 'text_truncated':len(item['body']) > 4000}, 'relevant')
            decision = item['decision']
            item['score'] += {'supported':0.1,'unsuitable':-0.1}.get(decision['outcome'],0)
            db.execute('INSERT INTO decision_receipts(provider,model,outcome,detail) VALUES (?,?,?,?)',(decision.get('provider','unknown'),decision.get('model'),decision['outcome'],json.dumps({'item_id':item['id'],'query':query,'reason':decision.get('reason'),'probability':decision.get('probability'),'usage':decision.get('usage'),'request_id':decision.get('request_id'),'thresholds':decision.get('thresholds')})))
        outcomes = [item['decision']['outcome'] for item in results]
        if any(outcome in ('unknown','unclear') for outcome in outcomes):
            reason = 'decision_unknown' if 'unknown' in outcomes else 'decision_unclear'
            baseline = search(db,query,variant='baseline',limit=limit)
            decisions = {item['id']:item['decision'] for item in results}
            results = baseline or results
            for item in results:
                item['decision'] = decisions.get(item['id'])
                item['fallback_reason'] = reason if baseline else reason + '_baseline_empty'
    db.commit()
    results = sorted(results,key=lambda x:(-x['score'],x['id']))
    if context_tokens is not None:
        def count_text(text):
            count = count_tokens(text)
            if isinstance(count,bool) or not isinstance(count,int) or count < 0:
                raise ValueError('token counter must return nonnegative integers')
            return count
        if count_text('') != 0:
            raise ValueError('token counter must return zero for empty text')
        remaining = context_tokens
        bounded = []
        for item in results:
            if remaining <= 0:
                break
            original = item['body']
            count = count_text(original)
            if count > remaining:
                lo, hi = 0, len(original)
                while lo < hi:
                    mid = (lo + hi + 1) // 2
                    if count_text(original[:mid]) <= remaining:
                        lo = mid
                    else:
                        hi = mid-1
                item['body'] = original[:lo]
                count = count_text(item['body'])
            item['context_token_count'] = count
            item['context_truncated'] = len(item['body']) < len(original)
            remaining -= count
            bounded.append(item)
        return bounded
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
