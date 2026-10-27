"""Adversarial and extreme edge case testing for Weirwise Core.

Tests:
1. RTL, Persian/Arabic Unicode text, emoji, complex scripts chunking and retrieval
2. Extreme whitespace, empty text, single character text chunking
3. Vector search deterministic tie-breaking on identical distance vectors
4. Non-existent and malformed payload injection (boundary verification)
5. Null vs missing field handling in search request schemas
"""

import pytest
import uuid
from httpx import AsyncClient, ASGITransport
from server.app.main import app
from server.app.ingestion import chunk_text
from server.app.retrieval import retrieve_relevant_chunks
from server.app.models import Tenant, APIKey, KnowledgeBase, Document, DocumentChunk
from server.app.database import AsyncSessionLocal
from server.app.auth import generate_api_key


def test_adversarial_unicode_and_rtl_chunking():
    # Persian text with ZWNJ (Zero Width Non-Joiner) and emojis
    persian_text = (
        "هوش مصنوعی و یادگیری ماشین یکی از مهم‌ترین فناوری‌های عصر حاضر هستند. 🚀\n\n"
        "سیستم‌های بازیابی اطلاعات (RAG) به مدل‌های زبانی کمک می‌کنند تا پاسخ‌های دقیق‌تری ارائه دهند.\n\n"
        "این یک متن آزمایشی است که شامل کاراکترهای نیم‌فاصله (‌) و اعراب و شکلک‌های متنوع می‌باشد: 🔍 ✨ 📊"
    )
    chunks = chunk_text(persian_text, chunk_size=100, chunk_overlap=20)
    assert len(chunks) >= 3
    # Ensure Unicode characters and emojis are preserved intact
    assert any("هوش مصنوعی" in c for c in chunks)
    assert any("🚀" in c for c in chunks)
    assert any("نیم‌فاصله" in c for c in chunks)


def test_adversarial_boundary_text_chunking():
    # 1. Empty string
    assert chunk_text("", chunk_size=500, chunk_overlap=50) == []
    # 2. Only whitespace
    assert chunk_text("   \n\n   \t  \n  ", chunk_size=500, chunk_overlap=50) == []
    # 3. Single character
    assert chunk_text("A", chunk_size=500, chunk_overlap=50) == ["A"]
    # 4. Paragraph exactly equal to chunk_size
    exact_text = "x" * 100
    chunks = chunk_text(exact_text, chunk_size=100, chunk_overlap=10)
    assert len(chunks) == 1
    assert len(chunks[0]) == 100


@pytest.mark.asyncio
async def test_deterministic_tie_breaking_in_vector_retrieval():
    """Verify that identical distance vectors break ties deterministically by chunk_index and id."""
    tenant_name = f"TieBreak-{uuid.uuid4().hex[:6]}"
    raw_key, key_hash = generate_api_key(prefix="ww_tie_")

    async with AsyncSessionLocal() as session:
        t = Tenant(name=tenant_name)
        session.add(t)
        await session.flush()
        k = APIKey(tenant_id=t.id, key_hash=key_hash, name="tie-key")
        session.add(k)
        kb = KnowledgeBase(tenant_id=t.id, name="Tie KB")
        session.add(kb)
        await session.flush()

        doc = Document(
            tenant_id=t.id,
            knowledge_base_id=kb.id,
            filename="tie.txt",
            storage_path="mock/tie.txt",
            mime_type="text/plain",
            file_size=100,
            content_hash="tiehash",
            status="completed",
        )
        session.add(doc)
        await session.flush()

        # Insert 3 chunks with identical embeddings but different chunk_index
        fixed_vec = [1.0] + [0.0] * 1535
        c0 = DocumentChunk(
            id=uuid.uuid4(),
            tenant_id=t.id,
            knowledge_base_id=kb.id,
            document_id=doc.id,
            chunk_index=0,
            content="Chunk Zero",
            embedding=fixed_vec,
        )
        c1 = DocumentChunk(
            id=uuid.uuid4(),
            tenant_id=t.id,
            knowledge_base_id=kb.id,
            document_id=doc.id,
            chunk_index=1,
            content="Chunk One",
            embedding=fixed_vec,
        )
        c2 = DocumentChunk(
            id=uuid.uuid4(),
            tenant_id=t.id,
            knowledge_base_id=kb.id,
            document_id=doc.id,
            chunk_index=2,
            content="Chunk Two",
            embedding=fixed_vec,
        )
        session.add_all([c0, c1, c2])
        await session.commit()
        tenant_id = t.id
        kb_id = kb.id

    class MockProvider:
        async def get_embeddings(self, texts):
            return [[1.0] + [0.0] * 1535 for _ in texts]

    async with AsyncSessionLocal() as session:
        res = await retrieve_relevant_chunks(
            db=session,
            tenant_id=tenant_id,
            knowledge_base_id=kb_id,
            query="test query",
            embedding_provider=MockProvider(),
            top_k=3,
        )
        assert len(res) == 3
        # Must be ordered deterministically by chunk_index asc when similarity scores tie (1.0)
        assert [r["content"] for r in res] == ["Chunk Zero", "Chunk One", "Chunk Two"]
        assert all(r["similarity_score"] == 1.0 for r in res)


@pytest.mark.asyncio
async def test_search_endpoint_with_null_and_boundary_score_thresholds():
    """Verify search endpoint handles score_threshold: 0.0, 1.0, null, and rejects out-of-range floats."""
    transport = ASGITransport(app=app)
    raw_key, key_hash = generate_api_key(prefix="ww_bound_")

    async with AsyncSessionLocal() as session:
        t = Tenant(name="Boundaries Tenant")
        session.add(t)
        await session.flush()
        k = APIKey(tenant_id=t.id, key_hash=key_hash, name="bound-key")
        session.add(k)
        kb = KnowledgeBase(tenant_id=t.id, name="Bound KB")
        session.add(kb)
        await session.commit()
        kb_id = str(kb.id)

    headers = {"X-API-Key": raw_key}

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Null score_threshold
        r_null = await client.post(
            "/api/v1/search",
            json={"knowledge_base_id": kb_id, "query": "hello", "score_threshold": None},
            headers=headers,
        )
        assert r_null.status_code == 200

        # 2. Threshold = 0.0
        r_zero = await client.post(
            "/api/v1/search",
            json={"knowledge_base_id": kb_id, "query": "hello", "score_threshold": 0.0},
            headers=headers,
        )
        assert r_zero.status_code == 200

        # 3. Threshold = 1.0
        r_one = await client.post(
            "/api/v1/search",
            json={"knowledge_base_id": kb_id, "query": "hello", "score_threshold": 1.0},
            headers=headers,
        )
        assert r_one.status_code == 200

        # 4. Out-of-bounds negative -> 422
        r_neg = await client.post(
            "/api/v1/search",
            json={"knowledge_base_id": kb_id, "query": "hello", "score_threshold": -0.01},
            headers=headers,
        )
        assert r_neg.status_code == 422

        # 5. Out-of-bounds > 1.0 -> 422
        r_over = await client.post(
            "/api/v1/search",
            json={"knowledge_base_id": kb_id, "query": "hello", "score_threshold": 1.01},
            headers=headers,
        )
        assert r_over.status_code == 422
