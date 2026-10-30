import hashlib
import sqlite3
import pytest
from quix_knowledge.store import open_catalog


def test_catalog_persists_and_enforces_references(tmp_path):
    path = tmp_path / 'catalog.db'
    db = open_catalog(path)
    digest = hashlib.sha256(b'hello').hexdigest()
    db.execute('INSERT INTO sources(id,path,revision,body) VALUES (?,?,?,?)', ('s1','a.md',digest,'hello'))
    db.commit()
    db.close()
    db = open_catalog(path)
    assert tuple(db.execute('SELECT path,revision FROM sources').fetchone()) == ('a.md', digest)
    with pytest.raises(sqlite3.IntegrityError):
        db.execute("INSERT INTO sections(id,source_id,title,body,start_line,end_line,generated) VALUES ('x','missing','x','x',1,1,0)")
