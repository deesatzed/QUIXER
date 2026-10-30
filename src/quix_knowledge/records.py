"""Create evidence-linked records and provisional annotations."""
def add_record(db, id, kind, body, producer, evidence=(), output_ref=None, supersedes=None):
    if kind == 'test_result' and not output_ref:
        raise ValueError('test results require an output reference')
    with db:
        db.execute('INSERT INTO records(id,kind,body,producer,supersedes,output_ref) VALUES (?,?,?,?,?,?)',(id,kind,body,producer,supersedes,output_ref))
        db.executemany('INSERT INTO evidence VALUES (?,?)',[(id,section) for section in evidence])
        if supersedes:
            db.execute("UPDATE records SET status='superseded' WHERE id=?",(supersedes,))

def add_topic(db, section_id, topic, method, status='proposed'):
    with db:
        db.execute('INSERT INTO topic_links(section_id,topic,method,status) VALUES (?,?,?,?)',(section_id,topic,method,status))

def add_role(db, section_id, role, role_version, score, method, source_revision, model=None):
    with db:
        db.execute('INSERT INTO role_annotations(section_id,role,role_version,score,method,source_revision,model) VALUES (?,?,?,?,?,?,?)',(section_id,role,role_version,score,method,source_revision,model))

def review_topic(db, link_id, decision, reviewer):
    """Record a named review of a current topic proposal."""
    if decision not in ('accepted','rejected') or not isinstance(reviewer,str) or not reviewer.strip():
        raise ValueError('accepted/rejected and a named reviewer are required')
    with db:
        current = db.execute("""SELECT t.id FROM topic_links t
            LEFT JOIN sections s ON s.id=t.section_id
            LEFT JOIN sources src ON src.id=s.source_id
            LEFT JOIN records r ON r.id=t.record_id
            WHERE t.id=? AND t.status='proposed' AND
              ((t.section_id IS NOT NULL AND src.status='current') OR
               (t.record_id IS NOT NULL AND r.status IN ('proposed','current') AND NOT EXISTS
                 (SELECT 1 FROM evidence e JOIN sections es ON es.id=e.section_id JOIN sources x ON x.id=es.source_id WHERE e.record_id=r.id AND x.status != 'current')))""",(link_id,)).fetchone()
        if current is None:
            raise ValueError('topic link is not a current proposal')
        db.execute('UPDATE topic_links SET status=? WHERE id=?',(decision,link_id))
        db.execute('INSERT INTO topic_link_reviews(link_id,reviewer,decision) VALUES (?,?,?)',(link_id,reviewer.strip(),decision))
