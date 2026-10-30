"""Versioned, local read contract for the proposed HITMCockpit adapter."""
import hashlib
from pathlib import Path

from .context import build_context_packet
from .retrieve import search
from .store import corpus_fingerprint


def _check_sources(db):
    for row in db.execute("SELECT path,revision FROM sources WHERE status='current'"):
        path = Path(row['path'])
        try:
            content = path.read_bytes() if path.suffix.lower() == '.pdf' else path.read_text(encoding='utf-8').encode('utf-8')
        except (OSError, UnicodeError) as exc:
            raise ValueError('source cannot be verified') from exc
        if hashlib.sha256(content).hexdigest() != row['revision']:
            raise ValueError('source changed since indexing')


def retrieve_context(db, request):
    """Return a character-budgeted packet; callers must revalidate before use."""
    if not isinstance(request, dict) or type(request.get('version')) is not int or request['version'] != 1:
        raise ValueError('unsupported protocol version')
    if not all(isinstance(request.get(k),str) and request[k].strip() for k in ('task','role','role_version')):
        raise ValueError('task, role and role version are required')
    if any(type(request.get(k)) is not int or request[k] < 0 for k in ('limit','budget_characters')):
        raise ValueError('nonnegative result limit and character budget are required')
    _check_sources(db)
    fingerprint = corpus_fingerprint(db)
    rows = search(db,request['task'],variant='role',role=request['role'],role_version=request['role_version'],limit=request['limit'])
    _check_sources(db)
    if corpus_fingerprint(db) != fingerprint:
        raise ValueError('catalog changed during retrieval')
    packet = build_context_packet(request['task'],request['role'],request['role_version'],rows,budget=request['budget_characters'],count_tokens=len,tokenizer_name='json-characters',catalog_fingerprint=fingerprint)
    return {'version':1,'packet':packet}
