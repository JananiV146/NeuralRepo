import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base


class RepositoryImport(Base):
    __tablename__ = "repository_imports"

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
    import_type: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    module_name: Mapped[str | None] = mapped_column(Text(), nullable=True)
    imported_name: Mapped[str | None] = mapped_column(Text(), nullable=True)
    alias: Mapped[str | None] = mapped_column(Text(), nullable=True)
    line_number: Mapped[int] = mapped_column(Integer(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    repository = relationship("Repository")
    repository_file = relationship("RepositoryFile")
