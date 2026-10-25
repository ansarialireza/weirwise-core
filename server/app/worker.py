import asyncio
import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from server.app.models import IngestionJob, Document, DocumentChunk
from server.app.ingestion import extract_text_from_file, chunk_text
from server.app.providers import EmbeddingProvider
from server.app.config import Settings
from server.app.database import AsyncSessionLocal

logger = logging.getLogger(__name__)


async def process_document_job(
    job_id,
    settings: Settings,
    embedding_provider: EmbeddingProvider,
    db: Optional[AsyncSession] = None,
    db_session_factory=None,
):
    """Executes the ingestion pipeline for a single queued job."""
    close_db = False
    if db is None:
        factory = db_session_factory or AsyncSessionLocal
        db = factory()
        close_db = True

    try:
        # 1. Fetch Job
        job_res = await db.execute(select(IngestionJob).where(IngestionJob.id == job_id))
        job = job_res.scalars().first()
        if not job or job.status == "completed":
            return

        job.status = "processing"
        job.attempts += 1
        await db.commit()

        # 2. Fetch Document
        doc_res = await db.execute(select(Document).where(Document.id == job.document_id))
        doc = doc_res.scalars().first()
        if not doc:
            job.status = "failed"
            job.error_message = "Document record not found"
            await db.commit()
            return

        doc.status = "processing"
        await db.commit()

        # 3. Extract text
        try:
            raw_text = extract_text_from_file(doc.storage_path, doc.mime_type)
        except Exception as e:
            logger.error(f"Failed to extract text from {doc.storage_path}: {e}")
            doc.status = "failed"
            doc.error_message = f"Text extraction failed: {str(e)}"
            job.status = "failed"
            job.error_message = doc.error_message
            await db.commit()
            return

        # 4. Chunk text
        chunks = chunk_text(
            raw_text,
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
        )

        if not chunks:
            # Handle empty document gracefully
            doc.status = "completed"
            job.status = "completed"
            await db.commit()
            return

        # 5. Generate embeddings in batches
        all_embeddings = []
        batch_size = settings.embedding_batch_size
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i : i + batch_size]
            embeddings = await embedding_provider.get_embeddings(batch)
            all_embeddings.extend(embeddings)

        # 6. Store Chunks
        for idx, (chunk_content, emb) in enumerate(zip(chunks, all_embeddings)):
            chunk_record = DocumentChunk(
                tenant_id=doc.tenant_id,
                knowledge_base_id=doc.knowledge_base_id,
                document_id=doc.id,
                chunk_index=idx,
                content=chunk_content,
                chunk_metadata={"filename": doc.filename, "chunk_index": idx},
                embedding=emb,
            )
            db.add(chunk_record)

        doc.status = "completed"
        job.status = "completed"
        await db.commit()
        logger.info(f"Ingestion completed for document {doc.id} ({len(chunks)} chunks)")

    except Exception as e:
        logger.exception(f"Unhandled error during ingestion job {job_id}: {e}")
        await db.rollback()
        try:
            # Re-fetch to update status
            job_res = await db.execute(select(IngestionJob).where(IngestionJob.id == job_id))
            job = job_res.scalars().first()
            if job:
                job.error_message = str(e)
                if job.attempts >= job.max_attempts:
                    job.status = "failed"
                else:
                    job.status = "pending"  # eligible for retry
            doc_res = await db.execute(select(Document).where(Document.id == job.document_id))
            doc = doc_res.scalars().first()
            if doc and job.status == "failed":
                doc.status = "failed"
                doc.error_message = str(e)
            await db.commit()
        except Exception:
            pass
    finally:
        if close_db:
            await db.close()


async def run_worker_loop():
    """Background worker polling ingestion jobs using PostgreSQL SKIP LOCKED."""
    from server.app.config import get_settings
    from server.app.providers import OpenAIEmbeddingProvider

    settings = get_settings()
    provider = OpenAIEmbeddingProvider(settings)
    logger.info("Starting Weirwise background worker...")

    while True:
        try:
            async with AsyncSessionLocal() as session:
                # Atomically claim pending job
                stmt = (
                    select(IngestionJob)
                    .where(IngestionJob.status == "pending")
                    .order_by(IngestionJob.created_at.asc())
                    .limit(1)
                )
                # If postgresql, use with_for_update(skip_locked=True)
                if session.bind and session.bind.dialect.name == "postgresql":
                    stmt = stmt.with_for_update(skip_locked=True)

                res = await session.execute(stmt)
                job = res.scalars().first()

                if job:
                    job_id = job.id
                    logger.info(f"Worker claimed job {job_id}")
                    await process_document_job(job_id, settings, provider, db=session)
                else:
                    await asyncio.sleep(settings.worker_poll_interval)
        except Exception as e:
            logger.error(f"Worker loop error: {e}")
            await asyncio.sleep(settings.worker_poll_interval)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_worker_loop())
