import pytest
import uuid
from unittest.mock import AsyncMock
from server.app.retrieval import retrieve_relevant_chunks
from server.app.models import DocumentChunk
from server.app.schemas import SearchRequest
from pydantic import ValidationError


class DummyEmbeddingProvider:
    async def get_embeddings(self, texts):
        return [[1.0, 0.0, 0.0] for _ in texts]


def test_search_request_score_threshold_validation():
    kb_id = uuid.uuid4()
    # Valid thresholds
    req1 = SearchRequest(knowledge_base_id=kb_id, query="test", score_threshold=0.5)
    assert req1.score_threshold == 0.5

    req2 = SearchRequest(knowledge_base_id=kb_id, query="test", score_threshold=0.0)
    assert req2.score_threshold == 0.0

    req3 = SearchRequest(knowledge_base_id=kb_id, query="test", score_threshold=1.0)
    assert req3.score_threshold == 1.0

    req4 = SearchRequest(knowledge_base_id=kb_id, query="test", score_threshold=None)
    assert req4.score_threshold is None

    # Invalid thresholds < 0.0 or > 1.0
    with pytest.raises(ValidationError):
        SearchRequest(knowledge_base_id=kb_id, query="test", score_threshold=-0.1)

    with pytest.raises(ValidationError):
        SearchRequest(knowledge_base_id=kb_id, query="test", score_threshold=1.1)


@pytest.mark.asyncio
async def test_retrieval_score_threshold_filtering():
    tenant_id = uuid.uuid4()
    kb_id = uuid.uuid4()

    # Mock DB session in fallback (in-memory) mode
    chunk_high = DocumentChunk(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        knowledge_base_id=kb_id,
        document_id=uuid.uuid4(),
        content="High similarity match",
        embedding=[1.0, 0.0, 0.0],  # cosine sim = 1.0
        chunk_metadata={},
    )
    chunk_low = DocumentChunk(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        knowledge_base_id=kb_id,
        document_id=uuid.uuid4(),
        content="Low similarity match",
        embedding=[0.0, 1.0, 0.0],  # orthogonal, cosine sim = 0.0
        chunk_metadata={},
    )

    class MockResult:
        def scalars(self):
            class MockScalars:
                def all(self):
                    return [chunk_high, chunk_low]

            return MockScalars()

    mock_db = AsyncMock()
    mock_db.bind.dialect.name = "sqlite"
    mock_db.execute.return_value = MockResult()

    # 1. No threshold -> returns both
    all_res = await retrieve_relevant_chunks(
        db=mock_db,
        tenant_id=tenant_id,
        knowledge_base_id=kb_id,
        query="test",
        embedding_provider=DummyEmbeddingProvider(),
        top_k=5,
        score_threshold=None,
    )
    assert len(all_res) == 2
    assert all_res[0]["similarity_score"] == 1.0
    assert all_res[1]["similarity_score"] == 0.0

    # 2. Threshold = 0.5 -> filters out chunk_low
    filtered_res = await retrieve_relevant_chunks(
        db=mock_db,
        tenant_id=tenant_id,
        knowledge_base_id=kb_id,
        query="test",
        embedding_provider=DummyEmbeddingProvider(),
        top_k=5,
        score_threshold=0.5,
    )
    assert len(filtered_res) == 1
    assert filtered_res[0]["content"] == "High similarity match"
    assert filtered_res[0]["similarity_score"] == 1.0

    # 3. Very high threshold -> empty results
    empty_res = await retrieve_relevant_chunks(
        db=mock_db,
        tenant_id=tenant_id,
        knowledge_base_id=kb_id,
        query="test",
        embedding_provider=DummyEmbeddingProvider(),
        top_k=5,
        score_threshold=1.0001,  # even if passed directly to function
    )
    assert len(empty_res) == 0
