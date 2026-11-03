import json
from pathlib import Path

import pytest


def test_preregistered_study_creates_blind_packet_with_lifecycle_fixtures(tmp_path):
    from quix_knowledge.retrieval_study import prepare_study
    root=Path(__file__).resolve().parents[1]
    output=tmp_path/'study'
    summary=prepare_study(root,root/'experiments/retrieval/manifest.json',output)
    packet=json.loads((output/'blind-review-packet.json').read_text())
    assert summary['tasks'] == 16
    assert summary['candidate_scope'] == 'sections_and_records'
    assert all(task['labels'] is None and not task['reviewed'] for task in packet['tasks'])
    assert not any(candidate['record_type']=='generated_index' for candidate in packet['candidates'])
    by_id={candidate['id']:candidate for candidate in packet['candidates']}
    assert by_id['synthetic-stale-finding']['evidence_status'] == 'stale'
    assert by_id['synthetic-unsupported-finding']['evidence_status'] == 'unsupported'
    assert by_id['synthetic-conflicting-finding']['evidence_status'] == 'current'
    with pytest.raises(FileExistsError):
        prepare_study(root,root/'experiments/retrieval/manifest.json',output)


def test_study_rejects_changed_source_before_creating_catalog(tmp_path):
    from quix_knowledge.retrieval_study import prepare_study
    root=tmp_path/'root'; root.mkdir()
    (root/'source.txt').write_text('changed')
    manifest={'schema':'quix-retrieval-study-v1','sources':[{'path':'source.txt','sha256':'a'*64,'kind':'project'}],'groups':{'g':'development'},'roles':{'reviewer':{'version':'1'}},'tasks':[{'id':'q','query':'retry','role':'reviewer','role_version':'1','split':'development','group':'g'}]}
    path=root/'manifest.json'; path.write_text(json.dumps(manifest))
    output=tmp_path/'out'
    with pytest.raises(ValueError,match='source revision'):
        prepare_study(root,path,output)
    assert not output.exists()


def test_unlabeled_study_run_uses_copy_and_reports_no_quality(tmp_path):
    import hashlib
    from quix_knowledge.retrieval_study import prepare_study, run_prepared_study
    root=Path(__file__).resolve().parents[1]
    manifest=root/'experiments/retrieval/manifest.json'
    study=tmp_path/'study'; prepare_study(root,manifest,study)
    original=(study/'catalog.db').read_bytes()
    def switch(snapshot):
        candidate=next(c for c in snapshot['candidates'] if c['record_type']=='section')
        return {'status':'complete','reason':None,'state':{'evidence':[{'id':candidate['id'],'text':candidate['body'],'truncated':candidate['body_truncated']}]},'receipts':[]}
    result=run_prepared_study(root,manifest,study,tmp_path/'run',switch_runner=switch,count_tokens=len,tokenizer_name='fixture-characters',packet_tokens=10000)
    assert result['manifest']['label_provenance']['kind'] == 'unreviewed'
    assert result['variants']['baseline']['metrics']['unlabeled'] == 16
    assert result['variants']['switch']['metrics']['mean_recall'] is None
    assert hashlib.sha256((study/'catalog.db').read_bytes()).digest() == hashlib.sha256(original).digest()
    assert (tmp_path/'run'/'report.json').exists()


def test_study_rejects_changed_blind_task_even_if_stored_digest_is_unchanged(tmp_path):
    from quix_knowledge.retrieval_study import prepare_study, run_prepared_study
    root=Path(__file__).resolve().parents[1]
    manifest=root/'experiments/retrieval/manifest.json'
    study=tmp_path/'study'; prepare_study(root,manifest,study)
    path=study/'blind-review-packet.json'
    packet=json.loads(path.read_text()); packet['tasks'][0]['query']='different task'; path.write_text(json.dumps(packet))
    with pytest.raises(ValueError,match='packet'):
        run_prepared_study(root,manifest,study,tmp_path/'run',switch_runner=lambda _: {},count_tokens=len,tokenizer_name='fixture',packet_tokens=10000)
