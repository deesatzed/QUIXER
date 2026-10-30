import json
import subprocess
import sys
import os
from pathlib import Path

def test_cli_ingest_and_search(tmp_path):
    path = tmp_path/'doc.md'
    path.write_text('# Interface\nmessage protocol\n')
    db = tmp_path/'catalog.db'
    env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1]/'src'))
    def run(*args):
        return subprocess.run([sys.executable,'-m','quix_knowledge', '--db',str(db),*args],env=env,capture_output=True,text=True,check=True)
    assert json.loads(run('ingest',str(path)).stdout)['source_id']
    result = json.loads(run('search','protocol').stdout)
    assert result[0]['title'] == 'Interface'
    assert result[0]['start_line'] == 1

def test_cli_requires_both_env_file_and_slot_for_model(tmp_path):
    env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1]/'src'))
    result = subprocess.run([sys.executable,'-m','quix_knowledge','--db',str(tmp_path/'db'),'search','retry','--variant','decision','--model-slot','2'],env=env,capture_output=True,text=True)
    assert result.returncode != 0
    assert '--env-file' in result.stderr

def test_cli_index_creates_proposed_topic(tmp_path):
    path = tmp_path/'doc.md'
    path.write_text('# Retry policy\nRetry twice.\n')
    env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1]/'src'))
    result = subprocess.run([sys.executable,'-m','quix_knowledge','--db',str(tmp_path/'db'),'index',str(path)],env=env,capture_output=True,text=True,check=True)
    assert json.loads(result.stdout)['topic_candidates'] == 1

def test_cli_experiment_emits_manifest_for_unlabeled_task(tmp_path):
    taskfile = tmp_path/'tasks.json'
    taskfile.write_text(json.dumps([{'id':'q','query':'retry','role':'reviewer','role_version':'1','labels':None}]))
    env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1]/'src'))
    result = subprocess.run([sys.executable,'-m','quix_knowledge','--db',str(tmp_path/'db'),'experiment',str(taskfile),'--context-chars','100'],env=env,capture_output=True,text=True,check=True)
    report = json.loads(result.stdout)
    assert report['variants']['baseline']['metrics']['unlabeled'] == 1
    assert report['manifest']['context_chars'] == 100

def test_cli_token_budget_uses_named_tokenizer(tmp_path):
    import pytest
    pytest.importorskip('tiktoken')
    path=tmp_path/'doc.md'
    path.write_text('# Retry\nRetry with exponential backoff and jitter.')
    db=tmp_path/'db'
    env=dict(os.environ,PYTHONPATH=str(Path(__file__).resolve().parents[1]/'src'))
    base=[sys.executable,'-m','quix_knowledge','--db',str(db)]
    subprocess.run([*base,'ingest',str(path)],env=env,capture_output=True,text=True,check=True)
    result=subprocess.run([*base,'search','retry','--context-tokens','3','--tokenizer','cl100k_base'],env=env,capture_output=True,text=True,check=True)
    rows=json.loads(result.stdout)
    assert sum(row['context_token_count'] for row in rows) <= 3

def test_cli_can_list_and_review_generated_entries(tmp_path):
    path=tmp_path/'manual.txt'
    path.write_text('Retries prevent outages.\n\nRecord failures.')
    db=tmp_path/'db'
    env=dict(os.environ,PYTHONPATH=str(Path(__file__).resolve().parents[1]/'src'))
    base=[sys.executable,'-m','quix_knowledge','--db',str(db)]
    subprocess.run([*base,'index',str(path)],env=env,capture_output=True,text=True,check=True)
    listed=json.loads(subprocess.run([*base,'list-index'],env=env,capture_output=True,text=True,check=True).stdout)
    assert len(listed) == 2
    entry=listed[0]['id']
    subprocess.run([*base,'review-index',entry,'accepted','--reviewer','human-reviewer'],env=env,capture_output=True,text=True,check=True)
    listed=json.loads(subprocess.run([*base,'list-index'],env=env,capture_output=True,text=True,check=True).stdout)
    assert next(x for x in listed if x['id'] == entry)['status'] == 'accepted'

def test_cli_experiment_accepts_saved_index_receipt_ids(tmp_path):
    tasks=tmp_path/'tasks.json'
    tasks.write_text(json.dumps([{'id':'q','query':'retry','labels':None}]))
    receipts=tmp_path/'receipts.json'
    receipts.write_text('[]')
    env=dict(os.environ,PYTHONPATH=str(Path(__file__).resolve().parents[1]/'src'))
    cmd=[sys.executable,'-m','quix_knowledge','--db',str(tmp_path/'db'),'experiment',str(tasks),'--indexing-receipts',str(receipts)]
    report=json.loads(subprocess.run(cmd,env=env,capture_output=True,text=True,check=True).stdout)
    assert report['manifest']['indexing']['decision_calls'] == 0

def test_cli_role_assessment_requires_explicit_model_and_role_purpose(tmp_path):
    env=dict(os.environ,PYTHONPATH=str(Path(__file__).resolve().parents[1]/'src'))
    cmd=[sys.executable,'-m','quix_knowledge','--db',str(tmp_path/'db'),'assess-role','section','--role','reviewer','--role-version','1']
    result=subprocess.run(cmd,env=env,capture_output=True,text=True)
    assert result.returncode != 0
    assert '--role-purpose' in result.stderr

def test_cli_rejects_mixed_local_and_openrouter_configuration(tmp_path):
    env=dict(os.environ,PYTHONPATH=str(Path(__file__).resolve().parents[1]/'src'))
    cmd=[sys.executable,'-m','quix_knowledge','--db',str(tmp_path/'db'),'search','retry','--variant','decision','--env-file','config.env','--model-slot','2','--jev-url','http://127.0.0.1:8090']
    result=subprocess.run(cmd,env=env,capture_output=True,text=True)
    assert result.returncode != 0
    assert 'choose one decision provider' in result.stderr
