import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, LargeBinary, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CodeChunk(Base):
    """Represents a semantically meaningful chunk of code for embedding and RAG retrieval."""

    __tablename__ = "code_chunks"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)

    # Foreign keys and relationships
    repository_id: Mapped[uuid.UUID] = mapped_column(
        index=True,
        nullable=False,
    )
    repository_file_id: Mapped[uuid.UUID] = mapped_column(
        index=True,
        nullable=False,
    )

    # Chunk positioning
    chunk_index: Mapped[int] = mapped_column(nullable=False)
    content: Mapped[str] = mapped_column(Text(), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    # Line and character tracking for precise source mapping
    start_line: Mapped[int] = mapped_column(nullable=False)
    end_line: Mapped[int] = mapped_column(nullable=False)
    start_char: Mapped[int] = mapped_column(nullable=False)
    end_char: Mapped[int] = mapped_column(nullable=False)

    # Size metrics for validation and stats
    token_count: Mapped[int] = mapped_column(nullable=False)
    character_count: Mapped[int] = mapped_column(nullable=False)

    # Chunking metadata
    chunking_strategy: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    chunk_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    # Symbol relationship (for semantic chunking)
    primary_symbol_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    related_symbol_ids: Mapped[list[uuid.UUID] | None] = mapped_column(JSON(), nullable=True)

    # Language and encoding info
    language: Mapped[str] = mapped_column(String(20), nullable=False, index=True)

    # Embedding (can be null until embedding service processes it)
    embedding: Mapped[bytes | None] = mapped_column(LargeBinary(), nullable=True)
    embedding_model: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Overlap tracking for context preservation
    is_overlapped: Mapped[bool] = mapped_column(default=False, nullable=False)
    overlap_source_chunk_ids: Mapped[list[uuid.UUID] | None] = mapped_column(JSON(), nullable=True)

    # Additional metadata (complexity, imports, etc.)
    chunk_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSON(), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), nullable=False)

    def __repr__(self) -> str:
        return f"<CodeChunk {self.id} [{self.start_line}:{self.end_line}] ({self.chunk_type})>"
