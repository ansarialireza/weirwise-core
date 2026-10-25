import os
import time
from typing import List, Optional, Union
from uuid import UUID
import httpx
from weirwise.models import KnowledgeBase, Document, SearchResult, Assistant, ChatResponse
from weirwise.exceptions import (
    AuthenticationError,
    NotFoundError,
    APIError,
    IngestionTimeoutError,
    IngestionFailedError,
)


class KnowledgeBasesResource:
    def __init__(self, client: "Weirwise"):
        self.client = client

    def create(self, name: str, description: Optional[str] = None) -> KnowledgeBase:
        payload = {"name": name, "description": description}
        res = self.client._post("/api/v1/knowledge-bases", json=payload)
        return KnowledgeBase(**res)

    def list(self, limit: int = 50, offset: int = 0) -> List[KnowledgeBase]:
        res = self.client._get("/api/v1/knowledge-bases", params={"limit": limit, "offset": offset})
        return [KnowledgeBase(**item) for item in res]

    def get(self, kb_id: Union[str, UUID]) -> KnowledgeBase:
        res = self.client._get(f"/api/v1/knowledge-bases/{kb_id}")
        return KnowledgeBase(**res)

    def delete(self, kb_id: Union[str, UUID]) -> None:
        self.client._delete(f"/api/v1/knowledge-bases/{kb_id}")


class DocumentsResource:
    def __init__(self, client: "Weirwise"):
        self.client = client

    def upload(self, knowledge_base_id: Union[str, UUID], path: str) -> Document:
        if not os.path.exists(path):
            raise FileNotFoundError(f"File not found: {path}")

        filename = os.path.basename(path)
        with open(path, "rb") as f:
            files = {"file": (filename, f, "application/octet-stream")}
            data = {"knowledge_base_id": str(knowledge_base_id)}
            res = self.client._post("/api/v1/documents/upload", data=data, files=files)
            return Document(**res["document"])

    def get(self, doc_id: Union[str, UUID]) -> Document:
        res = self.client._get(f"/api/v1/documents/{doc_id}")
        return Document(**res)

    def list(
        self, knowledge_base_id: Union[str, UUID], limit: int = 50, offset: int = 0
    ) -> List[Document]:
        res = self.client._get(
            f"/api/v1/knowledge-bases/{knowledge_base_id}/documents",
            params={"limit": limit, "offset": offset},
        )
        return [Document(**item) for item in res]

    def wait_for_completion(
        self,
        doc_id: Union[str, UUID],
        timeout: float = 60.0,
        poll_interval: float = 1.0,
    ) -> Document:
        """Polls document until ingestion is 'completed' or 'failed', with timeout."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            doc = self.get(doc_id)
            if doc.status == "completed":
                return doc
            elif doc.status == "failed":
                raise IngestionFailedError(
                    document_id=doc_id, message=doc.error_message or "Unknown failure"
                )
            time.sleep(poll_interval)

        raise IngestionTimeoutError(document_id=doc_id, timeout=timeout)

    def delete(self, doc_id: Union[str, UUID]) -> None:
        self.client._delete(f"/api/v1/documents/{doc_id}")


class AssistantsResource:
    def __init__(self, client: "Weirwise"):
        self.client = client

    def create(
        self,
        name: str,
        knowledge_base_id: Optional[Union[str, UUID]] = None,
        system_instructions: Optional[str] = None,
        model: str = "gpt-4o-mini",
        temperature: float = 0.2,
    ) -> Assistant:
        payload = {
            "name": name,
            "knowledge_base_id": str(knowledge_base_id) if knowledge_base_id else None,
            "system_instructions": system_instructions,
            "model": model,
            "temperature": temperature,
        }
        res = self.client._post("/api/v1/assistants", json=payload)
        return Assistant(**res)

    def list(self, limit: int = 50, offset: int = 0) -> List[Assistant]:
        params = {"limit": limit, "offset": offset}
        res = self.client._get("/api/v1/assistants", params=params)
        return [Assistant(**item) for item in res]

    def get(self, assistant_id: Union[str, UUID]) -> Assistant:
        res = self.client._get(f"/api/v1/assistants/{assistant_id}")
        return Assistant(**res)

    def delete(self, assistant_id: Union[str, UUID]) -> None:
        self.client._delete(f"/api/v1/assistants/{assistant_id}")


class Weirwise:
    """Client for Weirwise Core RAG API."""

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        api_key: Optional[str] = None,
        timeout: float = 30.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.client = httpx.Client(
            base_url=self.base_url,
            headers={"X-API-Key": self.api_key} if self.api_key else {},
            timeout=self.timeout,
        )

        self.knowledge_bases = KnowledgeBasesResource(self)
        self.documents = DocumentsResource(self)
        self.assistants = AssistantsResource(self)

    def _handle_response(self, response: httpx.Response):
        if response.status_code in (401, 403):
            raise AuthenticationError(response.text)
        elif response.status_code == 404:
            raise NotFoundError(response.text)
        elif response.status_code >= 400:
            raise APIError(response.status_code, response.text)

        if response.status_code == 204:
            return None
        return response.json()

    def _get(self, path: str, params: Optional[dict] = None):
        resp = self.client.get(path, params=params)
        return self._handle_response(resp)

    def _post(
        self,
        path: str,
        json: Optional[dict] = None,
        data: Optional[dict] = None,
        files: Optional[dict] = None,
    ):
        resp = self.client.post(path, json=json, data=data, files=files)
        return self._handle_response(resp)

    def _delete(self, path: str):
        resp = self.client.delete(path)
        return self._handle_response(resp)

    def search(
        self,
        knowledge_base_id: Union[str, UUID],
        query: str,
        top_k: int = 4,
    ) -> List[SearchResult]:
        payload = {
            "knowledge_base_id": str(knowledge_base_id),
            "query": query,
            "top_k": top_k,
        }
        res = self._post("/api/v1/search", json=payload)
        return [SearchResult(**item) for item in res["results"]]

    def chat(
        self,
        assistant_id: Union[str, UUID],
        message: str,
        conversation_id: Optional[Union[str, UUID]] = None,
    ) -> ChatResponse:
        payload = {
            "message": message,
            "conversation_id": str(conversation_id) if conversation_id else None,
        }
        res = self._post(f"/api/v1/assistants/{assistant_id}/chat", json=payload)
        return ChatResponse(**res)

    def close(self):
        self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
