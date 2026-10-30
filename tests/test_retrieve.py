from quix_knowledge.store import open_catalog
from quix_knowledge.ingest import ingest
from quix_knowledge.records import add_topic, add_role
from quix_knowledge.records import add_record
from quix_knowledge.retrieve import search

def test_topic_and_role_keep_relevant_source(tmp_path):
    db = open_catalog(':memory:')
    path = tmp_path/'doc.md'
    path.write_text('# Interface\nservice protocol\n# Tests\nservice failures\n')
    source = ingest(db,path)
    sections = db.execute('SELECT id FROM sections WHERE source_id=? ORDER BY start_line',(source,)).fetchall()
    add_topic(db,sections[1][0],'resilience','manual','accepted')
    rev = db.execute('SELECT revision FROM sources WHERE id=?',(source,)).fetchone()[0]
    add_role(db,sections[1][0],'reviewer','1',1.0,'manual',rev)
    results = search(db,'service',variant='role',role='reviewer',role_version='1')
    assert len(results) == 2
    assert results[0]['title'] == 'Tests'
    assert results[0]['path'] == str(path.resolve())
    assert search(db,'resilience',variant='topic')[0]['title'] == 'Tests'

def test_agent_claim_is_returned_with_evidence_and_failure_receipt(tmp_path):
    db = open_catalog(':memory:')
    path = tmp_path/'doc.md'
    path.write_text('# Design\nretry behavior\n')
    ingest(db,path)
    sid = db.execute('SELECT id FROM sections').fetchone()[0]
    add_record(db,'finding','finding','retry failure is possible','reviewer',evidence=[sid])
    add_record(db,'unsupported','finding','retry claim','reviewer')
    def broken(state, question):
        raise TimeoutError()
    results = search(db,'retry',variant='decision',provider=broken)
    by_id = {r['id']:r for r in results}
    assert by_id['finding']['evidence'] == [sid]
    assert by_id['unsupported']['unsupported'] is True
    assert len(results) == 3
    assert db.execute('SELECT COUNT(*) FROM decision_receipts').fetchone()[0] == 3
