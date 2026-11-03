import pytest

from quix_knowledge.ingest import ingest
from quix_knowledge.records import add_record
from quix_knowledge.store import open_catalog


def test_snapshot_exports_real_candidates_and_agent_evidence(tmp_path):
    from quix_knowledge.switch_snapshot import build_snapshot
    db = open_catalog(':memory:')
    path = tmp_path/'manual.md'
    path.write_text('# Retry\nRetry after timeout.')
    ingest(db,path)
    section = db.execute('SELECT id FROM sections').fetchone()[0]
    add_record(db,'f1','finding','unverified finding','agent',evidence=[section])
    snapshot = build_snapshot(db,task='retry',role='reviewer',role_version='1',max_steps=5,max_characters=5000)
    source = next(c for c in snapshot['candidates'] if c['id'] == section)
    finding = next(c for c in snapshot['candidates'] if c['id'] == 'f1')
    assert source['path'] == str(path)
    assert source['tier'] == 'initial'
    assert finding['tier'] == 'broadened'
    assert finding['source_status'] == 'proposed'
    assert finding['evidence_sources'][0]['section_id'] == section
    assert finding['evidence_sources'][0]['revision'] == source['revision']
    assert snapshot['catalog_fingerprint']


def test_snapshot_refuses_changed_source(tmp_path):
    from quix_knowledge.switch_snapshot import build_snapshot
    db = open_catalog(':memory:')
    path = tmp_path/'manual.md'
    path.write_text('# Retry\nRetry after timeout.')
    ingest(db,path)
    path.write_text('# Retry\nChanged.')
    with pytest.raises(ValueError,match='source'):
        build_snapshot(db,task='retry',role='reviewer',role_version='1',max_steps=5,max_characters=5000)


def test_snapshot_includes_role_score_only_at_requested_proposal_scope(tmp_path):
    from quix_knowledge.records import add_role
    from quix_knowledge.switch_snapshot import build_snapshot
    db = open_catalog(':memory:')
    path = tmp_path/'manual.md'
    path.write_text('# Retry\nRetry after timeout.')
    ingest(db,path)
    section = db.execute('SELECT id FROM sections').fetchone()[0]
    revision = db.execute('SELECT revision FROM sources').fetchone()[0]
    add_role(db,section,'reviewer','1',0.8,'fixture',revision)
    hidden = build_snapshot(db,task='retry',role='reviewer',role_version='1',max_steps=5,max_characters=5000)
    included = build_snapshot(db,task='retry',role='reviewer',role_version='1',max_steps=5,max_characters=5000,include_proposed=True)
    assert hidden['candidates'][0]['role_annotation'] is None
    assert included['candidates'][0]['role_annotation']['score'] == 0.8
    assert included['candidates'][0]['role_annotation']['status'] == 'proposed'


def test_matched_snapshot_uses_same_sections_and_records_as_experiment(tmp_path):
    from quix_knowledge.indexing import index_source
    from quix_knowledge.switch_snapshot import build_snapshot
    db = open_catalog(':memory:')
    path = tmp_path/'manual.txt'
    path.write_text('Retry after timeout.\n\nRecord the failure.')
    index_source(db,path)
    section = db.execute('SELECT id FROM sections').fetchone()[0]
    add_record(db,'f1','finding','retry finding','agent',evidence=[section])
    snapshot = build_snapshot(db,task='retry',role='reviewer',role_version='1',max_steps=5,max_characters=5000,include_proposed=True,matched_candidates=True)
    assert {c['id'] for c in snapshot['candidates']} == {section,'f1'}
    assert snapshot['candidate_scope'] == 'sections_and_records'
