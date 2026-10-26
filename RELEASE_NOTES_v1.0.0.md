# Weirwise Core v1.0.0 Release Notes

We are thrilled to release **Weirwise Core v1.0.0**, the first stable production release of the open-source, modular Retrieval-Augmented Generation (RAG) infrastructure.

---

## Highlights

### 1. Hardened pgvector Native Retrieval & Filtering
- Native PostgreSQL `pgvector` cosine distance retrieval executed directly in the database (`conditions.append(DocumentChunk.embedding.cosine_distance(query_vector) <= max_distance)`).
- `score_threshold` parameter (0.0 to 1.0) validated in API request schemas, SDK client methods, and executed with mathematical parity across both native pgvector queries and in-memory fallback modes.
- Verified top-k ranking and score filtering with deterministic 1536-dimensional vectors against live PostgreSQL 16 + pgvector.

### 2. High-Performance Ingestion & Concurrency Control
- Atomic chunk replacement per document with foreign key integrity and worker fencing.
- Document deduplication via SHA-256 content hashing and row-level locking (`with_for_update()`).
- File size boundary validation preventing denial-of-service/resource exhaustion.

### 3. Production-Ready Python SDK (`weirwise`)
- Type-safe Python client with complete `py.typed` typing marker support (PEP 561).
- Context manager protocol support (`with Weirwise(...) as client:`).
- `upload_directory` helper enabling deterministic, sorted, recursive or non-recursive directory ingestion with pattern filtering and optional completion waiting.
- Clear public exception hierarchy (`AuthenticationError`, `NotFoundError`, `IngestionTimeoutError`, `IngestionFailedError`, `APIError`).

### 4. Operational Reliability & Diagnostics
- Liveness (`/health/live`) and readiness (`/health/ready`) endpoints verifying live database connectivity.
- CLI diagnostic tools (`python -m server.app.cli check-db`) verifying PostgreSQL connectivity and pgvector extension readiness.
- Modernized packaging eliminating deprecated license classifiers and warnings.

---

## Upgrade Guide & Compatibility

### Upgrading SDK
```bash
pip install --upgrade weirwise
```

### Upgrading Server
Ensure your PostgreSQL instance has `pgvector >= 0.2.5` installed and run database migrations:
```bash
alembic -c server/alembic.ini upgrade head
```
