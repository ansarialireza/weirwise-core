import pytest
from pydantic import ValidationError
from server.app.config import Settings


def test_valid_settings():
    settings = Settings(
        database_url="postgresql+asyncpg://user:pass@localhost:5432/db",
        app_version="0.3.0",
        ingestion_mode="inline",
        chunk_size=500,
        chunk_overlap=50,
        db_pool_size=10,
    )
    assert settings.app_version == "0.3.0"
    assert settings.ingestion_mode == "inline"
    assert settings.chunk_size == 500
    assert settings.chunk_overlap == 50
    assert settings.db_pool_size == 10


def test_invalid_ingestion_mode():
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            database_url="postgresql+asyncpg://user:pass@localhost:5432/db",
            ingestion_mode="unsupported_mode",
        )
    assert "ingestion_mode" in str(exc_info.value)


def test_invalid_chunk_size():
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            database_url="postgresql+asyncpg://user:pass@localhost:5432/db",
            chunk_size=0,
        )
    assert "chunk_size must be a positive integer greater than 0" in str(exc_info.value)

    with pytest.raises(ValidationError) as exc_info:
        Settings(
            database_url="postgresql+asyncpg://user:pass@localhost:5432/db",
            chunk_size=-10,
        )
    assert "chunk_size must be a positive integer greater than 0" in str(exc_info.value)


def test_invalid_chunk_overlap():
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            database_url="postgresql+asyncpg://user:pass@localhost:5432/db",
            chunk_overlap=-1,
        )
    assert "chunk_overlap cannot be negative" in str(exc_info.value)

    with pytest.raises(ValidationError) as exc_info:
        Settings(
            database_url="postgresql+asyncpg://user:pass@localhost:5432/db",
            chunk_size=100,
            chunk_overlap=100,
        )
    assert "must be strictly less than chunk_size" in str(exc_info.value)


def test_invalid_db_pool_size():
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            database_url="postgresql+asyncpg://user:pass@localhost:5432/db",
            db_pool_size=0,
        )
    assert "db_pool_size must be greater than 0" in str(exc_info.value)
