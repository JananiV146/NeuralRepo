import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base


class RepositorySymbol(Base):
    __tablename__ = "repository_symbols"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    repository_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("repositories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    repository_file_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("repository_files.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    symbol_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    qualified_name: Mapped[str] = mapped_column(Text(), nullable=False)
    parent_qualified_name: Mapped[str | None] = mapped_column(Text(), nullable=True)
    line_start: Mapped[int] = mapped_column(Integer(), nullable=False)
    line_end: Mapped[int] = mapped_column(Integer(), nullable=False)
    docstring: Mapped[str | None] = mapped_column(Text(), nullable=True)
    is_public: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    repository = relationship("Repository")
    repository_file = relationship("RepositoryFile")
