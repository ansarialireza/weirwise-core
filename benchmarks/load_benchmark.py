"""End-to-end concurrency, throughput, and latency load benchmark for Weirwise Core.

Measures:
- Throughput (requests/sec)
- Latency percentiles: p50, p95, p99 (ms)
- Error rate and status code distribution
- Resource behavior under concurrent client load (1, 5, 10, 20 concurrent tasks)
"""

import asyncio
import time
import uuid
import math
import httpx
from server.app.main import app
from server.app.database import AsyncSessionLocal, engine, Base
from server.app.models import Tenant, APIKey, KnowledgeBase, Document, DocumentChunk
from server.app.auth import generate_api_key
from sqlalchemy import text


async def setup_bench_tenant_and_data(num_docs: int = 50, chunks_per_doc: int = 5):
    """Seed benchmark tenant, knowledge base, documents, and chunks."""
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)

    raw_key, key_hash = generate_api_key(prefix="ww_load_")

    async with AsyncSessionLocal() as session:
        tenant = Tenant(name="Load Test Tenant")
        session.add(tenant)
        await session.flush()

        api_key = APIKey(tenant_id=tenant.id, key_hash=key_hash, name="load-test-key")
        session.add(api_key)

        kb = KnowledgeBase(
            tenant_id=tenant.id,
            name="Load Test KB",
            description="Knowledge base for concurrent load testing",
        )
        session.add(kb)
        await session.flush()

        tenant_id = tenant.id
        kb_id = kb.id

        # Insert documents and chunks with 1536-dim vectors
        for d_idx in range(num_docs):
            doc = Document(
                tenant_id=tenant_id,
                knowledge_base_id=kb_id,
                filename=f"doc_{d_idx}.txt",
                storage_path=f"storage/doc_{d_idx}.txt",
                mime_type="text/plain",
                file_size=1024,
                content_hash=f"hash_{d_idx}",
                status="completed",
            )
            session.add(doc)
            await session.flush()

            for c_idx in range(chunks_per_doc):
                # Deterministic synthetic unit vector
                vec = [0.0] * 1536
                vec[c_idx % 100] = 1.0
                chunk = DocumentChunk(
                    id=uuid.uuid4(),
                    tenant_id=tenant_id,
                    knowledge_base_id=kb_id,
                    document_id=doc.id,
                    chunk_index=c_idx,
                    content=f"Benchmark content for document {d_idx} chunk {c_idx}. Highly relevant info.",
                    chunk_metadata={"doc_index": d_idx, "chunk_index": c_idx},
                    embedding=vec,
                )
                session.add(chunk)

        await session.commit()

    return raw_key, kb_id


def percentile(data: list[float], p: float) -> float:
    if not data:
        return 0.0
    s = sorted(data)
    k = (len(s) - 1) * (p / 100.0)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return s[int(k)]
    return s[int(f)] * (c - k) + s[int(c)] * (k - f)


async def run_concurrent_workload(
    raw_key: str,
    kb_id: uuid.UUID,
    concurrency_levels: list[int] = [1, 5, 10, 20],
    requests_per_level: int = 100,
):
    print("=" * 75)
    print("WEIRWISE CORE v1.0.0 — CONCURRENCY & WORKLOAD LOAD BENCHMARK")
    print("=" * 75)

    headers = {"X-API-Key": raw_key}
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # Warmup
        for _ in range(10):
            await client.post(
                "/api/v1/search",
                json={"knowledge_base_id": str(kb_id), "query": "warmup query", "top_k": 3},
                headers=headers,
            )

        print(
            f"{'Concurrency':<12} | {'Reqs':<6} | {'Throughput (req/s)':<20} | {'p50 (ms)':<10} | {'p95 (ms)':<10} | {'p99 (ms)':<10} | {'Errors':<6}"
        )
        print("-" * 88)

        benchmark_summary = []

        for concurrency in concurrency_levels:
            sem = asyncio.Semaphore(concurrency)
            latencies_ms = []
            errors = 0

            async def send_search_request(idx: int):
                nonlocal errors
                async with sem:
                    t0 = time.perf_counter()
                    try:
                        resp = await client.post(
                            "/api/v1/search",
                            json={
                                "knowledge_base_id": str(kb_id),
                                "query": f"test search query {idx}",
                                "top_k": 4,
                                "score_threshold": 0.0,
                            },
                            headers=headers,
                            timeout=30.0,
                        )
                        t1 = time.perf_counter()
                        if resp.status_code == 200:
                            latencies_ms.append((t1 - t0) * 1000.0)
                        else:
                            errors += 1
                    except Exception:
                        errors += 1

            start_time = time.perf_counter()
            tasks = [send_search_request(i) for i in range(requests_per_level)]
            await asyncio.gather(*tasks)
            total_duration = time.perf_counter() - start_time

            throughput = len(latencies_ms) / total_duration if total_duration > 0 else 0
            p50 = percentile(latencies_ms, 50)
            p95 = percentile(latencies_ms, 95)
            p99 = percentile(latencies_ms, 99)

            print(
                f"{concurrency:<12} | {requests_per_level:<6} | {throughput:<20.2f} | {p50:<10.2f} | {p95:<10.2f} | {p99:<10.2f} | {errors:<6}"
            )
            benchmark_summary.append(
                {
                    "concurrency": concurrency,
                    "throughput": throughput,
                    "p50": p50,
                    "p95": p95,
                    "p99": p99,
                    "errors": errors,
                }
            )

        print("=" * 75)
        return benchmark_summary


async def main():
    raw_key, kb_id = await setup_bench_tenant_and_data(num_docs=40, chunks_per_doc=5)
    await run_concurrent_workload(raw_key, kb_id)


if __name__ == "__main__":
    asyncio.run(main())
