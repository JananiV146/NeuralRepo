"""Tests for embedding functionality."""

import pytest
from uuid import uuid4


class TestEmbeddingProviders:
    """Test embedding providers."""

    def test_openai_provider_creation(self) -> None:
        """Test OpenAI provider initialization."""
        import os

        # Skip if no API key
        if not os.getenv("OPENAI_API_KEY"):
            pytest.skip("OPENAI_API_KEY not set")

        from app.services.embedding_provider_service import OpenAIEmbeddingProvider

        provider = OpenAIEmbeddingProvider(model="text-embedding-3-small")
        assert provider.model == "text-embedding-3-small"
        assert provider.dimension == 512
        assert provider.max_batch_size == 2048

    def test_local_provider_creation(self) -> None:
        """Test local provider initialization."""
        from app.services.embedding_provider_service import LocalEmbeddingProvider

        provider = LocalEmbeddingProvider(model_name="all-MiniLM-L6-v2")
        assert provider.model_name == "all-MiniLM-L6-v2"
        assert provider.dimension == 384
        assert provider.max_batch_size == 128

    @pytest.mark.asyncio
    async def test_local_provider_embedding(self) -> None:
        """Test local provider can generate embeddings."""
        from app.services.embedding_provider_service import LocalEmbeddingProvider

        provider = LocalEmbeddingProvider()
        texts = [
            "def hello_world():",
            "def add(a, b):",
            "class Calculator:",
        ]

        embeddings = await provider.embed(texts)

        assert len(embeddings) == 3
        assert all(len(emb) == 384 for emb in embeddings)

    def test_embedding_provider_factory(self) -> None:
        """Test embedding provider factory."""
        from app.services.embedding_provider_service import (
            EmbeddingProviderFactory,
            LocalEmbeddingProvider,
        )

        provider = EmbeddingProviderFactory.create("local")
        assert isinstance(provider, LocalEmbeddingProvider)

    def test_factory_raises_on_invalid_provider(self) -> None:
        """Test factory raises on invalid provider."""
        from app.services.embedding_provider_service import EmbeddingProviderFactory

        with pytest.raises(ValueError):
            EmbeddingProviderFactory.create("invalid_provider")


class TestQdrantClient:
    """Test Qdrant vector DB client."""

    @pytest.mark.asyncio
    async def test_qdrant_client_init(self) -> None:
        """Test Qdrant client initialization."""
        from app.services.qdrant_client_service import QdrantVectorDB

        # This should not raise even if Qdrant is not running
        client = QdrantVectorDB()
        assert client.url
        await client.close()

    @pytest.mark.asyncio
    async def test_embedding_embedding_model_operations(self) -> None:
        """Test embedding model CRUD operations."""
        from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
        from sqlalchemy.orm import sessionmaker

        from app.db.base import Base
        from app.models.embedding import EmbeddingModel
        from app.repositories.embedding_repository import EmbeddingModelRepository

        # Create in-memory SQLite
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with AsyncSessionLocal() as session:
            repo = EmbeddingModelRepository(session)

            # Create
            model = EmbeddingModel(
                name="test-model",
                provider="local",
                model_identifier="test/model",
                vector_dimension=384,
                context_length=256,
                max_batch_size=100,
            )
            created = await repo.create(model)
            assert created.id

            # Get by name
            retrieved = await repo.get_by_name("test-model")
            assert retrieved
            assert retrieved.name == "test-model"

            # List active
            active = await repo.list_active()
            assert len(active) > 0

        await engine.dispose()


class TestEmbeddingJob:
    """Test embedding job tracking."""

    @pytest.mark.asyncio
    async def test_embedding_job_operations(self) -> None:
        """Test embedding job CRUD operations."""
        from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
        from sqlalchemy.orm import sessionmaker

        from app.db.base import Base
        from app.models.embedding import EmbeddingJob
        from app.repositories.embedding_repository import EmbeddingJobRepository

        # Create in-memory SQLite
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with AsyncSessionLocal() as session:
            repo = EmbeddingJobRepository(session)

            repo_id = uuid4()

            # Create
            job = EmbeddingJob(
                repository_id=repo_id,
                embedding_model="test-model",
                status="processing",
                total_chunks=100,
            )
            created = await repo.create(job)
            assert created.id

            # Get by ID
            retrieved = await repo.get_by_id(created.id)
            assert retrieved
            assert retrieved.status == "processing"

            # Get latest by repository
            latest = await repo.get_latest_by_repository(repo_id)
            assert latest
            assert latest.id == created.id

            # List by status
            processing_jobs = await repo.list_by_status("processing")
            assert len(processing_jobs) > 0

            # Update progress
            await repo.update_progress(created.id, 50, 5)
            updated = await repo.get_by_id(created.id)
            assert updated.embedded_chunks == 50
            assert updated.failed_chunks == 5

        await engine.dispose()


class TestEmbeddingSchemas:
    """Test embedding schemas."""

    def test_embedding_status_response(self) -> None:
        """Test embedding status response schema."""
        from app.schemas.embedding import EmbeddingStatusResponse
        from datetime import datetime

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

    def test_chunk_search_response(self) -> None:
        """Test chunk search response schema."""
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
