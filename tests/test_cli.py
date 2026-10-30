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
