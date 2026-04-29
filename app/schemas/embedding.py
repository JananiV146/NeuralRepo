from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class EmbeddingModelRead(BaseModel):
    """Schema for reading embedding model configuration."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    provider: str
    model_identifier: str
    vector_dimension: int
    context_length: int
    max_batch_size: int
    cost_per_1k_tokens: float | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class EmbeddingJobRead(BaseModel):
    """Schema for reading embedding job status."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    repository_id: UUID
    embedding_model: str
    status: str
    total_chunks: int
    embedded_chunks: int
    failed_chunks: int
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class EmbedRepositoryRequest(BaseModel):
    """Request to embed a repository."""

    model_name: str = "text-embedding-3-small"
    batch_size: int = 100


class EmbeddingStatusResponse(BaseModel):
    """Response with embedding status."""

    repository_id: UUID
    status: str  # no_embeddings, processing, completed, failed
    total_chunks: int | None = None
    embedded_chunks: int | None = None
    failed_chunks: int | None = None
    progress_percentage: float | None = None
    embedding_model: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_message: str | None = None


class SimilarChunk(BaseModel):
    """Schema for similar chunk in search results."""

    chunk_id: UUID
    score: float
    start_line: int | None = None
    end_line: int | None = None
    chunk_type: str | None = None
    language: str | None = None


class ChunkSearchResponse(BaseModel):
    """Response with similar chunks."""

    query: str
    total_results: int
    results: list[SimilarChunk]


class EmbeddingModelsListResponse(BaseModel):
    """Response with list of available embedding models."""

    total_models: int
    models: list[EmbeddingModelRead]
