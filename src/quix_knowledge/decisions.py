"""Validate provider responses; errors are unknown, never a negative judgment."""
import json
def judge(provider, state, question):
    try:
        result = provider(state, question)
        if not isinstance(result, dict) or result.get('outcome') not in {'supported','unclear','unsuitable'} or not isinstance(result.get('provider'),str):
            return {'outcome':'unknown','provider':'unknown','reason':'invalid response'}
        return result
    except Exception as exc:
        return {'outcome':'unknown','provider':'unknown','reason':type(exc).__name__}

def assess_topic(db, section_id, topic, provider):
    section = db.execute('SELECT title,body FROM sections WHERE id=?',(section_id,)).fetchone()
    if section is None:
        raise ValueError('unknown section')
    result = judge(provider, {'title':section['title'],'text':section['body'],'topic':topic}, 'topic supported')
    # Even supported model proposals require independent acceptance.
    status = 'rejected' if result['outcome'] == 'unsuitable' else 'proposed'
    with db:
        db.execute('INSERT INTO topic_links(section_id,topic,method,status) VALUES (?,?,?,?)',(section_id,topic,'decision',status))
        db.execute('INSERT INTO decision_receipts(provider,model,outcome,detail) VALUES (?,?,?,?)',(result.get('provider','unknown'),result.get('model'),result['outcome'],json.dumps({'section_id':section_id,'topic':topic,'reason':result.get('reason'),'probability':result.get('probability'),'usage':result.get('usage'),'request_id':result.get('request_id'),'thresholds':result.get('thresholds')})))
    return result
