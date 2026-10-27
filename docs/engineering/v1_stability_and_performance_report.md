# Weirwise Core v1.0.0 Stability & Performance Engineering Report

## 1. Executive Summary & Release Candidate Decision
- **Release Decision**: **PASS**
- **Target Commit**: `61f0482` (+ hardening commits)
- **Official GitHub Release**: `https://github.com/ansarialireza/weirwise-core/releases/tag/v1.0.0`
- **Verification Environment**:
  - Operating System: Windows 10 (Build 26200) & Ubuntu 24.04 (WSL2)
  - Processor: Intel(R) Core(TM) i7-8565U CPU @ 1.80GHz (4 cores / 8 threads)
  - Python Environment: Python 3.11.0 (CPython 64-bit)
  - Relational & Vector DB: PostgreSQL 16.15 (Debian 16.15-1.pgdg12+2) with `pgvector 0.8.7`
  - Embedding Dimensions: 1536 (`text-embedding-3-small`)

---

## 2. Test Inventory & Execution Results

| Test Category | Suite File | Total Tests | Result | Notes |
|---|---|---|---|---|
| **Adversarial & Boundary Validation** | `server/tests/test_adversarial_validation.py` | 4 | **PASSED** | Persian/RTL Unicode, chunk exact bounds, deterministic ties, null/threshold ranges |
| **Atomic Chunk Replacement** | `server/tests/test_atomic_chunk_replacement.py` | 3 | **PASSED** | Re-ingestion chunk cleanout, worker lease fencing |
| **Benchmark Metric Monotonicity** | `server/tests/test_benchmark_metrics.py` | 1 | **PASSED** | Monotonic non-decreasing Recall@k nesting ($\text{Hits@5} \le \text{Hits@10}$) |
| **Concurrent Uploads & Dedup** | `server/tests/test_concurrent_uploads.py` | 2 | **PASSED** | Race condition deduplication via row-level locking (`with_for_update`) |
| **Settings & Bounds Validation** | `server/tests/test_config_validation.py` | 5 | **PASSED** | Overlap < Chunk size constraints, token bounds, ports |
| **End-to-End Workflow** | `server/tests/test_e2e.py` | 1 | **PASSED** | Full ingestion-search-assistant pipeline |
| **Failure Injection & Recovery** | `server/tests/test_failure_injection.py` | 3 | **PASSED** | 503 Provider error status, readiness degradation, 422 payload boundary |
| **Health Probes & CLI Diagnostics** | `server/tests/test_health_and_cli.py` | 4 | **PASSED** | Liveness probe, readiness probe, `check-db` CLI command |
| **Large Document Memory Bounds** | `server/tests/test_large_document_memory.py` | 1 | **PASSED** | Bounded streaming parser memory usage |
| **API Pagination** | `server/tests/test_pagination.py` | 1 | **PASSED** | Limit/offset determinism |
| **PostgreSQL & pgvector Integration** | `server/tests/test_postgres_integration.py` | 1 | **PASSED** | Live PostgreSQL native cosine distance & tenant isolation |
| **Score Threshold Filtering** | `server/tests/test_score_threshold.py` | 3 | **PASSED** | Validates 1536-dim vector filtering in SQL and fallback |
| **Security & Multi-Tenant Isolation** | `server/tests/test_security.py` | 1 | **PASSED** | Strict tenant boundary enforcement (404 on cross-tenant access) |
| **Unit Text Processing** | `server/tests/test_unit.py` | 4 | **PASSED** | Chunking edge cases |
| **Python SDK Client & Context Mgr** | `packages/python-sdk/tests/test_sdk.py` | 3 | **PASSED** | Client initialization, error translation, context manager cleanup |
| **SDK Directory Ingestion** | `packages/python-sdk/tests/test_sdk_upload_dir.py` | 3 | **PASSED** | Deterministic alphabetical order, recursive & non-recursive, empty directory |
| **SDK Ingestion Polling Waiter** | `packages/python-sdk/tests/test_sdk_wait.py` | 3 | **PASSED** | Completed, failed, and timeout polling semantics |
| **TOTAL TEST CASES** | **All 17 Test Modules** | **43** | **100% PASSED** | **Execution time: 44.91s** |

---

## 3. Discovered Defects & Verified Fixes

1. **Defect in Paragraph Chunking at Exact Boundary**:
   - **Root Cause**: `chunk_text` calculated `current_length + para_len + 2` even when `current_chunk` was empty, causing single paragraphs exactly equal to `chunk_size` to split into 2 chunks with trailing overlap.
   - **Fix**: Adjusted `added_len` so that the initial paragraph does not add a `+ 2` separator offset.
   - **Regression Coverage**: `test_adversarial_boundary_text_chunking` in `server/tests/test_adversarial_validation.py`.

2. **Defect in Tie-Breaking Non-Determinism on Equal Cosine Distance**:
   - **Root Cause**: When multiple vectors shared identical cosine similarity (e.g. 1.0), PostgreSQL and in-memory ranking relied on undefined order, causing unpredictable top-k pagination.
   - **Fix**: Added explicit secondary sort columns in both PostgreSQL SQL (`ORDER BY distance_col.asc(), chunk_index.asc(), id.asc()`) and in-memory fallback (`key=lambda x: (-x[1], x[0].chunk_index, str(x[0].id))`).
   - **Regression Coverage**: `test_deterministic_tie_breaking_in_vector_retrieval`.

---

## 4. Benchmark Measurements Summary

1. **HNSW vs Exact Search (`benchmarks/retrieval_benchmark.py`)**:
   - Exact Search (Sequential Scan): p50 = 11.41 ms | p95 = 14.93 ms | p99 = 18.39 ms
   - HNSW Index Search: p50 = **3.05 ms** (3.74x speedup) | p95 = **5.33 ms** | p99 = **6.04 ms**
   - Recall@10: 0.575 (with `ef_search = 40`)
2. **Concurrent Load (`benchmarks/load_benchmark.py`)**:
   - Concurrency 1: 15.55 req/s (p50: 50.65 ms)
   - Concurrency 5: 34.35 req/s (peak throughput)
   - Concurrency 10: 29.99 req/s (p50: 268.12 ms)
   - Concurrency 20: 26.01 req/s (p50: 818.77 ms)
   - Error Rate: 0.0% (0 / 400 failures)
3. **Sustained Soak Test (`benchmarks/soak_test.py`)**:
   - 100 operations at concurrency 10: 100% success (29.71 req/s sustained, 0 connection leaks)

---

## 5. Security & Isolation Verification
- **Tenant Isolation**: Every database query filters by `tenant_id`. Foreign resource lookups consistently return `404 Not Found` rather than leaking resource existence or metadata.
- **Path Traversal Protection**: Uploaded files generate isolated random UUID filenames (`storage_path = os.path.join(storage_dir, f"{uuid.uuid4()}{ext}")`), preventing arbitrary filesystem traversal.
- **SQL Injection Prevention**: All queries use parameterized SQLAlchemy ORM statements.
- **API Secret Storage**: Tenant API keys are hashed with SHA-256; raw keys are never stored in plaintext.
