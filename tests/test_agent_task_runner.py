import json
import pytest


def test_paired_runs_are_seeded_isolated_and_preserve_failures():
    from quix_knowledge.agent_study import run_agent_study
    tasks=[{'id':'t1','query':'first task','role':'reviewer','role_version':'1'},
           {'id':'t2','query':'second task','role':'reviewer','role_version':'1'}]
    observed=[]
    def context(task,condition):
        return {'source':condition,'task':task['id']}
    def agent(request):
        observed.append(request)
        if request['task_id']=='t2' and request['context'] and request['context']['source']=='baseline':
            raise TimeoutError()
        return {'output':'fixture answer','usage':None}
    report=run_agent_study(tasks,context_provider=context,agent=agent,seed=17)
    again=run_agent_study(tasks,context_provider=context,agent=agent,seed=17)
    assert report['schedule']==again['schedule']
    assert len(report['runs'])==8
    assert all(set(x)=={'task_id','query','role','role_version','context','max_input_characters'} for x in observed)
    assert sum(x['context'] is None for x in observed)==4
    assert all(x['context']['task']==x['task_id'] for x in observed if x['context'] is not None)
    assert next(r for r in report['runs'] if r['task_id']=='t2' and r['condition']=='baseline')['status']=='timeout'
    assert all(r['reported_cost'] is None for r in report['runs'])
    assert report['agent_kind']=='fixture'


def test_duplicate_tasks_and_oversized_context_are_rejected_or_recorded():
    from quix_knowledge.agent_study import run_agent_study
    task={'id':'t','query':'what','role':'reviewer','role_version':'1'}
    with pytest.raises(ValueError):
        run_agent_study([task,task],context_provider=lambda *_: None,agent=lambda _: {},seed=1)
    report=run_agent_study([task],context_provider=lambda *_: 'x'*1000,agent=lambda _: {'output':'ok'},seed=1,max_input_characters=300)
    assert sum(r['status']=='input_budget_exceeded' for r in report['runs'])==3


def test_process_agent_captures_real_output_usage_and_errors_without_key_in_args(tmp_path):
    import sys
    from quix_knowledge.agent_process import PlannerProcess
    script=tmp_path/'agent.py'
    script.write_text('import json,os,sys\nq=json.load(sys.stdin)\nassert os.environ["OPENROUTER_API_KEY"] == "secret"\nassert "secret" not in str(sys.argv)\nprint(json.dumps({"status":"completed","proposal":{"title":q["task"]},"call":{"costUSD":0.01}}))\n')
    agent=PlannerProcess([sys.executable,str(script)],api_key='secret',model='test/model',timeout=5)
    result=agent({'query':'a task','role':'reviewer','role_version':'1','context':None})
    assert json.loads(result['output'])['title']=='a task'
    assert result['usage']['cost']==0.01
    script.write_text('import json\nprint(json.dumps({"status":"source_changed"}))\n')
    assert agent({'query':'a task','role':'reviewer','role_version':'1','context':None})['status']=='source_changed'


def test_runner_preserves_explicit_agent_failure_status():
    from quix_knowledge.agent_study import run_agent_study
    task={'id':'t','query':'what','role':'reviewer','role_version':'1'}
    report=run_agent_study([task],context_provider=lambda *_: {},agent=lambda _: {'status':'source_changed'},seed=1)
    assert {run['status'] for run in report['runs']}=={'source_changed'}


def test_failed_agent_call_keeps_reported_usage():
    from quix_knowledge.agent_study import run_agent_study
    task={'id':'t','query':'what','role':'reviewer','role_version':'1'}
    result=run_agent_study([task],context_provider=lambda *_:{},agent=lambda _:{'status':'agent_failure','call':{'costUSD':0.02}},seed=1)
    assert all(run['reported_cost']==0.02 for run in result['runs'])


def test_study_records_packet_provenance_without_sending_another_condition():
    from quix_knowledge.agent_study import run_agent_study
    task={'id':'t','query':'what','role':'reviewer','role_version':'1'}
    packet={'catalog_fingerprint':'abc','results':[{'id':'s','revision':'rev','path':'doc','body':'evidence'}],'omitted_count':1}
    report=run_agent_study([task],context_provider=lambda *_:packet,agent=lambda _: {'output':'ok'},seed=3)
    result=next(x for x in report['runs'] if x['condition']=='baseline')
    assert result['context_provenance']['catalog_fingerprint']=='abc'
    assert result['context_provenance']['sources']==[{'id':'s','revision':'rev','path':'doc'}]
    assert len(result['context_provenance']['packet_sha256'])==64


def test_agent_packet_preserves_revision_and_marks_body_truncation():
    from quix_knowledge.agent_context import make_agent_packet
    task={'query':'what','role':'reviewer','role_version':'1'}
    row={'id':'id1','record_type':'section','title':'source','body':'a'*500,'path':'/source','revision':'rev','source_status':'current','start_line':1,'end_line':1}
    packet=make_agent_packet(task,[row],fingerprint='fp',body_characters=100)
    assert packet['results'][0]['body']=='a'*100
    assert packet['results'][0]['body_truncated'] is True
    assert packet['results'][0]['revision']=='rev'
    assert packet['tokenizer']=='json-characters'
    assert row['body']=='a'*500
