"""create embeddings and vector metadata tables

Revision ID: 20260428_0007
Revises: 20260428_0006
Create Date: 2026-04-29 12:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260428_0007"
down_revision = "20260428_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Table to track embedding operations and metadata
    op.create_table(
        "embedding_jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("repository_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("embedding_model", sa.String(100), nullable=False),
        sa.Column("total_chunks", sa.Integer(), nullable=False, default=0),
        sa.Column("embedded_chunks", sa.Integer(), nullable=False, default=0),
        sa.Column("failed_chunks", sa.Integer(), nullable=False, default=0),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["repository_id"], ["repositories.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.Index("idx_embedding_jobs_repository_id", "repository_id"),
        sa.Index("idx_embedding_jobs_status", "status"),
        sa.Index("idx_embedding_jobs_model", "embedding_model"),
    )

    # Table to track embedding model versions and configs
    op.create_table(
        "embedding_models",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
        sa.Column("provider", sa.String(50), nullable=False),  # openai, local, huggingface
        sa.Column("model_identifier", sa.String(200), nullable=False),  # e.g., "text-embedding-3-small"
        sa.Column("vector_dimension", sa.Integer(), nullable=False),
        sa.Column("context_length", sa.Integer(), nullable=False),
        sa.Column("max_batch_size", sa.Integer(), nullable=False, default=100),
        sa.Column("cost_per_1k_tokens", sa.Float(), nullable=True),  # For OpenAI models
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("config", sa.JSON(), nullable=True),  # Additional provider-specific config
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.Index("idx_embedding_models_provider", "provider"),
        sa.Index("idx_embedding_models_active", "is_active"),
    )


def downgrade() -> None:
    op.drop_table("embedding_models")
    op.drop_table("embedding_jobs")
