"""create repositories table

Revision ID: 20260428_0002
Revises: 20260428_0001
Create Date: 2026-04-28 00:30:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260428_0002"
down_revision = "20260428_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "repositories",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("branch", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("local_path", sa.Text(), nullable=False),
        sa.Column("archive_name", sa.String(length=255), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_repositories_project_id", "repositories", ["project_id"], unique=False)
    op.create_index("ix_repositories_source_type", "repositories", ["source_type"], unique=False)
    op.create_index("ix_repositories_status", "repositories", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_repositories_status", table_name="repositories")
    op.drop_index("ix_repositories_source_type", table_name="repositories")
    op.drop_index("ix_repositories_project_id", table_name="repositories")
    op.drop_table("repositories")
