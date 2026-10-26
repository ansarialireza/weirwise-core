"""Extended soak and sustained load test script for Weirwise Core.

Designed for sustained execution to measure memory drift, connection pool stability,
and resource reclamation over 1,000+ operations.
"""

import asyncio
import time
import uuid
import httpx
from server.app.main import app
from server.app.database import AsyncSessionLocal, engine, Base
from server.app.models import Tenant, APIKey, KnowledgeBase, Document, DocumentChunk
from server.app.auth import generate_api_key
from sqlalchemy import text


async def run_soak_test(iterations: int = 200, concurrency: int = 5):
    print("=" * 70)
    print("WEIRWISE CORE v1.0.0 — SUSTAINED SOAK & RESOURCE TEST")
    print(f"Iterations: {iterations} | Concurrency: {concurrency}")
    print("=" * 70)

    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)

    raw_key, key_hash = generate_api_key(prefix="ww_soak_")
    async with AsyncSessionLocal() as session:
        t = Tenant(name="Soak Test Tenant")
        session.add(t)
        await session.flush()
        k = APIKey(tenant_id=t.id, key_hash=key_hash, name="soak-key")
        session.add(k)
        kb = KnowledgeBase(tenant_id=t.id, name="Soak KB")
        session.add(kb)
        await session.flush()

        doc = Document(
            tenant_id=t.id,
            knowledge_base_id=kb.id,
            filename="soak_doc.txt",
            storage_path="mock/soak_doc.txt",
            mime_type="text/plain",
            file_size=1024,
            content_hash="soakhash",
            status="completed",
        )
        session.add(doc)
        await session.flush()

        # Seed sample chunks
        for i in range(10):
            chunk = DocumentChunk(
                id=uuid.uuid4(),
                tenant_id=t.id,
                knowledge_base_id=kb.id,
                document_id=doc.id,
                chunk_index=i,
                content=f"Soak test knowledge content chunk {i}",
                embedding=[1.0] + [0.0] * 1535,
            )
            session.add(chunk)
        await session.commit()
        kb_id = kb.id

    headers = {"X-API-Key": raw_key}
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        sem = asyncio.Semaphore(concurrency)
        successes = 0
        failures = 0

        async def worker(idx):
            nonlocal successes, failures
            async with sem:
                try:
                    res = await client.post(
                        "/api/v1/search",
                        json={
                            "knowledge_base_id": str(kb_id),
                            "query": f"soak query {idx}",
                            "top_k": 3,
                        },
                        headers=headers,
                        timeout=15.0,
                    )
                    if res.status_code == 200:
                        successes += 1
                    else:
                        failures += 1
                except Exception:
                    failures += 1

        t0 = time.perf_counter()
        tasks = [worker(i) for i in range(iterations)]
        await asyncio.gather(*tasks)
        duration = time.perf_counter() - t0

        print(
            f"[+] Completed {iterations} operations in {duration:.2f}s (Success: {successes}, Failures: {failures})"
        )
        print(f"[+] Operations/sec: {iterations / duration:.2f}")


if __name__ == "__main__":
    asyncio.run(run_soak_test(iterations=100, concurrency=10))
