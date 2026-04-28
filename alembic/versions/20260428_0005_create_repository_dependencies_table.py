"""create repository dependencies table

Revision ID: 20260428_0005
Revises: 20260428_0004
Create Date: 2026-04-28 12:10:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260428_0005"
down_revision = "20260428_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "repository_dependencies",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("repository_id", sa.Uuid(), nullable=False),
        sa.Column("source_repository_file_id", sa.Uuid(), nullable=False),
        sa.Column("target_repository_file_id", sa.Uuid(), nullable=True),
        sa.Column("import_record_id", sa.Uuid(), nullable=False),
        sa.Column("source_module_name", sa.Text(), nullable=False),
        sa.Column("target_module_name", sa.Text(), nullable=False),
        sa.Column("import_type", sa.String(length=16), nullable=False),
        sa.Column("is_internal", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_resolved", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["import_record_id"], ["repository_imports.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["repository_id"], ["repositories.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_repository_file_id"], ["repository_files.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_repository_file_id"], ["repository_files.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_repository_dependencies_repository_id", "repository_dependencies", ["repository_id"], unique=False)
    op.create_index("ix_repository_dependencies_source_repository_file_id", "repository_dependencies", ["source_repository_file_id"], unique=False)
    op.create_index("ix_repository_dependencies_target_repository_file_id", "repository_dependencies", ["target_repository_file_id"], unique=False)
    op.create_index("ix_repository_dependencies_import_record_id", "repository_dependencies", ["import_record_id"], unique=False)
    op.create_index("ix_repository_dependencies_import_type", "repository_dependencies", ["import_type"], unique=False)
    op.create_index("ix_repository_dependencies_is_internal", "repository_dependencies", ["is_internal"], unique=False)
    op.create_index("ix_repository_dependencies_is_resolved", "repository_dependencies", ["is_resolved"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_repository_dependencies_is_resolved", table_name="repository_dependencies")
    op.drop_index("ix_repository_dependencies_is_internal", table_name="repository_dependencies")
    op.drop_index("ix_repository_dependencies_import_type", table_name="repository_dependencies")
    op.drop_index("ix_repository_dependencies_import_record_id", table_name="repository_dependencies")
    op.drop_index("ix_repository_dependencies_target_repository_file_id", table_name="repository_dependencies")
    op.drop_index("ix_repository_dependencies_source_repository_file_id", table_name="repository_dependencies")
    op.drop_index("ix_repository_dependencies_repository_id", table_name="repository_dependencies")
    op.drop_table("repository_dependencies")
