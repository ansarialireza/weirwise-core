# Weirwise Core API Contract (v0.1.0)

## Overview
Weirwise Core provides a modular, lightweight HTTP REST API for multi-tenant document ingestion, vector retrieval, and RAG assistant execution.

## Base URL
`/api/v1`

## Authentication
Every tenant-scoped request must include the `X-API-Key` HTTP header:
```http
X-API-Key: ww_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```
API keys are hashed (SHA-256) on creation. The raw key is never stored in plaintext and is only visible once upon generation.

---

## Endpoints

### 1. Health Checks
- `GET /health/live`: Unauthenticated liveness probe.
- `GET /health/ready`: Database connectivity readiness check.

### 2. Knowledge Bases
- `POST /api/v1/knowledge-bases`: Create a knowledge base scoped to authenticated tenant.
  - Body: `{"name": str, "description": Optional[str]}`
- `GET /api/v1/knowledge-bases`: List all knowledge bases for tenant.
- `GET /api/v1/knowledge-bases/{kb_id}`: Retrieve a knowledge base by ID.
- `DELETE /api/v1/knowledge-bases/{kb_id}`: Delete knowledge base and cascade delete documents and chunks.

### 3. Documents
- `POST /api/v1/documents/upload`: Upload file (`multipart/form-data`) with `knowledge_base_id` and `file`.
  - Enqueues asynchronous ingestion job and returns HTTP 202.
- `GET /api/v1/documents/{doc_id}`: Retrieve document status and metadata.
- `GET /api/v1/knowledge-bases/{kb_id}/documents`: List documents in knowledge base.
- `DELETE /api/v1/documents/{doc_id}`: Delete document and its chunk vectors.

### 4. Vector Search & Retrieval
- `POST /api/v1/search`:
  - Request: `{"knowledge_base_id": UUID, "query": str, "top_k": int}`
  - Response:
    ```json
    {
      "results": [
        {
          "chunk_id": "...",
          "document_id": "...",
          "content": "...",
          "metadata": {},
          "similarity_score": 0.89,
          "rank": 1
        }
      ],
      "total": 1
    }
    ```

### 5. Assistants & Chat
- `POST /api/v1/assistants`: Create an assistant.
  - Body: `{"name": str, "knowledge_base_id": Optional[UUID], "system_instructions": Optional[str], "model": str, "temperature": float, "max_tokens": int}`
- `GET /api/v1/assistants`: List assistants.
- `GET /api/v1/assistants/{assistant_id}`: Retrieve assistant.
- `DELETE /api/v1/assistants/{assistant_id}`: Delete assistant.
- `POST /api/v1/assistants/{assistant_id}/chat`: Execute grounded RAG conversation.
  - Body: `{"message": str, "conversation_id": Optional[UUID]}`
  - Response:
    ```json
    {
      "conversation_id": "...",
      "message_id": "...",
      "role": "assistant",
      "content": "...",
      "sources": [...]
    }
    ```
- `GET /api/v1/conversations/{conversation_id}/messages`: Fetch ordered conversation history.
