# Changelog

All notable changes to Weirwise Core will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-10-26

### Added
- **Worker Leasing & Fencing Tokens**: Distributed job ownership with periodic lease heartbeats (`_heartbeat_loop`), stale job reclamation (`reclaim_stale_jobs`), monotonically increasing `generation` counters, and unique UUID `claim_token` validation. Stale workers are rejected before committing.
- **Atomic Chunk Replacement**: Safe text extraction and embedding generation staged in-memory prior to database changes; chunk replacement and document status updates execute in a single guarded transaction.
- **Concurrent Upload Deduplication**: Composite unique constraint `(knowledge_base_id, content_hash)` on documents; idempotent responses (HTTP 200 for completed, HTTP 202 for in-progress) and concurrency-safe single retry claims for failed documents.
- **API Pagination**: Standardized `limit` (1-100, default 50) and `offset` (>=0, default 0) with stable deterministic ordering (`created_at DESC, id DESC`) across `/knowledge-bases`, `/documents`, and `/assistants`.
- **Python SDK Ergonomics**: Added `wait_for_completion(doc_id, timeout, poll_interval)` and typed exceptions `IngestionTimeoutError` and `IngestionFailedError`.
- **Reproducible Vector Retrieval Benchmark**: Added `benchmarks/retrieval_benchmark.py` testing 2,500 1536-dimensional unit vectors against exact sequential scan ground truth, verifying HNSW index scan eligibility, latency percentiles, and monotonic Recall@5 / Recall@10.

## [0.1.0] - 2026-10-25

### Added
- **Core Architecture**: Modular monolith with FastAPI, SQLAlchemy 2.x, Alembic, and PostgreSQL + pgvector.
- **Tenant Isolation**: Complete tenant data isolation across knowledge bases, documents, chunks, assistants, and messages.
- **Authentication**: Secure API key generation with SHA-256 hashing.
- **Ingestion Pipeline**: Text extraction for PDF, Markdown, and TXT files with paragraph/sentence chunking.
- **Asynchronous Worker**: Queue-based background worker processing ingestion jobs using PostgreSQL `FOR UPDATE SKIP LOCKED`.
- **Vector Retrieval**: Native pgvector cosine distance similarity retrieval.
- **AI Assistant Runtime**: Context assembly, prompt construction with untrusted context demarcation, and source citation.
- **OpenAI-compatible Providers**: Embedding and Chat completion integrations with deterministic fallback test doubles.
- **Python SDK**: Standalone installable client under `packages/python-sdk` with typed resources.
- **Docker Compose**: Containerized multi-service deployment with healthchecks and persistent volumes.
- **Automated CI**: GitHub Actions workflow covering linting, migrations, and integration test execution.
