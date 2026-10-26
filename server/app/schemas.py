from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


# --- Health ---
class HealthResponse(BaseModel):
    status: str
    database: str
    version: str = "0.1.0"


# --- Tenant ---
class TenantCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)


class TenantResponse(BaseModel):
    id: UUID
    name: str
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- API Key ---
class APIKeyCreate(BaseModel):
    name: str = Field(default="default", max_length=100)


class APIKeyCreatedResponse(BaseModel):
    id: UUID
    name: str
    raw_key: str
    tenant_id: UUID
    created_at: datetime


class APIKeyResponse(BaseModel):
    id: UUID
    name: str
    tenant_id: UUID
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Knowledge Base ---
class KnowledgeBaseCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None


class KnowledgeBaseResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    name: str
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# --- Document ---
class DocumentResponse(BaseModel):
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

    model_config = ConfigDict(from_attributes=True)


class DocumentUploadResponse(BaseModel):
    document: DocumentResponse
    job_id: Optional[UUID] = None
    message: str


# --- Search & Retrieval ---
class SearchRequest(BaseModel):
    knowledge_base_id: UUID
    query: str = Field(..., min_length=1)
    top_k: int = Field(default=4, ge=1, le=50)
    score_threshold: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Optional minimum cosine similarity score threshold (0.0 to 1.0).",
    )


class SearchResultItem(BaseModel):
    chunk_id: UUID
    document_id: UUID
    content: str
    metadata: Optional[Dict[str, Any]] = None
    similarity_score: float
    rank: int


class SearchResponse(BaseModel):
    results: List[SearchResultItem]
    total: int


# --- Assistant ---
class AssistantCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    knowledge_base_id: Optional[UUID] = None
    system_instructions: Optional[str] = None
    model: str = "gpt-4o-mini"
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    max_tokens: int = Field(default=1024, ge=1, le=4096)


class AssistantResponse(BaseModel):
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

    model_config = ConfigDict(from_attributes=True)


# --- Conversation & Chat ---
class ConversationCreate(BaseModel):
    assistant_id: UUID
    title: Optional[str] = None


class ConversationResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    assistant_id: UUID
    title: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MessageResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    conversation_id: UUID
    role: str
    content: str
    sources: Optional[List[Dict[str, Any]]] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    conversation_id: Optional[UUID] = None
    stream: bool = False


class ChatResponse(BaseModel):
    conversation_id: UUID
    message_id: UUID
    role: str
    content: str
    sources: List[Dict[str, Any]] = []


# --- Error Schemas ---
class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None


class ErrorResponse(BaseModel):
    error: ErrorDetail
