import pytest
from server.app.ingestion import chunk_text
from server.app.auth import generate_api_key, hash_api_key
from server.app.config import Settings


def test_api_key_generation_and_hashing():
    raw_key, key_hash = generate_api_key(prefix="ww_")
    assert raw_key.startswith("ww_")
    assert len(raw_key) > 20
    assert hash_api_key(raw_key) == key_hash
    # Ensure different key produces different hash
    raw_key_2, key_hash_2 = generate_api_key()
    assert raw_key != raw_key_2
    assert key_hash != key_hash_2


def test_chunking_boundaries():
    text = (
        "Weirwise is an open-source RAG infrastructure for developers.\n\n"
        "It provides document ingestion, vector retrieval, and conversational assistants.\n\n"
        "Security and tenant isolation are first-class principles."
    )
    chunks = chunk_text(text, chunk_size=100, chunk_overlap=20)
    assert len(chunks) >= 2
    assert "Weirwise" in chunks[0]
    # Overlap validation
    with pytest.raises(ValueError):
        chunk_text("Some text", chunk_size=50, chunk_overlap=60)


def test_chunking_empty():
    assert chunk_text("", chunk_size=100, chunk_overlap=20) == []
    assert chunk_text("   \n\n  ", chunk_size=100, chunk_overlap=20) == []


def test_config_defaults():
    settings = Settings()
    assert settings.port == 8000
    assert settings.embedding_dimensions == 1536
    assert settings.chunk_size == 500
