# Changelog

All notable changes to Weirwise Core will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
