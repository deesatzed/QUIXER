from quix_knowledge.experiment import run_experiment
from quix_knowledge.ingest import ingest
from quix_knowledge.store import open_catalog


def test_run_records_common_corpus_and_real_call_receipts(tmp_path):
    db = open_catalog(':memory:')
    path = tmp_path / 'plan.md'
    path.write_text('# Retry\nRetry twice.')
    ingest(db, path)
    sid = db.execute('SELECT id FROM sections').fetchone()[0]
    calls = []
    def provider(state, question):
        calls.append(question)
        return {'outcome':'unclear','provider':'fake','model':'fixture','probability':0.5,'usage':{'cost':0.02,'input_tokens':15},'request_id':'test'}
    tasks = [{'id':'q','query':'retry','role':'reviewer','role_version':'1','split':'held_out','labels':[sid]}]
    result = run_experiment(db, tasks, provider=provider, context_chars=100, limit=3, label_provenance='synthetic fixture')
    assert set(result['variants']) == {'baseline','topic','decision','role'}
    assert result['manifest']['label_provenance'] == 'synthetic fixture'
    assert result['variants']['baseline']['metrics']['mean_recall'] == 1
    assert result['variants']['decision']['queries']['q']['decision_calls'] == 1
    assert result['variants']['decision']['queries']['q']['reported_cost'] == 0.02
    assert len(calls) == 2


def test_run_rejects_missing_or_duplicate_task_ids(tmp_path):
    import pytest
    db = open_catalog(':memory:')
    with pytest.raises(ValueError):
        run_experiment(db,[{'id':'x','query':'a'}, {'id':'x','query':'b'}])

def test_experiment_records_common_token_budget(tmp_path):
    db=open_catalog(':memory:')
    path=tmp_path/'doc.md'
    path.write_text('# Retry\nRetry with a bounded budget.')
    ingest(db,path)
    report=run_experiment(db,[{'id':'q','query':'retry','labels':None}],context_chars=None,context_tokens=2,count_tokens=lambda text:len(text.split()),tokenizer_name='fixture-words')
    assert report['manifest']['context_tokens'] == 2
    assert report['manifest']['tokenizer'] == 'fixture-words'
    for variant in report['variants'].values():
        assert variant['queries']['q']['returned_body_tokens'] <= 2

def test_experiment_compares_full_context_packets_under_same_budget(tmp_path):
    import json
    db=open_catalog(':memory:')
    path=tmp_path/'doc.md'
    path.write_text('# Retry\n'+'retry '*80)
    ingest(db,path)
    tasks=[{'id':'q','query':'retry','role':'reviewer','role_version':'1','labels':None}]
    report=run_experiment(db,tasks,context_chars=None,packet_tokens=400,count_tokens=len,tokenizer_name='fixture-chars')
    assert report['manifest']['packet_tokens'] == 400
    for variant in report['variants'].values():
        query=variant['queries']['q']
        packet=query['context_packet']
        serialized=json.dumps(packet,ensure_ascii=False,sort_keys=True,separators=(',',':'))
        assert len(serialized) <= 400
        assert query['packet_token_count'] == len(serialized)
        assert query['results'] == packet['results']

def test_experiment_records_provider_policy_without_credentials(tmp_path):
    from quix_knowledge.openrouter import OpenRouterDecision,Settings
    db=open_catalog(':memory:')
    provider=OpenRouterDecision(Settings('never-log-this-key','fixture-model'),transport=lambda *args:{'answers':{'judgment':{'type':'noul','noul':0.5}}},thresholds=(0.2,0.8))
    report=run_experiment(db,[{'id':'q','query':'retry','labels':None}],provider=provider)
    assert report['manifest']['provider']['configured_model'] == 'fixture-model'
    assert report['manifest']['provider']['thresholds'] == (0.2,0.8)
    assert 'never-log-this-key' not in str(report)

def test_experiment_can_explicitly_include_provisional_index(tmp_path):
    from quix_knowledge.indexing import index_source
    db=open_catalog(':memory:')
    path=tmp_path/'doc.txt'
    path.write_text('Retry helps outages.\n\nAudit tracks failures.')
    index_source(db,path)
    tasks=[{'id':'q','query':'audit','labels':None}]
    report=run_experiment(db,tasks,include_proposed=True)
    assert report['manifest']['include_proposed'] is True
    assert any(r['record_type']=='generated_index' for r in report['variants']['topic']['queries']['q']['results'])
    assert not any(r['record_type']=='generated_index' for r in report['variants']['baseline']['queries']['q']['results'])

def test_experiment_records_indexing_cost_as_separate_measurement(tmp_path):
    from quix_knowledge.indexing import index_source
    db=open_catalog(':memory:')
    path=tmp_path/'doc.md'
    path.write_text('# Retry\nRetry after delay.')
    def provider(state,question):
        return {'outcome':'unclear','provider':'fixture','usage':{'cost':0.01,'input_tokens':5}}
    indexed=index_source(db,path,provider=provider,max_decisions=2)
    report=run_experiment(db,[{'id':'q','query':'retry','labels':None}],indexing_receipt_ids=indexed['receipt_ids'])
    indexing=report['manifest']['indexing']
    assert indexing['decision_calls'] == 2
    assert indexing['reported_cost'] == 0.02
    assert indexing['input_tokens'] == 10
    assert report['variants']['baseline']['queries']['q']['decision_calls'] == 0

def test_experiment_rejects_receipts_for_superseded_source(tmp_path):
    import pytest
    from quix_knowledge.indexing import index_source
    db=open_catalog(':memory:')
    path=tmp_path/'doc.md'
    path.write_text('# Retry\nRetry after delay.')
    result=index_source(db,path,provider=lambda *args: {'outcome':'unclear','provider':'fixture'},max_decisions=1)
    path.write_text('# Retry\nDo not retry.')
    ingest(db,path)
    with pytest.raises(ValueError,match='current source'):
        run_experiment(db,[{'id':'q','query':'retry','labels':None}],indexing_receipt_ids=result['receipt_ids'])

def test_missing_gold_source_is_not_scored_as_retrieval_failure(tmp_path):
    db=open_catalog(':memory:')
    path=tmp_path/'doc.md'
    path.write_text('# Retry\nRetry after delay.')
    ingest(db,path)
    report=run_experiment(db,[{'id':'q','query':'retry','labels':['missing-section']}])
    for variant in report['variants'].values():
        assert variant['metrics']['missing_source'] == 1
        assert variant['metrics']['answerable'] == 0
        assert variant['metrics']['mean_recall'] is None
        assert variant['queries']['q']['missing_label_ids'] == ['missing-section']

def test_experiment_rejects_malformed_labels(tmp_path):
    import pytest
    db=open_catalog(':memory:')
    with pytest.raises(ValueError,match='labels'):
        run_experiment(db,[{'id':'q','query':'retry','labels':'section-id'}])

def test_metrics_are_reported_separately_for_development_and_held_out(tmp_path):
    db=open_catalog(':memory:')
    path=tmp_path/'doc.md'
    path.write_text('# Retry\nRetry after delay.')
    ingest(db,path)
    sid=db.execute('SELECT id FROM sections').fetchone()[0]
    tasks=[{'id':'dev','query':'retry','labels':[sid],'split':'development'}, {'id':'test','query':'timeout','labels':[sid],'split':'held_out'}]
    report=run_experiment(db,tasks)
    split=report['variants']['baseline']['metrics_by_split']
    assert split['development']['mean_recall'] == 1
    assert split['held_out']['mean_recall'] == 0
