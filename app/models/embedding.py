import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class EmbeddingModel(Base):
    """Configuration for an embedding model provider."""

    __tablename__ = "embedding_models"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)

    # Model identification
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    provider: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    model_identifier: Mapped[str] = mapped_column(String(200), nullable=False)

    # Capabilities
    vector_dimension: Mapped[int] = mapped_column(nullable=False)
    context_length: Mapped[int] = mapped_column(nullable=False)
    max_batch_size: Mapped[int] = mapped_column(default=100)

    # Pricing info (for OpenAI models)
    cost_per_1k_tokens: Mapped[float | None] = mapped_column(nullable=True)

    # Status
    is_active: Mapped[bool] = mapped_column(default=True, index=True)

    # Additional config
    config: Mapped[dict[str, Any] | None] = mapped_column(JSON(), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)

    def __repr__(self) -> str:
        return f"<EmbeddingModel {self.name} ({self.provider}) - {self.vector_dimension}d>"


class EmbeddingJob(Base):
    """Tracks embedding operations for a repository."""

    __tablename__ = "embedding_jobs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)

    # Repository and model
    repository_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    embedding_model: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # Status tracking
    status: Mapped[str] = mapped_column(String(50), nullable=False, index=True, default="pending")
    total_chunks: Mapped[int] = mapped_column(default=0)
    embedded_chunks: Mapped[int] = mapped_column(default=0)
    failed_chunks: Mapped[int] = mapped_column(default=0)

    # Error tracking
    error_message: Mapped[str | None] = mapped_column(nullable=True)

    # Timestamps
    started_at: Mapped[datetime | None] = mapped_column(nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)

    def __repr__(self) -> str:
        return f"<EmbeddingJob {self.id} [{self.status}] - {self.embedded_chunks}/{self.total_chunks}>"

    @property
    def progress_percentage(self) -> float:
        """Calculate completion percentage."""
        if self.total_chunks == 0:
            return 0.0
        return (self.embedded_chunks / self.total_chunks) * 100
