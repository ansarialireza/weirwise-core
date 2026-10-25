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
