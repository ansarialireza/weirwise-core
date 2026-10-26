# Weirwise Core v1.0.0 Execution Plan

## 1. Baseline Verification & Summary
- **Current Branch**: `main`
- **Initial Upstream Remote**: `origin` (`git@github.com:ansarialireza/weirwise-core.git`)
- **Last Pushed Commit**: `5ff0dd1` (Tagged `v0.2.0`)
- **Working Tree State at Start**: Pre-existing uncommitted changes implementing `v0.3.0` stabilization (score threshold filtering, SDK upload_directory, version alignment, health check endpoints, and regression tests).
- **Quality Checks Baseline**:
  - Ruff check & format: Passing (46 files verified).
  - Test Suite: 34 tests passing with `PYTHONPATH=".;packages/python-sdk"`.
  - Packaging: `weirwise` SDK and `weirwise_core` sdist & wheel build cleanly.
- **Identified Blockers / Constraints**:
  - Remote git authentication via SSH fails (`Permission denied (publickey)`).
  - Remote git authentication via HTTPS credentials currently requires interactive auth / token not present in environment.
  - Local Docker daemon is not active on Windows host (tests use mocked/SQLite-in-memory and unit mocks where PostgreSQL is absent).
  - Per Execution Rules (§4.3, §17, §19): In accordance with recovery protocol, all verified local commits will be cleanly created, and external push/release blockers are explicitly recorded without blocking engineering execution.

## 2. Major Architectural Components
- **Server API Layer (`server/app/api.py`, `server/app/main.py`)**: FastAPI REST endpoints for tenants, API keys, knowledge bases, documents, search, and health monitoring (`/health/live`, `/health/ready`).
- **Configuration & Settings (`server/app/config.py`)**: Pydantic `Settings` handling database URLs, embedding models, token bounds, chunk size/overlap constraints, and worker leases.
- **Ingestion Pipeline (`server/app/ingestion.py`)**: File validation, format parsers (txt, md, pdf), text chunking with overlap checks, and embedding orchestration.
- **Worker Execution (`server/app/worker.py`)**: Background job processing with status transitions (`pending` -> `processing` -> `completed` / `failed`), worker fencing, and lease timeouts.
- **Retrieval Engine (`server/app/retrieval.py`)**: Multi-mode retrieval supporting pgvector cosine distance SQL query and fallback in-memory cosine similarity ranking, with tenant/knowledge-base scoping and optional `score_threshold` filtering.
- **Python SDK (`packages/python-sdk/weirwise/`)**: Type-safe client wrapping all API endpoints with custom exception hierarchy, synchronous file and directory uploads, polling waiters, and type markers (`py.typed`).

## 3. Ordered Implementation Stages
- **Stage 1 (Phase 0 & 1 Baseline)**: Commit and record baseline v0.3.0 stabilization work and execution plan.
- **Stage 2 (Phase 2 Retrieval Correctness)**:
  - Audit `score_threshold` semantics in both pgvector SQL and in-memory fallback.
  - Ensure boundary values (0.0, 1.0) and edge cases (no embeddings, empty query, all scores below threshold) are fully tested and consistent.
  - Verify that SQL filtering produces identical ordering and scoring behavior as fallback ranking.
- **Stage 3 (Phase 3 Ingestion & Data Integrity)**:
  - Verify directory upload traversal, error handling on unreadable files, empty directories, and determinism.
  - Audit document error transitions, chunk deletion on document re-ingestion or failure, and memory usage.
- **Stage 4 (Phase 4 Security & Isolation)**:
  - Audit tenant isolation across all endpoints.
  - Validate path traversal protections in upload and ingestion.
  - Verify API key hashing, SQL injection safety (parameterized queries/ORM), and sanitized error responses.
- **Stage 5 (Phase 5 Public API & SDK Contract)**:
  - Establish stable v1 API contract in `CONTRACT.md` and SDK exports.
  - Verify type safety, docstrings, exception hierarchy, and context manager/cleanup support.
- **Stage 6 (Phase 6 Developer Experience & Docs)**:
  - Update README, examples, quickstart, and configuration guides.
  - Ensure all examples run against the v1 API.
- **Stage 7 (Phase 7 & 8 Packaging, CI, & Version Alignment)**:
  - Bump project versions to `1.0.0` across `pyproject.toml`, SDK `pyproject.toml`, `server/app/config.py`, and runtime health endpoints.
  - Update CI workflows with Python version matrix and packaging verification.
- **Stage 8 (Phase 11 & 12 Release Candidate Audit & v1.0.0 Preparation)**:
  - Compile `RELEASE_NOTES_v1.0.0.md` and `docs/engineering/v1_release_audit.md`.
  - Execute full test suite, build final distributions, tag Git commit `v1.0.0`, and attempt remote push / document remote credentials status.

## 4. Acceptance Criteria
- [x] Baseline verified with 34 tests passing and clean builds.
- [ ] Retrieval score threshold semantics verified across pgvector and in-memory modes.
- [ ] Ingestion lifecycle handles failures cleanly without corrupting state.
- [ ] Path traversal and tenant boundary security tests pass.
- [ ] SDK exports clean, type-annotated public interface with `py.typed`.
- [ ] Documentation and example scripts work against v1.0.0.
- [ ] Packaging builds sdist and wheel for both server and SDK with zero deprecation warnings if possible.
- [ ] All commits made incrementally with conventional commit messages.
- [ ] Git tag `v1.0.0` prepared and release notes documented.
