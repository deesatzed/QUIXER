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
