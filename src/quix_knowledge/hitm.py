"""Versioned, local read contract for the proposed HITMCockpit adapter."""
import hashlib
import json
from pathlib import Path
import sqlite3
import sys

from .context import build_context_packet
from .retrieve import search
from .store import corpus_fingerprint


class SourceChanged(ValueError):
    pass


def _check_sources(db):
    for row in db.execute("SELECT path,revision FROM sources WHERE status='current'"):
        path = Path(row['path'])
        try:
            content = path.read_bytes() if path.suffix.lower() == '.pdf' else path.read_text(encoding='utf-8').encode('utf-8')
        except (OSError, UnicodeError) as exc:
            raise SourceChanged('source cannot be verified') from exc
        if hashlib.sha256(content).hexdigest() != row['revision']:
            raise SourceChanged('source changed since indexing')


def _validate_request(request):
    if not isinstance(request, dict) or type(request.get('version')) is not int or request['version'] != 1:
        raise ValueError('unsupported protocol version')
    if set(request) != {'version','task','role','role_version','limit','budget_characters'}:
        raise ValueError('request fields do not match protocol version')
    if not all(isinstance(request.get(k),str) and request[k].strip() for k in ('task','role','role_version')):
        raise ValueError('task, role and role version are required')
    if any(type(request.get(k)) is not int or request[k] < 0 for k in ('limit','budget_characters')):
        raise ValueError('nonnegative result limit and character budget are required')


def retrieve_context(db, request):
    """Return a character-budgeted packet; callers must revalidate before use."""
    _validate_request(request)
    _check_sources(db)
    fingerprint = corpus_fingerprint(db)
    rows = search(db,request['task'],variant='role',role=request['role'],role_version=request['role_version'],limit=request['limit'])
    _check_sources(db)
    if corpus_fingerprint(db) != fingerprint:
        raise ValueError('catalog changed during retrieval')
    packet = build_context_packet(request['task'],request['role'],request['role_version'],rows,budget=request['budget_characters'],count_tokens=len,tokenizer_name='json-characters',catalog_fingerprint=fingerprint)
    return {'version':1,'packet':packet}


def cli_context(catalog_path):
    """Read one bounded request and write one structured response without catalog writes."""
    def fail(code, message):
        print(json.dumps({'ok':False,'error':{'code':code,'message':message}}))
        return 1
    try:
        raw = sys.stdin.buffer.read(65537)
        if len(raw) > 65536:
            return fail('invalid_request','request exceeds 65536 bytes')
        request = json.loads(raw.decode('utf-8'))
        if not isinstance(request,dict) or type(request.get('limit')) is not int or request['limit'] > 100 or type(request.get('budget_characters')) is not int or request['budget_characters'] > 100000:
            return fail('invalid_request','request exceeds bounds or lacks required fields')
        _validate_request(request)
    except (UnicodeError, ValueError):
        return fail('invalid_request','request must be valid UTF-8 JSON')
    db = None
    try:
        uri = Path(catalog_path).resolve().as_uri() + '?mode=ro'
        db = sqlite3.connect(uri,uri=True)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA query_only=ON')
        if db.execute('PRAGMA user_version').fetchone()[0] != 7:
            return fail('catalog_unavailable','catalog schema version is unsupported')
        result = retrieve_context(db,request)
        print(json.dumps({'ok':True,**result},ensure_ascii=False))
        return 0
    except SourceChanged:
        return fail('source_changed','a source is missing, unreadable or changed')
    except ValueError as exc:
        code = 'budget_too_small' if str(exc) == 'budget is too small for packet metadata' else 'catalog_changed' if str(exc) == 'catalog changed during retrieval' else 'invalid_request'
        return fail(code,str(exc))
    except (sqlite3.Error,OSError):
        return fail('catalog_unavailable','catalog could not be read')
    finally:
        if db is not None:
            db.close()
