"""Initial schema with pgvector

Revision ID: 001_initial
Revises:
Create Date: 2026-10-25 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 0. Extension for pgvector
    conn = op.get_bind()
    if conn.dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # 1. Tenants
    op.create_table(
        "tenants",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )

    # 2. API Keys
    op.create_table(
        "api_keys",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.CHAR(36),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("key_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("name", sa.String(100), nullable=False, server_default="default"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_api_keys_tenant_id", "api_keys", ["tenant_id"])
    op.create_index("ix_api_keys_key_hash", "api_keys", ["key_hash"])

    # 3. Knowledge Bases
    op.create_table(
        "knowledge_bases",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.CHAR(36),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_knowledge_bases_tenant_id", "knowledge_bases", ["tenant_id"])

    # 4. Documents
    op.create_table(
        "documents",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.CHAR(36),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "knowledge_base_id",
            sa.CHAR(36),
            sa.ForeignKey("knowledge_bases.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("storage_path", sa.String(512), nullable=False),
        sa.Column("mime_type", sa.String(100), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_documents_tenant_id", "documents", ["tenant_id"])
    op.create_index("ix_documents_knowledge_base_id", "documents", ["knowledge_base_id"])

    # 5. Document Chunks
    op.create_table(
        "document_chunks",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.CHAR(36),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "knowledge_base_id",
            sa.CHAR(36),
            sa.ForeignKey("knowledge_bases.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "document_id",
            sa.CHAR(36),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("embedding", Vector(1536), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_document_chunks_tenant_id", "document_chunks", ["tenant_id"])
    op.create_index("ix_document_chunks_kb_id", "document_chunks", ["knowledge_base_id"])
    op.create_index("ix_document_chunks_doc_id", "document_chunks", ["document_id"])
    op.create_index("ix_chunks_tenant_kb", "document_chunks", ["tenant_id", "knowledge_base_id"])

    # 6. Assistants
    op.create_table(
        "assistants",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.CHAR(36),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "knowledge_base_id",
            sa.CHAR(36),
            sa.ForeignKey("knowledge_bases.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("system_instructions", sa.Text(), nullable=True),
        sa.Column("model", sa.String(100), nullable=False, server_default="gpt-4o-mini"),
        sa.Column("temperature", sa.Float(), nullable=False, server_default="0.2"),
        sa.Column("max_tokens", sa.Integer(), nullable=False, server_default="1024"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_assistants_tenant_id", "assistants", ["tenant_id"])

    # 7. Conversations
    op.create_table(
        "conversations",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.CHAR(36),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "assistant_id",
            sa.CHAR(36),
            sa.ForeignKey("assistants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_conversations_tenant_id", "conversations", ["tenant_id"])
    op.create_index("ix_conversations_assistant_id", "conversations", ["assistant_id"])

    # 8. Messages
    op.create_table(
        "messages",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.CHAR(36),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "conversation_id",
            sa.CHAR(36),
            sa.ForeignKey("conversations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", sa.String(50), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("sources", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_messages_tenant_id", "messages", ["tenant_id"])
    op.create_index("ix_messages_conv_id", "messages", ["conversation_id"])

    # 9. Ingestion Jobs
    op.create_table(
        "ingestion_jobs",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column(
            "tenant_id",
            sa.CHAR(36),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "document_id",
            sa.CHAR(36),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_ingestion_jobs_tenant_id", "ingestion_jobs", ["tenant_id"])
    op.create_index("ix_ingestion_jobs_document_id", "ingestion_jobs", ["document_id"])


def downgrade() -> None:
    op.drop_table("ingestion_jobs")
    op.drop_table("messages")
    op.drop_table("conversations")
    op.drop_table("assistants")
    op.drop_table("document_chunks")
    op.drop_table("documents")
    op.drop_table("knowledge_bases")
    op.drop_table("api_keys")
    op.drop_table("tenants")
