"""Single-writer SQLite catalog."""
import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS sources(id TEXT PRIMARY KEY,path TEXT NOT NULL,revision TEXT NOT NULL,body TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'current' CHECK(status IN ('current','superseded','invalidated')), UNIQUE(path,revision));
CREATE TABLE IF NOT EXISTS sections(id TEXT PRIMARY KEY,source_id TEXT NOT NULL REFERENCES sources(id),title TEXT NOT NULL,body TEXT NOT NULL,start_line INTEGER NOT NULL,end_line INTEGER NOT NULL,generated INTEGER NOT NULL CHECK(generated IN (0,1)));
CREATE TABLE IF NOT EXISTS records(id TEXT PRIMARY KEY,kind TEXT NOT NULL CHECK(kind IN ('finding','decision','test_result')),body TEXT NOT NULL,producer TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'proposed' CHECK(status IN ('proposed','current','superseded','invalidated')),supersedes TEXT REFERENCES records(id),output_ref TEXT);
CREATE TABLE IF NOT EXISTS evidence(record_id TEXT NOT NULL REFERENCES records(id),section_id TEXT NOT NULL REFERENCES sections(id),PRIMARY KEY(record_id,section_id));
CREATE TABLE IF NOT EXISTS topic_links(id INTEGER PRIMARY KEY,section_id TEXT REFERENCES sections(id),record_id TEXT REFERENCES records(id),topic TEXT NOT NULL,method TEXT NOT NULL,status TEXT NOT NULL CHECK(status IN ('proposed','accepted','rejected','stale')),CHECK((section_id IS NULL) != (record_id IS NULL)));
CREATE TABLE IF NOT EXISTS role_annotations(id INTEGER PRIMARY KEY,section_id TEXT REFERENCES sections(id),record_id TEXT REFERENCES records(id),role TEXT NOT NULL,role_version TEXT NOT NULL,score REAL NOT NULL CHECK(score BETWEEN 0 AND 1),method TEXT NOT NULL,model TEXT,source_revision TEXT,status TEXT NOT NULL DEFAULT 'proposed' CHECK(status IN ('proposed','accepted','stale')),CHECK((section_id IS NULL) != (record_id IS NULL)));
CREATE TABLE IF NOT EXISTS decision_receipts(id INTEGER PRIMARY KEY,provider TEXT NOT NULL,model TEXT,outcome TEXT NOT NULL,detail TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS ingestion_failures(path TEXT NOT NULL,reason TEXT NOT NULL);
"""

def open_catalog(path):
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys=ON')
    version = db.execute('PRAGMA user_version').fetchone()[0]
    if version not in (0, 1):
        db.close()
        raise ValueError(f'Unsupported schema version: {version}')
    db.executescript(SCHEMA)
    db.execute('PRAGMA user_version=1')
    db.commit()
    return db
