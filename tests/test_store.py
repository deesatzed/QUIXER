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

def test_version_one_catalog_migrates_without_losing_sources(tmp_path):
    path = tmp_path/'old.db'
    db = open_catalog(path)
    db.execute("INSERT INTO sources VALUES ('old','a.md','hash','body','current')")
    db.execute('DROP TABLE section_pages')
    db.execute('DROP TABLE extraction_warnings')
    db.execute('DROP TABLE generated_index_reviews')
    db.execute('DROP TABLE generated_index')
    db.execute('PRAGMA user_version=1')
    db.commit()
    db.close()
    reopened = open_catalog(path)
    assert reopened.execute('PRAGMA user_version').fetchone()[0] == 3
    assert reopened.execute("SELECT body FROM sources WHERE id='old'").fetchone()[0] == 'body'
    assert reopened.execute('SELECT count(*) FROM section_pages').fetchone()[0] == 0
    assert reopened.execute('SELECT count(*) FROM generated_index').fetchone()[0] == 0
