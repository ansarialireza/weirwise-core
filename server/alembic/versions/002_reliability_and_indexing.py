"""Reliability, Indexing, and Fencing Tokens

Revision ID: 002_reliability_and_indexing
Revises: 001_initial
Create Date: 2026-10-25 22:30:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "002_reliability_and_indexing"
down_revision = "001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    is_postgres = conn.dialect.name == "postgresql"

    # 1. Pre-check for duplicate documents before adding unique constraint
    # Safety rule: Never silently drop or merge user data. Abort if duplicates exist.
    check_query = sa.text(
        "SELECT knowledge_base_id, content_hash, count(*) as cnt "
        "FROM documents "
        "GROUP BY knowledge_base_id, content_hash "
        "HAVING count(*) > 1;"
    )
    duplicates = conn.execute(check_query).fetchall()
    if duplicates:
        dup_summary = [f"(KB: {row[0]}, Hash: {row[1]}, Count: {row[2]})" for row in duplicates]
        raise RuntimeError(
            f"Migration 002 aborted: Found {len(duplicates)} duplicate document set(s) "
            f"with identical content_hash within the same knowledge base:\n"
            f"{', '.join(dup_summary)}\n"
            f"Please clean up existing duplicates before upgrading. No data was modified."
        )

    # 2. Unique index for duplicate upload protection per Knowledge Base
    op.create_index(
        "uq_documents_kb_content_hash",
        "documents",
        ["knowledge_base_id", "content_hash"],
        unique=True,
    )

    # 3. Worker heartbeat, lease, and monotonically increasing generation / fencing token
    # claim_token is a unique UUID generated on each claim, ensuring earlier workers cannot commit.
    uuid_type = postgresql.UUID(as_uuid=True) if is_postgres else sa.CHAR(36)
    op.add_column("ingestion_jobs", sa.Column("locked_at", sa.DateTime(), nullable=True))
    op.add_column("ingestion_jobs", sa.Column("locked_by", sa.String(100), nullable=True))
    op.add_column("ingestion_jobs", sa.Column("claim_token", uuid_type, nullable=True))
    op.add_column(
        "ingestion_jobs",
        sa.Column("generation", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index(
        "ix_ingestion_jobs_status_locked_at",
        "ingestion_jobs",
        ["status", "locked_at"],
    )

    # 4. HNSW Vector Index on document_chunks (embedding)
    if is_postgres:
        op.execute(
            "CREATE INDEX ix_chunks_embedding_hnsw ON document_chunks "
            "USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);"
        )


def downgrade() -> None:
    conn = op.get_bind()
    is_postgres = conn.dialect.name == "postgresql"

    if is_postgres:
        op.execute("DROP INDEX IF EXISTS ix_chunks_embedding_hnsw;")
    op.drop_index("ix_ingestion_jobs_status_locked_at", table_name="ingestion_jobs")
    op.drop_column("ingestion_jobs", "generation")
    op.drop_column("ingestion_jobs", "claim_token")
    op.drop_column("ingestion_jobs", "locked_by")
    op.drop_column("ingestion_jobs", "locked_at")
    op.drop_index("uq_documents_kb_content_hash", table_name="documents")
