from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel


class KnowledgeBase(BaseModel):
    id: UUID
    tenant_id: UUID
    name: str
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class Document(BaseModel):
    id: UUID
    tenant_id: UUID
    knowledge_base_id: UUID
    filename: str
    mime_type: str
    file_size: int
    content_hash: str
    status: str
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class SearchResult(BaseModel):
    chunk_id: UUID
    document_id: UUID
    content: str
    metadata: Optional[Dict[str, Any]] = None
    similarity_score: float
    rank: int


class Assistant(BaseModel):
    id: UUID
    tenant_id: UUID
    knowledge_base_id: Optional[UUID] = None
    name: str
    system_instructions: Optional[str] = None
    model: str
    temperature: float
    max_tokens: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ChatResponse(BaseModel):
    conversation_id: UUID
    message_id: UUID
    role: str
    content: str
    sources: List[Dict[str, Any]] = []
