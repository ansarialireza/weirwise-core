import pytest
from httpx import Response
from weirwise import Weirwise
from weirwise.exceptions import AuthenticationError, NotFoundError


def test_sdk_initialization():
    client = Weirwise(base_url="http://localhost:8000", api_key="ww_test123")
    assert client.base_url == "http://localhost:8000"
    assert client.api_key == "ww_test123"
    assert client.knowledge_bases is not None
    assert client.documents is not None
    assert client.assistants is not None


def test_sdk_error_handling():
    client = Weirwise()

    # 401 AuthenticationError
    mock_resp_401 = Response(401, text="Unauthorized key")
    with pytest.raises(AuthenticationError):
        client._handle_response(mock_resp_401)

    # 404 NotFoundError
    mock_resp_404 = Response(404, text="Resource not found")
    with pytest.raises(NotFoundError):
        client._handle_response(mock_resp_404)


def test_sdk_context_manager():
    with Weirwise(base_url="http://localhost:8000", api_key="ww_test") as client:
        assert client.client.is_closed is False
    assert client.client.is_closed is True


def test_sdk_search_with_metadata_filters(monkeypatch):
    client = Weirwise(base_url="http://localhost:8000", api_key="ww_test")

    captured_payload = {}

    def mock_post(path, json=None, **kwargs):
        captured_payload["path"] = path
        captured_payload["json"] = json
        return {
            "results": [
                {
                    "chunk_id": "00000000-0000-0000-0000-000000000001",
                    "document_id": "00000000-0000-0000-0000-000000000002",
                    "content": "Test chunk",
                    "metadata": {"category": "finance"},
                    "similarity_score": 0.95,
                    "rank": 1,
                }
            ],
            "total": 1,
        }

    monkeypatch.setattr(client, "_post", mock_post)

    res = client.search(
        knowledge_base_id="00000000-0000-0000-0000-000000000003",
        query="financials",
        metadata_filters={"category": "finance"},
        score_threshold=0.7,
    )

    assert len(res) == 1
    assert res[0].content == "Test chunk"
    assert captured_payload["json"]["metadata_filters"] == {"category": "finance"}
    assert captured_payload["json"]["score_threshold"] == 0.7
