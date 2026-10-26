# Weirwise Core v1.0.0 Execution Log

## 2026-10-26 - Stage 0: Baseline Verification & Environment Audit
- **Work Completed**:
  - Inspected working tree and commit history (`5ff0dd1`, matching `origin/main` at `v0.2.0`).
  - Identified pre-existing unstaged/untracked stabilization changes (v0.3.0 changes including `score_threshold`, `upload_directory`, health endpoints, and test coverage).
  - Executed baseline test suite (`34 passed in 51.46s`).
  - Ran code quality checks: `ruff check .` (passed), `ruff format --check .` (46 files verified).
  - Tested SDK packaging (`python -m build packages/python-sdk` -> `weirwise-0.3.0.tar.gz` and `.whl` generated).
  - Tested Core packaging (`python -m build .` -> `weirwise_core-0.3.0.tar.gz` and `.whl` generated).
  - Tested network/remote access: GitHub SSH connection reported `Permission denied (publickey)`.
- **Files Changed / Tracked**:
  - `docs/engineering/v1_execution_plan.md`
  - `docs/engineering/v1_execution_log.md`
- **Commit**: `5f58f2e` (`chore: establish v1 baseline documentation and v0.3.0 stabilization state`)

## 2026-10-26 - Stage 1: Retrieval Correctness & Real pgvector Integration
- **Work Completed**:
  - Discovered local running PostgreSQL 16.15 instance with pgvector 0.8.7 extension enabled.
  - Implemented real PostgreSQL integration test `test_native_pgvector_score_threshold_real_db` in `server/tests/test_score_threshold.py`.
  - Verified pgvector cosine distance filtering against live database with 1536-dimensional vectors.
  - Confirmed strict parity between native PostgreSQL pgvector SQL queries and in-memory fallback.
- **Files Changed**:
  - `server/tests/test_score_threshold.py`
- **Commit**: `d192398` (`test(retrieval): add live PostgreSQL pgvector cosine distance threshold integration test`)

## 2026-10-26 - Stage 2: SDK Hardening, Public Contract, and Context Manager
- **Work Completed**:
  - Verified SDK directory upload and polling behavior.
  - Added test coverage for SDK context manager lifecycle (`with Weirwise(...) as client:`).
  - Updated `CONTRACT.md` to reflect complete v1.0.0 API specification including health probes and `score_threshold`.
  - Updated `examples/basic_rag.py` to use context manager and score threshold filtering.
- **Files Changed**:
  - `CONTRACT.md`
  - `packages/python-sdk/tests/test_sdk.py`
  - `examples/basic_rag.py`
  - `README.md`
- **Commit**: `15c4e74` (`feat(sdk): add context manager lifecycle support, update API contract and examples`)

## 2026-10-26 - Stage 3: Version 1.0.0 Alignment, Packaging, and Clean Virtualenv Test
- **Work Completed**:
  - Updated versions to `1.0.0` in `pyproject.toml`, `packages/python-sdk/pyproject.toml`, `server/app/config.py`, and health tests.
  - Modernized `pyproject.toml` license syntax to eliminate setuptools deprecation warnings.
  - Built distributions and verified wheel installation in clean `$env:TEMP\ww_test_venv`.
  - Prepared `RELEASE_NOTES_v1.0.0.md` and `docs/engineering/v1_release_audit.md`.
- **Files Changed**:
  - `pyproject.toml`
  - `packages/python-sdk/pyproject.toml`
  - `server/app/config.py`
  - `server/tests/test_health_and_cli.py`
  - `.github/workflows/ci.yml`
  - `RELEASE_NOTES_v1.0.0.md`
  - `docs/engineering/v1_release_audit.md`
- **Commit**: `8a84389` (`chore(release): bump version to v1.0.0 and finalize release documentation`)
- **Git Tag**: `v1.0.0`

## 2026-10-26 - Stage 4: Performance, Stability, Concurrency, and Failure Injection Validation
- **Work Completed**:
  - Executed native vector retrieval benchmark: 2,500 vectors (1536-dim), measured 3.05ms p50 for HNSW vs 11.41ms exact search.
  - Built and executed concurrency load test `benchmarks/load_benchmark.py`: evaluated 1, 5, 10, 20 concurrent clients, measured peak throughput of 34.35 req/s with 0 errors across 400 requests.
  - Built and executed sustained soak test `benchmarks/soak_test.py`: 100 sustained operations with 10 concurrent workers, 0 failures, verified connection pool cleanup.
  - Built automated failure injection test suite `server/tests/test_failure_injection.py`: tested 503 embedding provider outage (graceful failure transition, no orphaned chunks), database degradation probe (/health/ready degraded while /health/live remains alive), and upload boundary validation (422/404).
  - Executed full 39-test regression suite: 39 passed in 26.14s.
  - Compiled detailed results in `docs/engineering/performance_and_stability.md`.
- **Files Changed**:
  - `benchmarks/load_benchmark.py`
  - `benchmarks/soak_test.py`
  - `server/tests/test_failure_injection.py`
  - `docs/engineering/performance_and_stability.md`
  - `docs/engineering/v1_execution_log.md`
