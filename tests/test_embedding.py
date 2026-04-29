"""Tests for embedding functionality - Unit tests only.

Integration tests requiring Qdrant and aiosqlite are deferred until
full infrastructure is available. Run unit tests with: pytest tests/
"""

import os
import pytest
from uuid import uuid4


class TestEmbeddingProviders:
    """Test embedding provider configuration and factory."""

    def test_local_provider_creation(self) -> None:
        """Test local embedding provider initialization."""
        from app.services.embedding_provider_service import LocalEmbeddingProvider

        provider = LocalEmbeddingProvider(model_name="all-MiniLM-L6-v2")
        assert provider.model_name == "all-MiniLM-L6-v2"
        assert provider.dimension == 384
        assert provider.max_batch_size == 128

    def test_embedding_provider_factory(self) -> None:
        """Test factory creates correct provider type."""
        from app.services.embedding_provider_service import (
            EmbeddingProviderFactory,
            LocalEmbeddingProvider,
        )

        provider = EmbeddingProviderFactory.create("local")
        assert isinstance(provider, LocalEmbeddingProvider)

    def test_factory_raises_on_invalid_provider(self) -> None:
        """Test factory validation."""
        from app.services.embedding_provider_service import EmbeddingProviderFactory

        with pytest.raises(ValueError):
            EmbeddingProviderFactory.create("nonexistent")

    def test_openai_provider_with_api_key(self) -> None:
        """Test OpenAI provider when API key is available."""
        if not os.getenv("OPENAI_API_KEY"):
            pytest.skip("OPENAI_API_KEY not set")

        from app.services.embedding_provider_service import OpenAIEmbeddingProvider

        provider = OpenAIEmbeddingProvider(model="text-embedding-3-small")
        assert provider.model == "text-embedding-3-small"
        assert provider.dimension == 512
        assert provider.max_batch_size == 2048


class TestEmbeddingSchemas:
    """Test Pydantic validation schemas."""

    def test_embedding_status_response_schema(self) -> None:
        """Test EmbeddingStatusResponse validation."""
        from app.schemas.embedding import EmbeddingStatusResponse

        response = EmbeddingStatusResponse(
            repository_id=uuid4(),
            status="completed",
            total_chunks=100,
            embedded_chunks=100,
            failed_chunks=0,
            progress_percentage=100.0,
            embedding_model="test-model",
        )

        assert response.status == "completed"
        assert response.progress_percentage == 100.0
        assert response.embedded_chunks == 100

    def test_chunk_search_response_schema(self) -> None:
        """Test ChunkSearchResponse validation."""
        from app.schemas.embedding import ChunkSearchResponse, SimilarChunk

        chunk = SimilarChunk(
            chunk_id=uuid4(),
            score=0.95,
            start_line=10,
            end_line=20,
            chunk_type="function",
            language="python",
        )

        response = ChunkSearchResponse(
            query="test query",
            total_results=1,
            results=[chunk],
        )

        assert response.query == "test query"
        assert len(response.results) == 1
        assert response.results[0].score == 0.95
        assert response.total_results == 1

    def test_embed_repository_request_schema(self) -> None:
        """Test EmbedRepositoryRequest validation."""
        from app.schemas.embedding import EmbedRepositoryRequest

        request = EmbedRepositoryRequest(
            model_name="text-embedding-3-small",
            batch_size=50,
        )

        assert request.model_name == "text-embedding-3-small"
        assert request.batch_size == 50

    def test_embedding_models_list_response(self) -> None:
        """Test EmbeddingModelsListResponse validation."""
        from app.schemas.embedding import (
            EmbeddingModelsListResponse,
            EmbeddingModelRead,
        )
        from datetime import datetime

        model = EmbeddingModelRead(
            id=uuid4(),
            name="test-model",
            provider="local",
            model_identifier="test/model",
            vector_dimension=384,
            context_length=512,
            max_batch_size=128,
            cost_per_1k_tokens=None,
            is_active=True,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        response = EmbeddingModelsListResponse(total_models=1, models=[model])
        assert response.total_models == 1
        assert len(response.models) == 1
        assert response.models[0].name == "test-model"
