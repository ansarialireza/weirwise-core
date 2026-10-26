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
- **Commands Executed**:
  - `pytest server/tests/test_score_threshold.py -v` (3 passed)

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
- **Commands Executed**:
  - `pytest packages/python-sdk/tests/ -v` (9 passed)

## 2026-10-26 - Stage 3: Version 1.0.0 Alignment, Packaging, and Clean Virtualenv Test
- **Work Completed**:
  - Updated versions to `1.0.0` in `pyproject.toml`, `packages/python-sdk/pyproject.toml`, `server/app/config.py`, and health tests.
  - Modernized `pyproject.toml` license syntax to eliminate setuptools deprecation warnings.
  - Updated GitHub Actions CI workflow to build both packages.
  - Built distributions: `weirwise-1.0.0.tar.gz`, `weirwise-1.0.0-py3-none-any.whl`, `weirwise_core-1.0.0.tar.gz`, `weirwise_core-1.0.0-py3-none-any.whl`.
  - Verified wheel in isolated virtualenv (`$env:TEMP\ww_test_venv`): installed, imported, and verified client instantiation.
  - Ran full test suite: 36 passed in 39.55s.
  - Formatted and linted: ruff check (passed), ruff format (48 files clean).
  - Prepared `RELEASE_NOTES_v1.0.0.md` and `docs/engineering/v1_release_audit.md`.
- **Files Changed**:
  - `pyproject.toml`
  - `packages/python-sdk/pyproject.toml`
  - `server/app/config.py`
  - `server/tests/test_health_and_cli.py`
  - `.github/workflows/ci.yml`
  - `RELEASE_NOTES_v1.0.0.md`
  - `docs/engineering/v1_release_audit.md`
  - `docs/engineering/v1_execution_log.md`
