"""create_document_chunks_and_hnsw_index

Revision ID: c13d8475532d
Revises: 56d6158e44b6
Create Date: 2026-08-27
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
import pgvector
import pgvector.sqlalchemy

revision: str = 'c13d8475532d'
down_revision: Union[str, None] = '56d6158e44b6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create document_chunks table
    op.create_table('document_chunks',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('organization_id', sa.UUID(), nullable=False),
        sa.Column('knowledge_base_id', sa.UUID(), nullable=False),
        sa.Column('document_id', sa.UUID(), nullable=False),
        sa.Column('chunk_index', sa.Integer(), nullable=False),
        sa.Column('ingestion_version', sa.Integer(), nullable=False),
        sa.Column('page_number', sa.Integer(), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('embedding', pgvector.sqlalchemy.vector.VECTOR(dim=768), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['knowledge_base_id'], ['knowledge_bases.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('document_id', 'chunk_index', 'ingestion_version', name='uq_chunks_doc_index_version')
    )
    op.create_index(op.f('ix_document_chunks_document_id'), 'document_chunks', ['document_id'], unique=False)
    op.create_index(op.f('ix_document_chunks_knowledge_base_id'), 'document_chunks', ['knowledge_base_id'], unique=False)
    op.create_index(op.f('ix_document_chunks_organization_id'), 'document_chunks', ['organization_id'], unique=False)

    # 2. Create HNSW Vector Index for Cosine Similarity Search
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_document_chunks_embedding_hnsw "
        "ON document_chunks USING hnsw (embedding vector_cosine_ops) "
        "WITH (m = 16, ef_construction = 64);"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_document_chunks_embedding_hnsw;")
    op.drop_index(op.f('ix_document_chunks_organization_id'), table_name='document_chunks')
    op.drop_index(op.f('ix_document_chunks_knowledge_base_id'), table_name='document_chunks')
    op.drop_index(op.f('ix_document_chunks_document_id'), table_name='document_chunks')
    op.drop_table('document_chunks')
