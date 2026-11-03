import json
import pytest


def test_blind_review_hides_condition_and_keeps_failed_runs_separate():
    from quix_knowledge.agent_review import prepare_agent_review
    report={'agent_kind':'actual','runs':[
        {'task_id':'t1','condition':'baseline','status':'completed','output':'First response'},
        {'task_id':'t1','condition':'switch','status':'completed','output':'Second response'},
        {'task_id':'t2','condition':'none','status':'timeout','output':None}]}
    tasks=[{'id':'t1','query':'task one'},{'id':'t2','query':'task two'}]
    packet,key=prepare_agent_review(report,tasks,seed=8)
    assert len(packet['items'])==2
    assert len(key['missing'])==6 and sum(x['status']=='timeout' for x in key['missing'])==1
    assert sum(x['status']=='missing' for x in key['missing'])==5
    assert 'baseline' not in json.dumps(packet) and 'switch' not in json.dumps(packet)
    assert all(item['review'] is None for item in packet['items'])
    assert prepare_agent_review(report,tasks,seed=8)==(packet,key)
    assert {item['blind_id'] for item in packet['items']}==set(key['conditions'])


def test_blind_review_rejects_fixture_and_duplicate_conditions():
    from quix_knowledge.agent_review import prepare_agent_review
    task=[{'id':'t','query':'task'}]
    with pytest.raises(ValueError): prepare_agent_review({'agent_kind':'fixture','runs':[]},task,seed=1)
    run={'task_id':'t','condition':'none','status':'completed','output':'ok'}
    with pytest.raises(ValueError): prepare_agent_review({'agent_kind':'actual','runs':[run,run]},task,seed=1)
