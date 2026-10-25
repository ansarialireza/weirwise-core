import logging
from typing import List, Dict, Any, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from server.app.models import DocumentChunk
from server.app.providers import EmbeddingProvider

logger = logging.getLogger(__name__)


async def retrieve_relevant_chunks(
    db: AsyncSession,
    tenant_id: UUID,
    knowledge_base_id: UUID,
    query: str,
    embedding_provider: EmbeddingProvider,
    top_k: int = 4,
    metadata_filters: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Retrieve top-k chunks for query using pgvector cosine distance, scoped to tenant & KB."""
    # 1. Generate query embedding
    query_embeddings = await embedding_provider.get_embeddings([query])
    query_vector = query_embeddings[0]

    # Check dialect for vector distance vs in-memory fallback
    bind = db.bind
    dialect_name = bind.dialect.name if bind else "postgresql"

    results = []

    if dialect_name == "postgresql":
        # Native pgvector cosine distance: embedding.cosine_distance(query_vector)
        # Cosine distance ranges from 0 (identical) to 2 (opposite). Similarity = 1 - distance.
        distance_col = DocumentChunk.embedding.cosine_distance(query_vector).label("distance")

        stmt = (
            select(DocumentChunk, distance_col)
            .where(
                DocumentChunk.tenant_id == tenant_id,
                DocumentChunk.knowledge_base_id == knowledge_base_id,
                DocumentChunk.embedding.isnot(None),
            )
            .order_by(distance_col.asc())
            .limit(top_k)
        )

        res = await db.execute(stmt)
        rows = res.all()

        for rank, (chunk, distance) in enumerate(rows, start=1):
            similarity_score = max(0.0, 1.0 - float(distance))
            results.append(
                {
                    "chunk_id": chunk.id,
                    "document_id": chunk.document_id,
                    "content": chunk.content,
                    "metadata": chunk.chunk_metadata or {},
                    "similarity_score": round(similarity_score, 4),
                    "rank": rank,
                }
            )
    else:
        # Fallback for testing environments without pgvector (e.g. SQLite test engine)
        import numpy as np

        stmt = select(DocumentChunk).where(
            DocumentChunk.tenant_id == tenant_id,
            DocumentChunk.knowledge_base_id == knowledge_base_id,
        )
        res = await db.execute(stmt)
        chunks = res.scalars().all()

        scored_chunks = []
        q_vec = np.array(query_vector)
        q_norm = np.linalg.norm(q_vec)

        for chunk in chunks:
            if chunk.embedding is not None:
                c_vec = np.array(chunk.embedding)
                c_norm = np.linalg.norm(c_vec)
                dot = np.dot(q_vec, c_vec)
                sim = dot / (q_norm * c_norm) if (q_norm * c_norm) > 0 else 0.0
                scored_chunks.append((chunk, float(sim)))

        scored_chunks.sort(key=lambda x: x[1], reverse=True)
        top_chunks = scored_chunks[:top_k]

        for rank, (chunk, score) in enumerate(top_chunks, start=1):
            results.append(
                {
                    "chunk_id": chunk.id,
                    "document_id": chunk.document_id,
                    "content": chunk.content,
                    "metadata": chunk.chunk_metadata or {},
                    "similarity_score": round(score, 4),
                    "rank": rank,
                }
            )

    return results
