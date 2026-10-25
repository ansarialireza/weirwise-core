import uuid
from datetime import datetime
import pytest
from unittest.mock import MagicMock
from weirwise import Weirwise, Document
from weirwise.exceptions import IngestionFailedError, IngestionTimeoutError

BASE_URL = "http://testserver"
API_KEY = "ww_test_key"


def _make_doc(doc_id: uuid.UUID, status: str, error_message: str = None) -> Document:
    return Document(
        id=doc_id,
        tenant_id=uuid.uuid4(),
        knowledge_base_id=uuid.uuid4(),
        filename="test.txt",
        mime_type="text/plain",
        file_size=10,
        content_hash="abcd1234",
        status=status,
        error_message=error_message,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


def test_wait_for_completion_success():
    client = Weirwise(base_url=BASE_URL, api_key=API_KEY)
    doc_id = uuid.uuid4()

    # Mock responses for client.documents.get
    responses = [
        _make_doc(doc_id, "pending"),
        _make_doc(doc_id, "processing"),
        _make_doc(doc_id, "completed"),
    ]
    client.documents.get = MagicMock(side_effect=responses)

    doc = client.documents.wait_for_completion(doc_id, timeout=5.0, poll_interval=0.01)
    assert doc.id == doc_id
    assert doc.status == "completed"
    assert client.documents.get.call_count == 3


def test_wait_for_completion_failed():
    client = Weirwise(base_url=BASE_URL, api_key=API_KEY)
    doc_id = uuid.uuid4()

    responses = [
        _make_doc(doc_id, "processing"),
        _make_doc(doc_id, "failed", error_message="Embedding provider timeout"),
    ]
    client.documents.get = MagicMock(side_effect=responses)

    with pytest.raises(IngestionFailedError) as exc_info:
        client.documents.wait_for_completion(doc_id, timeout=5.0, poll_interval=0.01)

    assert "Embedding provider timeout" in str(exc_info.value)
    assert exc_info.value.document_id == doc_id


def test_wait_for_completion_timeout():
    client = Weirwise(base_url=BASE_URL, api_key=API_KEY)
    doc_id = uuid.uuid4()

    client.documents.get = MagicMock(return_value=_make_doc(doc_id, "processing"))

    with pytest.raises(IngestionTimeoutError) as exc_info:
        client.documents.wait_for_completion(doc_id, timeout=0.05, poll_interval=0.02)

    assert exc_info.value.document_id == doc_id
