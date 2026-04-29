"""create code chunks table

Revision ID: 20260428_0006
Revises: 20260428_0005
Create Date: 2026-04-28 12:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260428_0006"
down_revision = "20260428_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "code_chunks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("repository_id", sa.Uuid(), nullable=False),
        sa.Column("repository_file_id", sa.Uuid(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("start_line", sa.Integer(), nullable=False),
        sa.Column("end_line", sa.Integer(), nullable=False),
        sa.Column("start_char", sa.Integer(), nullable=False),
        sa.Column("end_char", sa.Integer(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=False),
        sa.Column("character_count", sa.Integer(), nullable=False),
        sa.Column("chunking_strategy", sa.String(50), nullable=False),
        sa.Column("chunk_type", sa.String(50), nullable=False),
        sa.Column("primary_symbol_id", sa.Uuid(), nullable=True),
        sa.Column("related_symbol_ids", sa.JSON(), nullable=True),
        sa.Column("language", sa.String(20), nullable=False),
        sa.Column("embedding", sa.LargeBinary(), nullable=True),
        sa.Column("embedding_model", sa.String(100), nullable=True),
        sa.Column("is_overlapped", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("overlap_source_chunk_ids", sa.JSON(), nullable=True),
        sa.Column("chunk_metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["repository_id"], ["repositories.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["repository_file_id"], ["repository_files.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["primary_symbol_id"], ["repository_symbols.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.Index("idx_code_chunks_repository_id", "repository_id"),
        sa.Index("idx_code_chunks_file_id", "repository_file_id"),
        sa.Index("idx_code_chunks_strategy", "chunking_strategy"),
        sa.Index("idx_code_chunks_type", "chunk_type"),
        sa.Index("idx_code_chunks_language", "language"),
        sa.UniqueConstraint(
            "repository_file_id", "chunk_index", "chunking_strategy", name="uq_file_chunk_strategy"
        ),
    )


def downgrade() -> None:
    op.drop_table("code_chunks")
