"""Make a condition-blind outcome-review packet and a separate local key."""
import random


def prepare_agent_review(report, tasks, *, seed):
    if not isinstance(report,dict) or report.get('agent_kind')!='actual' or type(seed) is not int:
        raise ValueError('an actual-agent report and integer seed are required')
    if not isinstance(tasks,list) or any(not isinstance(t,dict) or not isinstance(t.get('id'),str) or not isinstance(t.get('query'),str) for t in tasks):
        raise ValueError('invalid tasks')
    by_id={t['id']:t['query'] for t in tasks}
    if len(by_id)!=len(tasks): raise ValueError('duplicate task')
    runs=report.get('runs')
    if not isinstance(runs,list): raise ValueError('invalid runs')
    seen=set(); completed=[]; missing=[]
    for run in runs:
        if not isinstance(run,dict) or run.get('task_id') not in by_id or run.get('condition') not in ('none','baseline','role','switch'):
            raise ValueError('invalid run identity')
        identity=(run['task_id'],run['condition'])
        if identity in seen: raise ValueError('duplicate run')
        seen.add(identity)
        if run.get('status')=='completed' and isinstance(run.get('output'),str): completed.append(run)
        else: missing.append({'task_id':run['task_id'],'condition':run['condition'],'status':run.get('status','unknown')})
    for task_id in by_id:
        for condition in ('none','baseline','role','switch'):
            if (task_id,condition) not in seen:
                missing.append({'task_id':task_id,'condition':condition,'status':'missing'})
    random.Random(seed).shuffle(completed)
    items=[]; conditions={}
    for index,run in enumerate(completed,1):
        blind_id=f'answer-{index:03d}'
        items.append({'blind_id':blind_id,'task_id':run['task_id'],'task':by_id[run['task_id']],'output':run['output'],'review':None})
        conditions[blind_id]={'task_id':run['task_id'],'condition':run['condition']}
    return ({'schema':'quix-agent-outcome-review-v1','reviewer':None,'reviewed_at':None,
             'rubric':{'correctness':'correct, partial, incorrect, or unknown',
                 'source_support':'supported, partial, unsupported, no_citations, or unknown',
                 'missing_evidence':'none, material, or unknown','task_completion':'complete, partial, incomplete, or unknown'},
             'items':items},
            {'schema':'quix-agent-outcome-key-v1','seed':seed,'conditions':conditions,'missing':missing})
