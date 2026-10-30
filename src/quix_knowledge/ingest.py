"""Ingest UTF-8 text with line-level structural anchors."""
import hashlib
from pathlib import Path
import re

def ingest(db, path):
    path = Path(path).resolve()
    try:
        body = path.read_text(encoding='utf-8')
    except (OSError, UnicodeError) as exc:
        db.execute('INSERT INTO ingestion_failures VALUES (?,?)',(str(path),str(exc)))
        db.commit()
        return None
    if not body.strip():
        db.execute('INSERT INTO ingestion_failures VALUES (?,?)',(str(path),'empty text'))
        db.commit()
        return None
    revision = hashlib.sha256(body.encode()).hexdigest()
    source_id = hashlib.sha256((str(path)+'\0'+revision).encode()).hexdigest()
    existing = db.execute('SELECT status FROM sources WHERE id=?',(source_id,)).fetchone()
    if existing and existing[0] == 'current':
        return source_id
    lines = body.splitlines()
    headings = [(i, m.group(1)) for i,line in enumerate(lines) if (m := re.match(r'^#{1,6}\s+(.+?)\s*#*\s*$',line))]
    if not headings or headings[0][0] > 0:
        headings.insert(0,(0,'Unstructured text'))
    with db:
        db.execute("UPDATE topic_links SET status='stale' WHERE section_id IN (SELECT sections.id FROM sections JOIN sources ON sources.id=sections.source_id WHERE sources.path=? AND sources.status='current')",(str(path),))
        db.execute("UPDATE role_annotations SET status='stale' WHERE section_id IN (SELECT sections.id FROM sections JOIN sources ON sources.id=sections.source_id WHERE sources.path=? AND sources.status='current')",(str(path),))
        db.execute("UPDATE sources SET status='superseded' WHERE path=? AND status='current'",(str(path),))
        if existing:
            db.execute("UPDATE sources SET status='current' WHERE id=?",(source_id,))
            return source_id
        db.execute('INSERT INTO sources(id,path,revision,body) VALUES (?,?,?,?)',(source_id,str(path),revision,body))
        for n,(start,title) in enumerate(headings):
            end = headings[n+1][0] if n+1 < len(headings) else len(lines)
            sid = hashlib.sha256(f'{source_id}:{start}:{end}'.encode()).hexdigest()
            generated = int(title == 'Unstructured text' and not re.match(r'^#{1,6}\s+',lines[start]))
            db.execute('INSERT INTO sections VALUES (?,?,?,?,?,?,?)',(sid,source_id,title,'\n'.join(lines[start:end]),start+1,end,generated))
    return source_id
