"""create repository ast tables

Revision ID: 20260428_0004
Revises: 20260428_0003
Create Date: 2026-04-28 11:40:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260428_0004"
down_revision = "20260428_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "repository_symbols",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("repository_id", sa.Uuid(), nullable=False),
        sa.Column("repository_file_id", sa.Uuid(), nullable=False),
        sa.Column("symbol_type", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("qualified_name", sa.Text(), nullable=False),
        sa.Column("parent_qualified_name", sa.Text(), nullable=True),
        sa.Column("line_start", sa.Integer(), nullable=False),
        sa.Column("line_end", sa.Integer(), nullable=False),
        sa.Column("docstring", sa.Text(), nullable=True),
        sa.Column("is_public", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["repository_file_id"], ["repository_files.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["repository_id"], ["repositories.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_repository_symbols_repository_id", "repository_symbols", ["repository_id"], unique=False)
    op.create_index("ix_repository_symbols_repository_file_id", "repository_symbols", ["repository_file_id"], unique=False)
    op.create_index("ix_repository_symbols_symbol_type", "repository_symbols", ["symbol_type"], unique=False)

    op.create_table(
        "repository_imports",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("repository_id", sa.Uuid(), nullable=False),
        sa.Column("repository_file_id", sa.Uuid(), nullable=False),
        sa.Column("import_type", sa.String(length=16), nullable=False),
        sa.Column("module_name", sa.Text(), nullable=True),
        sa.Column("imported_name", sa.Text(), nullable=True),
        sa.Column("alias", sa.Text(), nullable=True),
        sa.Column("line_number", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["repository_file_id"], ["repository_files.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["repository_id"], ["repositories.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_repository_imports_repository_id", "repository_imports", ["repository_id"], unique=False)
    op.create_index("ix_repository_imports_repository_file_id", "repository_imports", ["repository_file_id"], unique=False)
    op.create_index("ix_repository_imports_import_type", "repository_imports", ["import_type"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_repository_imports_import_type", table_name="repository_imports")
    op.drop_index("ix_repository_imports_repository_file_id", table_name="repository_imports")
    op.drop_index("ix_repository_imports_repository_id", table_name="repository_imports")
    op.drop_table("repository_imports")

    op.drop_index("ix_repository_symbols_symbol_type", table_name="repository_symbols")
    op.drop_index("ix_repository_symbols_repository_file_id", table_name="repository_symbols")
    op.drop_index("ix_repository_symbols_repository_id", table_name="repository_symbols")
    op.drop_table("repository_symbols")
