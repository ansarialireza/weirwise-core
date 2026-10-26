# Release Notes — Weirwise Core v0.3.0

**Release Tag:** `v0.3.0`  
**Date:** 2026-10-26  
**License:** MIT  
**Compatibility:** Fully backward-compatible with `v0.2.0` API and database schemas.

Weirwise Core v0.3.0 focuses on **Developer Experience (DX), Diagnostics, Type Safety, and Retrieval Precision**. Our design principle remains: *"Make the correct path the easiest path for developers."*

---

## 1. User-Facing Changes & Developer Experience

- **PEP 561 Type Information for Python SDK:**
  - The `weirwise` Python package now ships with `py.typed` and package data mappings, providing first-class autocomplete, type hints, and static validation in modern IDEs and type checkers (`mypy`, `pyright`).
- **Database & pgvector Doctor Command (`check-db`):**
  - Added CLI diagnostic tool `weirwise check-db` (or `python -m server.app.cli check-db`).
  - Verifies database reachability, queries PostgreSQL server version, and asserts that the `pgvector` extension is installed with its active version.
  - Automatically masks database passwords in output for security.
- **SDK Directory Ingestion Helper (`upload_directory`):**
  - Added `client.documents.upload_directory(...)` to easily index whole directories or folders into a Knowledge Base.
  - Supports recursive traversal, glob file matching patterns (e.g. `*.txt`), deterministic sorting, and optional ingestion polling (`wait=True`).
- **Modernized Documentation & Examples:**
  - Modernized `examples/basic_rag.py` and `README.md` to use deterministic ingestion completion polling (`wait_for_completion`) instead of arbitrary sleeps.

---

## 2. API & SDK Changes

- **Vector Search Score Cutoff (`score_threshold`):**
  - Added optional `score_threshold: Optional[float]` (bounded `0.0` to `1.0`) to `SearchRequest` and `client.search(...)`.
  - Filters out vector chunks below the specified cosine similarity threshold directly in PostgreSQL / pgvector queries or test fallbacks, eliminating noise before result serialization.
- **Fail-Fast Configuration Validation:**
  - `server/app/config.py` enforces strict bounds at startup:
    - `ingestion_mode` restricted to `Literal["inline", "worker"]`.
    - `chunk_size > 0`, `chunk_overlap >= 0`, `db_pool_size > 0`.
    - Cross-validation: `chunk_overlap < chunk_size`.
- **Dynamic Application Versioning:**
  - Application OpenAPI metadata, `/health/live`, and `/health/ready` dynamically report the active version from configuration, ensuring health probes reflect deployed versions accurately.

---

## 3. Bug Fixes & Packaging Hardening

- **Setuptools Discovery in Server Builds:**
  - Configured `[tool.setuptools.packages.find]` in root `pyproject.toml` to cleanly exclude non-distribution directories (`data`, `packages`, `benchmarks`) during flat-layout builds.
- **CI Build Step for SDK Distribution:**
  - Enhanced GitHub Actions workflow to run `python -m build packages/python-sdk` on every push and PR to prevent packaging regressions.

---

## 4. Compatibility Considerations

- **Server REST API:** Fully backward-compatible. `score_threshold` is optional and defaults to `None` (preserving existing top-$k$ search behavior).
- **Python SDK:** Fully backward-compatible. Existing scripts using `client.documents.upload()` and `client.search(...)` require no modifications.
- **Database Schema:** No schema migrations are required between v0.2.0 and v0.3.0.

---

## 5. Known Limitations

- Ingestion of exceptionally large files (>50MB) remains bounded by `max_upload_size_bytes` (50MB default) and memory staging limits established in v0.2.0.
- PostgreSQL 16+ and `pgvector` 0.5.0+ are recommended for production deployments.
