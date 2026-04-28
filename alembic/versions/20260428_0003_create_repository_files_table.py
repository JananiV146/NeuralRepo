"""create repository files table

Revision ID: 20260428_0003
Revises: 20260428_0002
Create Date: 2026-04-28 11:00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260428_0003"
down_revision = "20260428_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "repository_files",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("repository_id", sa.Uuid(), nullable=False),
        sa.Column("relative_path", sa.Text(), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("extension", sa.String(length=32), nullable=True),
        sa.Column("language", sa.String(length=64), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("content_type", sa.String(length=32), nullable=False, server_default="text"),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["repository_id"], ["repositories.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("repository_id", "relative_path", name="uq_repository_files_repository_path"),
    )
    op.create_index("ix_repository_files_repository_id", "repository_files", ["repository_id"], unique=False)
    op.create_index("ix_repository_files_extension", "repository_files", ["extension"], unique=False)
    op.create_index("ix_repository_files_language", "repository_files", ["language"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_repository_files_language", table_name="repository_files")
    op.drop_index("ix_repository_files_extension", table_name="repository_files")
    op.drop_index("ix_repository_files_repository_id", table_name="repository_files")
    op.drop_table("repository_files")
