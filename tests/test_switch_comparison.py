import pytest

from quix_knowledge.ingest import ingest
from quix_knowledge.store import open_catalog


def test_switch_comparison_uses_shared_candidate_set_and_packet_budget(tmp_path):
    from quix_knowledge.switch_comparison import run_switch_comparison
    db=open_catalog(':memory:')
    path=tmp_path/'doc.md'
    path.write_text('# Retry\nRetry after a timeout.')
    ingest(db,path)
    sid=db.execute('SELECT id FROM sections').fetchone()[0]
    tasks=[{'id':'q','query':'retry','role':'reviewer','role_version':'1','split':'held_out','labels':[sid]}]
    def switch(snapshot):
        candidate=snapshot['candidates'][0]
        assert snapshot['candidate_scope'] == 'sections_and_records'
        return {'status':'complete','reason':None,'state':{'evidence':[{'id':candidate['id'],'text':candidate['body'],'truncated':False}]},'receipts':[]}
    report=run_switch_comparison(db,tasks,switch_runner=switch,packet_tokens=3000,count_tokens=len,tokenizer_name='fixture-characters',limit=3)
    assert report['manifest']['candidate_scope'] == 'sections_and_records'
    assert report['variants']['switch']['metrics']['mean_recall'] == 1
    assert report['variants']['switch']['queries']['q']['packet_token_count'] <= 3000
    assert report['variants']['switch']['queries']['q']['fallback_reason'] is None


def test_invalid_switch_selection_uses_explicit_baseline_fallback(tmp_path):
    from quix_knowledge.switch_comparison import run_switch_comparison
    db=open_catalog(':memory:')
    path=tmp_path/'doc.md'; path.write_text('# Retry\nRetry after a timeout.'); ingest(db,path)
    sid=db.execute('SELECT id FROM sections').fetchone()[0]
    tasks=[{'id':'q','query':'retry','role':'reviewer','role_version':'1','labels':[sid]}]
    def switch(snapshot): return {'status':'complete','reason':None,'state':{'evidence':[{'id':'invented','text':'invented','truncated':False}]},'receipts':[]}
    report=run_switch_comparison(db,tasks,switch_runner=switch,packet_tokens=3000,count_tokens=len,tokenizer_name='fixture-characters',limit=3)
    query=report['variants']['switch']['queries']['q']
    assert query['fallback_reason'] == 'invalid_switch_result'
    assert [r['id'] for r in query['results']] == [r['id'] for r in report['variants']['baseline']['queries']['q']['results']]


def test_switch_comparison_rejects_source_changed_during_navigation(tmp_path):
    from quix_knowledge.switch_comparison import run_switch_comparison
    db=open_catalog(':memory:')
    path=tmp_path/'doc.md'; path.write_text('# Retry\nRetry after a timeout.'); ingest(db,path)
    tasks=[{'id':'q','query':'retry','role':'reviewer','role_version':'1','labels':None}]
    def switch(snapshot):
        path.write_text('# Retry\nChanged.')
        return {'status':'insufficient_evidence','reason':'unknown','state':{'evidence':[]},'receipts':[]}
    with pytest.raises(ValueError,match='source'):
        run_switch_comparison(db,tasks,switch_runner=switch,packet_tokens=3000,count_tokens=len,tokenizer_name='fixture-characters',limit=3)


def test_failed_runner_does_not_claim_zero_provider_calls(tmp_path):
    from quix_knowledge.switch_comparison import run_switch_comparison
    db=open_catalog(':memory:')
    path=tmp_path/'doc.md'; path.write_text('# Retry\nRetry after a timeout.'); ingest(db,path)
    tasks=[{'id':'q','query':'retry','role':'reviewer','role_version':'1','labels':None}]
    def switch(snapshot): raise TimeoutError()
    report=run_switch_comparison(db,tasks,switch_runner=switch,packet_tokens=3000,count_tokens=len,tokenizer_name='fixture-characters')
    query=report['variants']['switch']['queries']['q']
    assert query['fallback_reason'] == 'switch_insufficient_evidence'
    assert query['physical_requests'] is None
    assert query['reported_cost'] is None


def test_real_node_fixture_runner_participates_in_matched_comparison(tmp_path):
    import shutil
    from pathlib import Path
    from quix_knowledge.switch_comparison import NodeSwitchRunner, run_switch_comparison
    node=shutil.which('node')
    script=Path(__file__).resolve().parents[1]/'experiments/switch-navigation/src/compare.ts'
    if not node or not (script.parents[1]/'node_modules/@osolmaz/switch').exists():
        pytest.skip('node or installed switch package unavailable')
    db=open_catalog(':memory:')
    path=tmp_path/'doc.md'; path.write_text('# Retry\nRetry after timeout.'); ingest(db,path)
    sid=db.execute('SELECT id FROM sections').fetchone()[0]
    tasks=[{'id':'q','query':'retry','role':'reviewer','role_version':'1','labels':[sid]}]
    report=run_switch_comparison(db,tasks,switch_runner=NodeSwitchRunner(node,script,mode='fixture'),packet_tokens=3000,count_tokens=len,tokenizer_name='fixture-characters')
    query=report['variants']['switch']['queries']['q']
    assert query['fallback_reason'] is None
    assert query['results'][0]['id'] == sid
    assert query['physical_requests'] == 0
