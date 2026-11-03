"""Isolated paired agent-study orchestration; injected functions own all I/O."""
import json
import math
import random
import time

CONDITIONS=('none','baseline','role','switch')


def run_agent_study(tasks, *, context_provider, agent, seed, max_input_characters=12000, agent_kind='fixture'):
    if not isinstance(tasks,list) or not tasks or type(seed) is not int or type(max_input_characters) is not int or max_input_characters < 1:
        raise ValueError('invalid study configuration')
    fields=('id','query','role','role_version')
    if any(not isinstance(t,dict) or any(not isinstance(t.get(k),str) or not t[k].strip() for k in fields) for t in tasks) or len({t['id'] for t in tasks})!=len(tasks):
        raise ValueError('invalid or duplicate tasks')
    if not callable(context_provider) or not callable(agent) or agent_kind not in ('fixture','actual'):
        raise ValueError('invalid study adapters')
    rng=random.Random(seed)
    schedule=[]
    for task in tasks:
        conditions=list(CONDITIONS); rng.shuffle(conditions)
        schedule.extend({'task_id':task['id'],'condition':condition} for condition in conditions)
    by_id={task['id']:task for task in tasks}
    runs=[]
    for entry in schedule:
        task=by_id[entry['task_id']]; condition=entry['condition']; started=time.monotonic()
        record={**entry,'status':'error','output':None,'reported_cost':None,'usage':None}
        try:
            context=None if condition=='none' else context_provider(dict(task),condition)
            if condition!='none' and context is None:
                record['status']='context_unavailable'
            else:
                request={'task_id':task['id'],'query':task['query'],'role':task['role'],'role_version':task['role_version'],
                    'context':context,'max_input_characters':max_input_characters}
                if len(json.dumps(request,ensure_ascii=False,separators=(',',':'))) > max_input_characters:
                    record['status']='input_budget_exceeded'
                else:
                    response=agent(request)
                    if not isinstance(response,dict) or not isinstance(response.get('output'),str):
                        record['status']='invalid_response'
                    else:
                        record['status']='completed'; record['output']=response['output']; record['usage']=response.get('usage')
                        cost=(response.get('usage') or {}).get('cost') if isinstance(response.get('usage'),dict) else None
                        if isinstance(cost,(int,float)) and not isinstance(cost,bool) and math.isfinite(cost) and cost>=0:
                            record['reported_cost']=cost
        except TimeoutError:
            record['status']='timeout'
        except Exception:
            record['status']='adapter_error'
        record['elapsed_seconds']=time.monotonic()-started
        runs.append(record)
    return {'schema':'quix-agent-study-v1','agent_kind':agent_kind,'seed':seed,'max_input_characters':max_input_characters,'schedule':schedule,'runs':runs}
