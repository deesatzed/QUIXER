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
