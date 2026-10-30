from quix_knowledge.decisions import assess_role
from quix_knowledge.ingest import ingest
from quix_knowledge.retrieve import search
from quix_knowledge.store import open_catalog


def test_role_assessment_records_provisional_score_and_provenance(tmp_path):
    db=open_catalog(':memory:')
    path=tmp_path/'doc.md'
    path.write_text('# Retry\nReview retry failures.')
    ingest(db,path)
    section=db.execute('SELECT id FROM sections').fetchone()[0]
    def provider(state,question):
        assert question == 'role usefulness'
        return {'outcome':'unclear','provider':'fixture','model':'model-v1','probability':0.8,'usage':{'cost':0.01}}
    result=assess_role(db,section,'reviewer','1','Find implementation defects',provider)
    assert result['outcome'] == 'unclear'
    annotation=db.execute('SELECT * FROM role_annotations').fetchone()
    assert annotation['status'] == 'proposed'
    assert annotation['model'] == 'model-v1'
    assert annotation['score'] == 0.8
    row=search(db,'retry',variant='role',role='reviewer',role_version='1')[0]
    assert row['role_score_status'] == 'proposed'
    assert row['role_score'] == 0.8


def test_failed_role_assessment_records_unknown_without_inventing_score(tmp_path):
    db=open_catalog(':memory:')
    path=tmp_path/'doc.md'
    path.write_text('# Retry\nRetry after failure.')
    ingest(db,path)
    section=db.execute('SELECT id FROM sections').fetchone()[0]
    def fail(*args):
        raise TimeoutError()
    assert assess_role(db,section,'reviewer','1','Find defects',fail)['outcome'] == 'unknown'
    assert db.execute('SELECT count(*) FROM role_annotations').fetchone()[0] == 0
    assert db.execute('SELECT outcome FROM decision_receipts').fetchone()[0] == 'unknown'

def test_role_score_is_version_specific_and_stales_with_source(tmp_path):
    db=open_catalog(':memory:')
    path=tmp_path/'doc.md'
    path.write_text('# Retry\nReview retry failures.')
    ingest(db,path)
    section=db.execute('SELECT id FROM sections').fetchone()[0]
    provider=lambda *args: {'outcome':'unclear','provider':'fixture','probability':0.8}
    assess_role(db,section,'reviewer','1','Find defects',provider)
    assert search(db,'retry',variant='role',role='reviewer',role_version='2')[0]['role_score'] is None
    path.write_text('# Retry\nReview recovery behavior.')
    ingest(db,path)
    assert db.execute('SELECT status FROM role_annotations').fetchone()[0] == 'stale'
    assert search(db,'retry',variant='role',role='reviewer',role_version='1')[0]['role_score'] is None
