import os
import uuid
import hashlib
from typing import List
from uuid import UUID
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    UploadFile,
    File,
    Form,
    BackgroundTasks,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from server.app.database import get_db
from server.app.dependencies import get_current_tenant
from server.app.config import get_settings, Settings
from server.app.models import (
    Tenant,
    KnowledgeBase,
    Document,
    IngestionJob,
    Assistant,
    Conversation,
    Message,
)
from server.app.schemas import (
    KnowledgeBaseCreate,
    KnowledgeBaseResponse,
    DocumentResponse,
    DocumentUploadResponse,
    SearchRequest,
    SearchResponse,
    SearchResultItem,
    AssistantCreate,
    AssistantResponse,
    MessageResponse,
    ChatRequest,
    ChatResponse,
)
from server.app.retrieval import retrieve_relevant_chunks
from server.app.providers import OpenAIEmbeddingProvider, OpenAIChatProvider
from server.app.worker import process_document_job

router = APIRouter(prefix="/v1")


# --- Knowledge Bases ---
@router.post(
    "/knowledge-bases", response_model=KnowledgeBaseResponse, status_code=status.HTTP_201_CREATED
)
async def create_knowledge_base(
    payload: KnowledgeBaseCreate,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    kb = KnowledgeBase(
        tenant_id=tenant.id,
        name=payload.name,
        description=payload.description,
    )
    db.add(kb)
    await db.commit()
    await db.refresh(kb)
    return kb


@router.get("/knowledge-bases", response_model=List[KnowledgeBaseResponse])
async def list_knowledge_bases(
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(KnowledgeBase).where(KnowledgeBase.tenant_id == tenant.id)
    res = await db.execute(stmt)
    return res.scalars().all()


@router.get("/knowledge-bases/{kb_id}", response_model=KnowledgeBaseResponse)
async def get_knowledge_base(
    kb_id: UUID,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(KnowledgeBase).where(
        KnowledgeBase.id == kb_id,
        KnowledgeBase.tenant_id == tenant.id,
    )
    res = await db.execute(stmt)
    kb = res.scalars().first()
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    return kb


@router.delete("/knowledge-bases/{kb_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_knowledge_base(
    kb_id: UUID,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(KnowledgeBase).where(
        KnowledgeBase.id == kb_id,
        KnowledgeBase.tenant_id == tenant.id,
    )
    res = await db.execute(stmt)
    kb = res.scalars().first()
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    await db.delete(kb)
    await db.commit()
    return None


# --- Documents ---
@router.post(
    "/documents/upload", response_model=DocumentUploadResponse, status_code=status.HTTP_202_ACCEPTED
)
async def upload_document(
    background_tasks: BackgroundTasks,
    knowledge_base_id: UUID = Form(...),
    file: UploadFile = File(...),
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    # Verify Knowledge Base ownership
    stmt = select(KnowledgeBase).where(
        KnowledgeBase.id == knowledge_base_id,
        KnowledgeBase.tenant_id == tenant.id,
    )
    res = await db.execute(stmt)
    kb = res.scalars().first()
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")

    # Read and validate file content
    content = await file.read()
    if len(content) > settings.max_upload_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum allowed size of {settings.max_upload_size_bytes} bytes",
        )

    content_hash = hashlib.sha256(content).hexdigest()

    # Generate safe storage path
    storage_dir = settings.storage_dir
    os.makedirs(storage_dir, exist_ok=True)
    file_ext = os.path.splitext(file.filename or "")[1]
    safe_name = f"{uuid.uuid4()}{file_ext}"
    storage_path = os.path.join(storage_dir, safe_name)

    with open(storage_path, "wb") as f:
        f.write(content)

    doc = Document(
        tenant_id=tenant.id,
        knowledge_base_id=kb.id,
        filename=file.filename or "unknown",
        storage_path=storage_path,
        mime_type=file.content_type or "application/octet-stream",
        file_size=len(content),
        content_hash=content_hash,
        status="pending",
    )
    db.add(doc)
    await db.flush()

    job = IngestionJob(
        tenant_id=tenant.id,
        document_id=doc.id,
        status="pending",
    )
    db.add(job)
    await db.commit()
    await db.refresh(doc)
    await db.refresh(job)

    # Trigger background task for immediate ingestion
    provider = OpenAIEmbeddingProvider(settings)
    from server.app.database import AsyncSessionLocal

    # Check if app state has session factory
    session_factory = getattr(db, "_session_factory", AsyncSessionLocal)
    background_tasks.add_task(
        process_document_job, job.id, settings, provider, db_session_factory=session_factory
    )

    return DocumentUploadResponse(
        document=DocumentResponse.model_validate(doc),
        job_id=job.id,
        message="Document uploaded successfully. Processing started.",
    )


@router.get("/documents/{doc_id}", response_model=DocumentResponse)
async def get_document(
    doc_id: UUID,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Document).where(
        Document.id == doc_id,
        Document.tenant_id == tenant.id,
    )
    res = await db.execute(stmt)
    doc = res.scalars().first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.get("/knowledge-bases/{kb_id}/documents", response_model=List[DocumentResponse])
async def list_documents(
    kb_id: UUID,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    # Check KB ownership
    kb_res = await db.execute(
        select(KnowledgeBase).where(
            KnowledgeBase.id == kb_id,
            KnowledgeBase.tenant_id == tenant.id,
        )
    )
    if not kb_res.scalars().first():
        raise HTTPException(status_code=404, detail="Knowledge base not found")

    stmt = select(Document).where(
        Document.knowledge_base_id == kb_id,
        Document.tenant_id == tenant.id,
    )
    res = await db.execute(stmt)
    return res.scalars().all()


@router.delete("/documents/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    doc_id: UUID,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Document).where(
        Document.id == doc_id,
        Document.tenant_id == tenant.id,
    )
    res = await db.execute(stmt)
    doc = res.scalars().first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Clean up physical file if exists
    if os.path.exists(doc.storage_path):
        try:
            os.remove(doc.storage_path)
        except Exception:
            pass

    await db.delete(doc)
    await db.commit()
    return None


# --- Search ---
@router.post("/search", response_model=SearchResponse)
async def search_knowledge(
    payload: SearchRequest,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    # Verify Knowledge Base belongs to tenant
    kb_res = await db.execute(
        select(KnowledgeBase).where(
            KnowledgeBase.id == payload.knowledge_base_id,
            KnowledgeBase.tenant_id == tenant.id,
        )
    )
    if not kb_res.scalars().first():
        raise HTTPException(status_code=404, detail="Knowledge base not found")

    provider = OpenAIEmbeddingProvider(settings)
    results = await retrieve_relevant_chunks(
        db=db,
        tenant_id=tenant.id,
        knowledge_base_id=payload.knowledge_base_id,
        query=payload.query,
        embedding_provider=provider,
        top_k=payload.top_k,
    )

    items = [SearchResultItem(**r) for r in results]
    return SearchResponse(results=items, total=len(items))


# --- Assistants ---
@router.post("/assistants", response_model=AssistantResponse, status_code=status.HTTP_201_CREATED)
async def create_assistant(
    payload: AssistantCreate,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    if payload.knowledge_base_id:
        kb_res = await db.execute(
            select(KnowledgeBase).where(
                KnowledgeBase.id == payload.knowledge_base_id,
                KnowledgeBase.tenant_id == tenant.id,
            )
        )
        if not kb_res.scalars().first():
            raise HTTPException(status_code=404, detail="Knowledge base not found")

    assistant = Assistant(
        tenant_id=tenant.id,
        name=payload.name,
        knowledge_base_id=payload.knowledge_base_id,
        system_instructions=payload.system_instructions,
        model=payload.model,
        temperature=payload.temperature,
        max_tokens=payload.max_tokens,
    )
    db.add(assistant)
    await db.commit()
    await db.refresh(assistant)
    return assistant


@router.get("/assistants", response_model=List[AssistantResponse])
async def list_assistants(
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Assistant).where(Assistant.tenant_id == tenant.id)
    res = await db.execute(stmt)
    return res.scalars().all()


@router.get("/assistants/{assistant_id}", response_model=AssistantResponse)
async def get_assistant(
    assistant_id: UUID,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Assistant).where(
        Assistant.id == assistant_id,
        Assistant.tenant_id == tenant.id,
    )
    res = await db.execute(stmt)
    ast = res.scalars().first()
    if not ast:
        raise HTTPException(status_code=404, detail="Assistant not found")
    return ast


@router.delete("/assistants/{assistant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_assistant(
    assistant_id: UUID,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Assistant).where(
        Assistant.id == assistant_id,
        Assistant.tenant_id == tenant.id,
    )
    res = await db.execute(stmt)
    ast = res.scalars().first()
    if not ast:
        raise HTTPException(status_code=404, detail="Assistant not found")
    await db.delete(ast)
    await db.commit()
    return None


# --- Conversations & Chat ---
@router.post("/assistants/{assistant_id}/chat", response_model=ChatResponse)
async def chat_with_assistant(
    assistant_id: UUID,
    payload: ChatRequest,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    # 1. Fetch and verify Assistant
    stmt = select(Assistant).where(
        Assistant.id == assistant_id,
        Assistant.tenant_id == tenant.id,
    )
    res = await db.execute(stmt)
    assistant = res.scalars().first()
    if not assistant:
        raise HTTPException(status_code=404, detail="Assistant not found")

    # 2. Get or create Conversation
    conversation_id = payload.conversation_id
    if conversation_id:
        conv_res = await db.execute(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.tenant_id == tenant.id,
                Conversation.assistant_id == assistant.id,
            )
        )
        conversation = conv_res.scalars().first()
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
    else:
        conversation = Conversation(
            tenant_id=tenant.id,
            assistant_id=assistant.id,
            title=payload.message[:40],
        )
        db.add(conversation)
        await db.flush()
        conversation_id = conversation.id

    # 3. Retrieve grounding sources from KB if attached
    sources = []
    context_str = ""
    if assistant.knowledge_base_id:
        embed_provider = OpenAIEmbeddingProvider(settings)
        sources = await retrieve_relevant_chunks(
            db=db,
            tenant_id=tenant.id,
            knowledge_base_id=assistant.knowledge_base_id,
            query=payload.message,
            embedding_provider=embed_provider,
            top_k=4,
        )
        if sources:
            context_blocks = [f"[Source chunk {s['chunk_id']}]:\n{s['content']}" for s in sources]
            context_str = "\n\n".join(context_blocks)

    # 4. Construct prompt messages
    sys_instruction = (
        assistant.system_instructions or "You are a helpful and knowledgeable AI assistant."
    )
    messages_payload = [{"role": "system", "content": sys_instruction}]

    if context_str:
        user_prompt = (
            f"Context information is below.\n"
            f"---------------------\n"
            f"{context_str}\n"
            f"---------------------\n"
            f"Given the context above, answer the following question. If the context does not contain enough information to answer, state that clearly.\n\n"
            f"Question: {payload.message}"
        )
    else:
        user_prompt = payload.message

    # Fetch past conversation messages (bounded history: last 6)
    past_msgs_res = await db.execute(
        select(Message)
        .where(
            Message.conversation_id == conversation_id,
            Message.tenant_id == tenant.id,
        )
        .order_by(Message.created_at.desc())
        .limit(6)
    )
    past_msgs = list(reversed(past_msgs_res.scalars().all()))
    for m in past_msgs:
        messages_payload.append({"role": m.role, "content": m.content})

    messages_payload.append({"role": "user", "content": user_prompt})

    # 5. Generate Response via LLM
    chat_provider = OpenAIChatProvider(settings)
    answer = await chat_provider.generate_response(
        messages=messages_payload,
        temperature=assistant.temperature,
        max_tokens=assistant.max_tokens,
    )

    # 6. Persist Messages
    user_msg = Message(
        tenant_id=tenant.id,
        conversation_id=conversation_id,
        role="user",
        content=payload.message,
    )
    db.add(user_msg)

    # Format source references for response
    formatted_sources = [
        {
            "chunk_id": str(s["chunk_id"]),
            "document_id": str(s["document_id"]),
            "similarity_score": s["similarity_score"],
            "metadata": s.get("metadata", {}),
        }
        for s in sources
    ]

    assistant_msg = Message(
        tenant_id=tenant.id,
        conversation_id=conversation_id,
        role="assistant",
        content=answer,
        sources=formatted_sources,
    )
    db.add(assistant_msg)
    await db.commit()
    await db.refresh(assistant_msg)

    return ChatResponse(
        conversation_id=conversation_id,
        message_id=assistant_msg.id,
        role="assistant",
        content=answer,
        sources=formatted_sources,
    )


@router.get("/conversations/{conversation_id}/messages", response_model=List[MessageResponse])
async def get_conversation_messages(
    conversation_id: UUID,
    tenant: Tenant = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    # Verify ownership
    conv_res = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.tenant_id == tenant.id,
        )
    )
    if not conv_res.scalars().first():
        raise HTTPException(status_code=404, detail="Conversation not found")

    stmt = (
        select(Message)
        .where(
            Message.conversation_id == conversation_id,
            Message.tenant_id == tenant.id,
        )
        .order_by(Message.created_at.asc())
    )
    res = await db.execute(stmt)
    return res.scalars().all()
