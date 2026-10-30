"""Validate provider responses; errors are unknown, never a negative judgment."""
import json
import math

def decision_metadata(result):
    """Retain score semantics and usage without storing authentication data."""
    keys = ('probability','probability_status','legal_mass','stability','usage','request_id','thresholds','reason')
    return {key:result.get(key) for key in keys}

def judge(provider, state, question):
    try:
        result = provider(state, question)
        if not isinstance(result, dict) or result.get('outcome') not in {'supported','unclear','unsuitable'} or not isinstance(result.get('provider'),str):
            return {'outcome':'unknown','provider':'unknown','reason':'invalid response'}
        usage = result.get('usage')
        if usage is not None:
            result = dict(result)
            result['usage'] = {key:value for key,value in usage.items() if key in ('cost','input_tokens','output_tokens') and isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value) and value >= 0} if isinstance(usage,dict) else None
        return result
    except Exception as exc:
        return {'outcome':'unknown','provider':'unknown','reason':type(exc).__name__}

def assess_topic(db, section_id, topic, provider, proposal_id=None):
    section = db.execute('SELECT title,body FROM sections WHERE id=?',(section_id,)).fetchone()
    if section is None:
        raise ValueError('unknown section')
    result = judge(provider, {'title':section['title'],'text':section['body'][:4000],'text_truncated':len(section['body']) > 4000,'topic':topic}, 'topic supported')
    # Even supported model proposals require independent acceptance.
    status = 'rejected' if result['outcome'] == 'unsuitable' else 'proposed'
    with db:
        if proposal_id is None:
            method = 'heading' if result['outcome'] == 'unknown' else 'decision'
            db.execute('INSERT INTO topic_links(section_id,topic,method,status) VALUES (?,?,?,?)',(section_id,topic,method,status))
        else:
            method = 'heading' if result['outcome'] == 'unknown' else 'decision'
            updated = db.execute("UPDATE topic_links SET method=?,status=? WHERE id=? AND section_id=? AND topic=? AND status='proposed'",(method,status,proposal_id,section_id,topic))
            if updated.rowcount != 1:
                raise ValueError('proposal no longer available')
        db.execute('INSERT INTO decision_receipts(provider,model,outcome,detail) VALUES (?,?,?,?)',(result.get('provider','unknown'),result.get('model'),result['outcome'],json.dumps({'section_id':section_id,'topic':topic,**decision_metadata(result)})))
    return result


def assess_role(db, section_id, role, role_version, role_purpose, provider):
    """Save a provisional role-usefulness estimate tied to a source revision."""
    if not all(isinstance(value,str) and value.strip() for value in (role,role_version,role_purpose)):
        raise ValueError('role, version and purpose are required')
    section = db.execute("SELECT sections.title,sections.body,sources.revision FROM sections JOIN sources ON sources.id=sections.source_id WHERE sections.id=? AND sources.status='current'",(section_id,)).fetchone()
    if section is None:
        raise ValueError('section is not in a current source')
    state = {'title':section['title'],'text':section['body'][:4000],'text_truncated':len(section['body'])>4000,'role':role,'role_version':role_version,'role_purpose':role_purpose}
    result = judge(provider,state,'role usefulness')
    score = result.get('probability')
    valid = not isinstance(score,bool) and isinstance(score,(int,float)) and math.isfinite(score) and 0 <= score <= 1
    if result['outcome'] != 'unknown' and not valid:
        result = dict(result,outcome='unknown',reason='invalid role-usefulness probability',probability=None)
    detail = {'section_id':section_id,'source_revision':section['revision'],'question':'role usefulness','role':role,'role_version':role_version,'role_purpose':role_purpose,**decision_metadata(result)}
    detail['probability'] = score if valid else None
    with db:
        db.execute('INSERT INTO decision_receipts(provider,model,outcome,detail) VALUES (?,?,?,?)',(result.get('provider','unknown'),result.get('model'),result['outcome'],json.dumps(detail)))
        if result['outcome'] != 'unknown' and valid:
            db.execute('INSERT INTO role_annotations(section_id,role,role_version,score,method,model,source_revision,status) VALUES (?,?,?,?,?,?,?,?)',(section_id,role,role_version,score,'decision',result.get('model'),section['revision'],'proposed'))
    return result
