import pytest

from quix_knowledge.ingest import ingest
from quix_knowledge.store import open_catalog


def test_adapter_returns_bounded_source_linked_packet(tmp_path):
    from quix_knowledge.context import serialize_packet
    from quix_knowledge.hitm import retrieve_context
    db = open_catalog(':memory:')
    path = tmp_path / 'manual.md'
    path.write_text('# Retry\nRetry after a timeout.')
    ingest(db, path)
    response = retrieve_context(db, {'version': 1, 'task': 'retry timeout', 'role': 'reviewer', 'role_version': '1', 'limit': 3, 'budget_characters': 3000})
    assert response['version'] == 1
    assert response['packet']['results'][0]['path'] == str(path)
    assert response['packet']['results'][0]['revision']
    assert response['packet']['results'][0]['start_line'] == 1
    assert response['packet']['tokenizer'] == 'json-characters'
    assert len(serialize_packet(response['packet'])) <= 3000


def test_adapter_refuses_source_changed_after_ingestion(tmp_path):
    from quix_knowledge.hitm import retrieve_context
    db = open_catalog(':memory:')
    path = tmp_path / 'manual.md'
    path.write_text('# Retry\nRetry after a timeout.')
    ingest(db, path)
    path.write_text('# Retry\nDo not retry.')
    with pytest.raises(ValueError, match='source'):
        retrieve_context(db, {'version': 1, 'task': 'retry', 'role': 'reviewer', 'role_version': '1', 'limit': 3, 'budget_characters': 3000})


def test_adapter_rechecks_after_search(tmp_path, monkeypatch):
    import quix_knowledge.hitm as contract
    db = open_catalog(':memory:')
    path = tmp_path / 'manual.md'
    path.write_text('# Retry\nRetry after a timeout.')
    ingest(db, path)
    original = contract.search
    def change_after_search(*args, **kwargs):
        rows = original(*args, **kwargs)
        path.write_text('# Retry\nDo not retry.')
        return rows
    monkeypatch.setattr(contract, 'search', change_after_search)
    with pytest.raises(ValueError, match='source'):
        contract.retrieve_context(db, {'version': 1, 'task': 'retry', 'role': 'reviewer', 'role_version': '1', 'limit': 3, 'budget_characters': 3000})


@pytest.mark.parametrize('input_request', [None, {}, {'version': True}, {'version': 2}, {'version': 1, 'task': 'x', 'role': 'r', 'role_version': '1', 'limit': True, 'budget_characters': 100}])
def test_adapter_rejects_malformed_request(input_request):
    from quix_knowledge.hitm import retrieve_context
    with pytest.raises(ValueError):
        retrieve_context(open_catalog(':memory:'), input_request)
