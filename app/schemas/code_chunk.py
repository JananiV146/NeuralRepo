from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CodeChunkRead(BaseModel):
    """Schema for reading a code chunk from the database."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    repository_id: UUID
    repository_file_id: UUID
    chunk_index: int
    content: str
    content_hash: str
    start_line: int
    end_line: int
    start_char: int
    end_char: int
    token_count: int
    character_count: int
    chunking_strategy: str
    chunk_type: str
    primary_symbol_id: UUID | None
    related_symbol_ids: list[UUID] | None
    language: str
    embedding_model: str | None
    is_overlapped: bool
    overlap_source_chunk_ids: list[UUID] | None
    metadata: dict | None
    created_at: datetime
    updated_at: datetime


class CodeChunkCreateRequest(BaseModel):
    """Internal schema for creating code chunks (used by service)."""

    repository_id: UUID
    repository_file_id: UUID
    chunk_index: int
    content: str
    content_hash: str
    start_line: int
    end_line: int
    start_char: int
    end_char: int
    token_count: int
    character_count: int
    chunking_strategy: str
    chunk_type: str
    primary_symbol_id: UUID | None = None
    related_symbol_ids: list[UUID] | None = None
    language: str = "python"
    is_overlapped: bool = False
    overlap_source_chunk_ids: list[UUID] | None = None
    metadata: dict | None = None


class RepositoryChunkingResponse(BaseModel):
    """Response for repository chunking operation."""

    repository_id: UUID
    status: str
    total_chunks_created: int
    files_processed: int
    failed_files: int
    strategy_used: str
    chunking_errors: dict[str, str]


class ChunkingStatisticsResponse(BaseModel):
    """Statistics about code chunks in a repository."""

    repository_id: UUID
    total_chunks: int
    embedded_chunks: int
    by_strategy: dict[str, int]
    by_type: dict[str, int]
    embedding_coverage: float


class ChunkingConfigRequest(BaseModel):
    """Configuration for chunking operation."""

    strategy: str = "semantic"  # semantic, fixed_size, sliding_window
    max_tokens: int = 512
    max_characters: int = 2000
    overlap_tokens: int = 50
    chunk_by_symbols: bool = True
    include_docstrings: bool = True
    preserve_context: bool = True
