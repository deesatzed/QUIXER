"""Run the isolated HITMCockpit planner executable as a bounded child process."""
import json
import os
import subprocess
import tempfile

_STATUSES={'invalid_request','configuration_missing','agent_failure','intent_too_large','task_mismatch','source_changed','context_invalid'}


class PlannerProcess:
    def __init__(self, command, *, api_key, model, timeout=60):
        if not isinstance(command,list) or not command or not all(isinstance(x,str) and x for x in command) or not api_key or not model or not 0 < timeout <= 120:
            raise ValueError('invalid process configuration')
        self.command=list(command)
        self._key=api_key
        self.model=model
        self.timeout=timeout

    def __call__(self, request):
        payload={'task':request['query'],'role':request['role'],'role_version':request['role_version'],'packet':request['context']}
        raw=json.dumps(payload,ensure_ascii=False,separators=(',',':')).encode()
        if len(raw)>500_000:
            return {'status':'input_budget_exceeded'}
        environment={'PATH':os.environ.get('PATH','/usr/bin:/bin'),'OPENROUTER_API_KEY':self._key,'QUIX_STUDY_AGENT_MODEL':self.model}
        try:
            with tempfile.TemporaryFile() as output:
                process=subprocess.run(self.command,input=raw,stdout=output,stderr=subprocess.DEVNULL,env=environment,timeout=self.timeout,check=False)
                if process.returncode != 0 or output.tell()>500_000:
                    return {'status':'process_failure'}
                output.seek(0); result=json.load(output)
        except subprocess.TimeoutExpired:
            raise TimeoutError() from None
        except (OSError,ValueError):
            return {'status':'process_failure'}
        if not isinstance(result,dict):
            return {'status':'invalid_response'}
        call=result.get('call') if isinstance(result.get('call'),dict) else None
        status=result.get('status')
        if status in _STATUSES:
            return {'status':status,'call':call}
        if status!='completed' or not isinstance(result.get('proposal'),dict):
            return {'status':'invalid_response','call':call}
        return {'output':json.dumps(result['proposal'],ensure_ascii=False,sort_keys=True),'usage':{'cost':call.get('costUSD')} if call else None,'call':call}
