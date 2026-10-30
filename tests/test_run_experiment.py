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
