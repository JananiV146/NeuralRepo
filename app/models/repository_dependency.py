import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base import Base


class RepositoryDependency(Base):
    __tablename__ = "repository_dependencies"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    repository_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("repositories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_repository_file_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("repository_files.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_repository_file_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("repository_files.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    import_record_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("repository_imports.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_module_name: Mapped[str] = mapped_column(Text(), nullable=False)
    target_module_name: Mapped[str] = mapped_column(Text(), nullable=False)
    import_type: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    is_internal: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=False, index=True)
    is_resolved: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    repository = relationship("Repository")
    source_repository_file = relationship("RepositoryFile", foreign_keys=[source_repository_file_id])
    target_repository_file = relationship("RepositoryFile", foreign_keys=[target_repository_file_id])
    import_record = relationship("RepositoryImport")
