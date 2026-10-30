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
