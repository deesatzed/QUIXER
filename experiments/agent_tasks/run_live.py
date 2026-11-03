"""Run an isolated, exploratory paired HITMCockpit planner comparison."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3

import tiktoken
from quix_knowledge.agent_context import make_agent_packet
from quix_knowledge.agent_process import PlannerProcess
from quix_knowledge.agent_study import run_agent_study
from quix_knowledge.openrouter import load_settings
from quix_knowledge.store import open_catalog
from quix_knowledge.switch_comparison import NodeSwitchRunner, run_switch_comparison

parser=argparse.ArgumentParser()
parser.add_argument('study',help='prepared retrieval study directory')
parser.add_argument('output',help='new output directory')
parser.add_argument('--planner',required=True,help='built QuixPlannerStudyCLI executable')
parser.add_argument('--model',required=True,help='explicit OpenRouter text model for all conditions')
parser.add_argument('--env-file',default='/Volumes/WS4TB/QUIX/.env')
parser.add_argument('--decision-slot',type=int,default=2)
args=parser.parse_args()
root=Path(__file__).resolve().parents[2]
manifest_path=Path(__file__).parent/'manifest.json'
manifest_bytes=manifest_path.read_bytes(); manifest=json.loads(manifest_bytes)
study=Path(args.study); prep=json.loads((study/'preparation.json').read_text())
output=Path(args.output); output.mkdir(parents=True,exist_ok=False)
(output/'manifest.json').write_bytes(manifest_bytes)
source=sqlite3.connect((study/'catalog.db').resolve().as_uri()+'?mode=ro',uri=True)
copy=sqlite3.connect(output/'catalog-copy.db')
try: source.backup(copy)
finally: copy.close(); source.close()
db=open_catalog(output/'catalog-copy.db')
try:
    node=shutil.which('node')
    if not node: raise RuntimeError('node unavailable')
    runner=NodeSwitchRunner(node,root/'experiments/switch-navigation/src/compare.ts',mode='openrouter',env_file=args.env_file,model_slot=args.decision_slot)
    encoding=tiktoken.get_encoding('cl100k_base')
    comparison=run_switch_comparison(db,manifest['tasks'],switch_runner=runner,packet_tokens=2000,count_tokens=lambda x:len(encoding.encode(x)),tokenizer_name='cl100k_base',limit=3,provider=None,include_proposed=True,ranking='bm25')
    if comparison['manifest']['corpus_revision'] != prep['corpus_revision']:
        raise RuntimeError('prepared catalog changed')
    (output/'retrieval-report.json').write_text(json.dumps(comparison,ensure_ascii=False,indent=2))
    fingerprint=comparison['manifest']['corpus_revision']
    packets={}
    for task in manifest['tasks']:
        for condition in ('baseline','role','switch'):
            q=comparison['variants'][condition]['queries'][task['id']]
            rows=[dict(item) for item in q['results']]
            if rows and q.get('fallback_reason'): rows[0]['fallback_reason']=q['fallback_reason']
            for row in rows:
                if row['record_type']=='agent_record':
                    row['evidence_sources']=[dict(item) for item in db.execute('''SELECT s.id AS section_id,x.path,x.revision,x.status AS source_status,s.start_line,s.end_line,p.page_start,p.page_end FROM evidence e JOIN sections s ON s.id=e.section_id JOIN sources x ON x.id=s.source_id LEFT JOIN section_pages p ON p.section_id=s.id WHERE e.record_id=? ORDER BY s.id''',(row['id'],))]
            packets[(task['id'],condition)]=make_agent_packet(task,rows,fingerprint=fingerprint)
    (output/'packets.json').write_text(json.dumps([{'task_id':key[0],'condition':key[1],'packet':value} for key,value in packets.items()],ensure_ascii=False,indent=2))
    settings=load_settings(args.env_file,args.decision_slot)
    agent=PlannerProcess([str(Path(args.planner).resolve())],api_key=settings.api_key,model=args.model,timeout=60)
    report=run_agent_study(manifest['tasks'],context_provider=lambda task,condition:packets[(task['id'],condition)],agent=agent,seed=manifest['seed'],max_input_characters=manifest['max_input_characters'],agent_kind='actual')
    report['manifest']={'sha256':hashlib.sha256(manifest_bytes).hexdigest(),'model':args.model,'corpus_revision':fingerprint,
        'planner_executable_sha256':hashlib.sha256(Path(args.planner).read_bytes()).hexdigest(),
        'role_annotations':db.execute('SELECT count(*) FROM role_annotations').fetchone()[0],
        'planner_intent_limit_unicode_scalars':2000,'context_body_character_limit':300,
        'retrieval_packet_token_limit':2000,'retrieval_tokenizer':'cl100k_base','decision_slot':args.decision_slot,
        'limitations':'Exploratory shared corpus; no independent labels, no agent outcome review; provider/model input budgets are not matched across retrieval policies. Costs and failures are per call; local compute unknown.'}
    (output/'agent-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print(json.dumps({'runs':len(report['runs']),'statuses':{status:sum(x['status']==status for x in report['runs']) for status in sorted({x['status'] for x in report['runs']})},'output':str(output)}))
finally: db.close()
