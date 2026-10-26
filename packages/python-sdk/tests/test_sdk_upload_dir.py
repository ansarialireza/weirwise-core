import pytest
import uuid
from unittest.mock import MagicMock
from weirwise import Weirwise
from weirwise.models import Document


def test_sdk_upload_directory_non_existent(tmp_path):
    client = Weirwise(base_url="http://test", api_key="ww_test")
    fake_dir = tmp_path / "does_not_exist"
    with pytest.raises(FileNotFoundError):
        client.documents.upload_directory(
            knowledge_base_id=uuid.uuid4(),
            directory_path=str(fake_dir),
        )


def test_sdk_upload_directory_empty(tmp_path):
    client = Weirwise(base_url="http://test", api_key="ww_test")
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()

    uploaded = client.documents.upload_directory(
        knowledge_base_id=uuid.uuid4(),
        directory_path=str(empty_dir),
    )
    assert uploaded == []


def test_sdk_upload_directory_matched_files(tmp_path):
    client = Weirwise(base_url="http://test", api_key="ww_test")
    kb_id = uuid.uuid4()

    # Create dummy directory with files
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "b.txt").write_text("file b", encoding="utf-8")
    (docs_dir / "a.txt").write_text("file a", encoding="utf-8")
    (docs_dir / "image.png").write_text("binary", encoding="utf-8")

    sub_dir = docs_dir / "sub"
    sub_dir.mkdir()
    (sub_dir / "c.txt").write_text("file c in sub", encoding="utf-8")

    # Mock upload method on documents resource
    mock_upload = MagicMock()
    mock_upload.side_effect = lambda knowledge_base_id, path: Document(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        knowledge_base_id=knowledge_base_id,
        filename=path,
        mime_type="text/plain",
        file_size=100,
        content_hash="abc123",
        status="pending",
        created_at="2026-10-26T00:00:00",
        updated_at="2026-10-26T00:00:00",
    )
    client.documents.upload = mock_upload

    # 1. Non-recursive .txt only
    docs = client.documents.upload_directory(
        knowledge_base_id=kb_id,
        directory_path=str(docs_dir),
        pattern="*.txt",
        recursive=False,
    )
    assert len(docs) == 2
    # Deterministic sorted order: a.txt before b.txt
    assert docs[0].filename.endswith("a.txt")
    assert docs[1].filename.endswith("b.txt")
    assert mock_upload.call_count == 2

    # 2. Recursive .txt
    mock_upload.reset_mock()
    docs_recursive = client.documents.upload_directory(
        knowledge_base_id=kb_id,
        directory_path=str(docs_dir),
        pattern="*.txt",
        recursive=True,
    )
    assert len(docs_recursive) == 3
    assert mock_upload.call_count == 3
