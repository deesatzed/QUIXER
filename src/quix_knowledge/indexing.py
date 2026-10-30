"""Propose source-linked topics and record bounded structure decisions."""
import json
import hashlib
import re

from .decisions import assess_topic, judge
from .ingest import ingest


def _paragraphs(text, max_chars=1200):
    """Extract source spans, splitting long paragraphs without inventing text."""
    for match in re.finditer(r'\S.*?(?=\n[ \t]*\n|\Z)', text, flags=re.DOTALL):
        start, end = match.span()
        while start < end:
            stop = min(end, start + max_chars)
            if stop < end:
                boundary = text.rfind(' ',start,stop)
                if boundary > start:
                    stop = boundary
            while start < stop and text[start].isspace():
                start += 1
            if start < stop:
                yield start, stop
            start = stop


def _propose_generated(db, section, provider, decision_budget):
    created = calls = 0
    for start, end in _paragraphs(section['body']):
        body = section['body'][start:end]
        title_body = re.sub(r'^\s*#{1,6}\s+[^\n]*\n', '', body, count=1)
        title = re.split(r'(?<=[.!?])\s|\n', title_body, maxsplit=1)[0].strip()[:120]
        if not title:
            continue
        entry_id = hashlib.sha256(f"index-v1:{section['id']}:{start}:{end}".encode()).hexdigest()
        existing = db.execute('SELECT status FROM generated_index WHERE id=?',(entry_id,)).fetchone()
        if existing and existing['status'] in ('accepted','rejected'):
            continue
        if existing and existing['status'] == 'stale':
            with db:
                db.execute("UPDATE generated_index SET status='proposed' WHERE id=?",(entry_id,))
            existing = None  # recreate the assessment but retain the existing row
            restored = True
        else:
            restored = False
        if existing:
            assessed = db.execute("SELECT 1 FROM decision_receipts WHERE json_valid(detail) AND json_extract(detail,'$.generated_index_id')=? AND outcome != 'unknown' LIMIT 1",(entry_id,)).fetchone()
            if assessed or provider is None or calls >= decision_budget:
                continue
        judgment = None
        if provider is not None and calls < decision_budget:
            judgment = judge(provider, {'title':title, 'text':body, 'topic':title}, 'topic supported')
            calls += 1
        status = 'rejected' if judgment and judgment['outcome'] == 'unsuitable' else 'proposed'
        with db:
            if existing or restored:
                db.execute('UPDATE generated_index SET status=? WHERE id=?',(status,entry_id))
            else:
                db.execute('INSERT INTO generated_index VALUES (?,?,?,?,?,?,?,?)',(entry_id,section['id'],title,body,start,end,status,'extractive-paragraph-v1'))
            if judgment:
                db.execute('INSERT INTO decision_receipts(provider,model,outcome,detail) VALUES (?,?,?,?)',(judgment.get('provider','unknown'),judgment.get('model'),judgment['outcome'],json.dumps({'generated_index_id':entry_id,'question':'topic supported','probability':judgment.get('probability'),'usage':judgment.get('usage'),'request_id':judgment.get('request_id'),'thresholds':judgment.get('thresholds'),'reason':judgment.get('reason')})))
        created += not bool(existing) and not restored
    return created, calls


def review_generated_entry(db, entry_id, decision, reviewer):
    """Record a named review of a current proposed entry, never a model verdict."""
    if decision not in ('accepted','rejected') or not reviewer or not reviewer.strip():
        raise ValueError('accepted/rejected and a named reviewer are required')
    with db:
        updated = db.execute("UPDATE generated_index SET status=? WHERE id=? AND status='proposed' AND section_id IN (SELECT sections.id FROM sections JOIN sources ON sources.id=sections.source_id WHERE sources.status='current')",(decision,entry_id))
        if updated.rowcount != 1:
            raise ValueError('entry is not a current proposal')
        db.execute('INSERT INTO generated_index_reviews(entry_id,reviewer,decision) VALUES (?,?,?)',(entry_id,reviewer.strip(),decision))


def index_source(db, path, provider=None, max_decisions=10):
    if max_decisions < 0:
        raise ValueError('max_decisions must be nonnegative')
    source_id = ingest(db, path)
    if source_id is None:
        return {'source_id': None, 'structure_judgment': None, 'topic_candidates': 0, 'decision_calls': 0}
    sections = db.execute('SELECT * FROM sections WHERE source_id=? ORDER BY start_line', (source_id,)).fetchall()
    result = {'source_id': source_id, 'structure_judgment': None, 'topic_candidates': 0, 'generated_entries': 0, 'decision_calls': 0}
    if provider is not None and max_decisions:
        # A compact structure sample is not a complete document-quality assessment.
        state = {'sections': [{'title': s['title'], 'generated': bool(s['generated']), 'text': s['body'][:1000]} for s in sections[:5]], 'section_count': len(sections)}
        judgment = judge(provider, state, 'structure usable')
        result['structure_judgment'] = judgment
        result['decision_calls'] += 1
        with db:
            db.execute('INSERT INTO decision_receipts(provider,model,outcome,detail) VALUES (?,?,?,?)', (judgment.get('provider','unknown'), judgment.get('model'), judgment['outcome'], json.dumps({'source_id': source_id, 'question': 'structure usable', 'probability': judgment.get('probability'), 'usage': judgment.get('usage'), 'request_id': judgment.get('request_id'), 'thresholds': judgment.get('thresholds'), 'reason': judgment.get('reason')})))
    for section in sections:
        if section['generated']:
            created, calls = _propose_generated(db, section, provider, max_decisions-result['decision_calls'])
            result['generated_entries'] += created
            result['decision_calls'] += calls
            continue
        if not section['title'].strip():
            continue
        existing = db.execute('SELECT id,method,status FROM topic_links WHERE section_id=? AND topic=? AND status != ? ORDER BY id DESC LIMIT 1', (section['id'],section['title'],'stale')).fetchone()
        if existing:
            if existing['status'] == 'proposed' and existing['method'] == 'heading' and provider is not None and result['decision_calls'] < max_decisions:
                assess_topic(db, section['id'], section['title'], provider, proposal_id=existing['id'])
                result['decision_calls'] += 1
        else:
            result['topic_candidates'] += 1
            if provider is not None and result['decision_calls'] < max_decisions:
                assess_topic(db, section['id'], section['title'], provider)
                result['decision_calls'] += 1
            else:
                with db:
                    db.execute('INSERT INTO topic_links(section_id,topic,method,status) VALUES (?,?,?,?)', (section['id'], section['title'], 'heading', 'proposed'))
        if sum(1 for _ in _paragraphs(section['body'])) > 1:
            created, calls = _propose_generated(db, section, provider, max_decisions-result['decision_calls'])
            result['generated_entries'] += created
            result['decision_calls'] += calls
    return result
