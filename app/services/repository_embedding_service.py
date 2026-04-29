"""Repository embedding service - orchestrates the embedding pipeline."""

from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.code_chunk import CodeChunk
from app.models.embedding import EmbeddingJob
from app.repositories.code_chunk_repository import CodeChunkRepository
from app.repositories.embedding_repository import EmbeddingJobRepository, EmbeddingModelRepository
from app.repositories.repository_repository import RepositoryRepository
from app.services.embedding_provider_service import EmbeddingProviderFactory
from app.services.qdrant_client_service import QdrantVectorDB


class RepositoryEmbeddingError(Exception):
    """Raised when embedding operations fail."""

    pass


class RepositoryEmbeddingService:
    """Service for embedding code chunks and storing in vector DB."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repositories = RepositoryRepository(session)
        self.chunks = CodeChunkRepository(session)
        self.embedding_models = EmbeddingModelRepository(session)
        self.embedding_jobs = EmbeddingJobRepository(session)
        self.vector_db = QdrantVectorDB()

    async def embed_repository(
        self,
        project_id: UUID,
        repository_id: UUID,
        model_name: str = "text-embedding-3-small",
        batch_size: int = 100,
    ) -> EmbeddingJob:
        """
        Embed all chunks in a repository.

        Args:
            project_id: Project ID
            repository_id: Repository ID
            model_name: Name of embedding model to use
            batch_size: Batch size for processing

        Returns:
            EmbeddingJob with results

        Raises:
            RepositoryEmbeddingError: If embedding fails
        """
        # Validate repository exists
        repository = await self.repositories.get_by_id(repository_id)
        if repository is None or repository.project_id != project_id:
            raise RepositoryEmbeddingError(f"Repository {repository_id} not found")

        # Get embedding model
        embedding_model = await self.embedding_models.get_by_name(model_name)
        if not embedding_model:
            raise RepositoryEmbeddingError(f"Embedding model {model_name} not found or inactive")

        if not embedding_model.is_active:
            raise RepositoryEmbeddingError(f"Embedding model {model_name} is not active")

        # Create job
        job = EmbeddingJob(
            repository_id=repository_id,
            embedding_model=model_name,
            status="processing",
        )
        job = await self.embedding_jobs.create(job)
        job.started_at = datetime.utcnow()

        try:
            # Get all chunks
            chunks = await self.chunks.list_by_repository_id(repository_id)
            job.total_chunks = len(chunks)

            if not chunks:
                job.status = "completed"
                job.completed_at = datetime.utcnow()
                await self.embedding_jobs.update(job)
                return job

            # Create Qdrant collection for this model
            collection_name = f"repo_{repository_id.hex}_{embedding_model.name.replace('-', '_')}"
            await self.vector_db.create_collection(
                collection_name=collection_name,
                vector_size=embedding_model.vector_dimension,
            )

            # Create embedding provider
            provider = EmbeddingProviderFactory.create(
                embedding_model.provider,
                embedding_model.config or {},
            )

            # Process in batches
            embedded_count = 0
            failed_count = 0

            for i in range(0, len(chunks), batch_size):
                batch_chunks = chunks[i : i + batch_size]

                try:
                    # Extract texts to embed
                    texts = [chunk.content for chunk in batch_chunks]

                    # Generate embeddings
                    embeddings = await provider.embed(texts)

                    # Prepare data for storage
                    embeddings_data = []
                    for chunk, embedding in zip(batch_chunks, embeddings):
                        embeddings_data.append(
                            (
                                chunk.id,
                                embedding,
                                {
                                    "repository_id": str(repository_id),
                                    "file_id": str(chunk.repository_file_id),
                                    "start_line": chunk.start_line,
                                    "end_line": chunk.end_line,
                                    "chunk_type": chunk.chunk_type,
                                    "language": chunk.language,
                                },
                            )
                        )

                    # Store in Qdrant
                    await self.vector_db.store_embeddings_batch(
                        collection_name=collection_name,
                        embeddings_data=embeddings_data,
                    )

                    # Store embedding in database (as binary)
                    import struct

                    for chunk, embedding in zip(batch_chunks, embeddings):
                        # Convert float list to bytes
                        embedding_bytes = struct.pack(f"{len(embedding)}f", *embedding)
                        chunk.embedding = embedding_bytes
                        chunk.embedding_model = model_name

                    await self.session.flush()

                    embedded_count += len(batch_chunks)
                    job.embedded_chunks = embedded_count
                    await self.embedding_jobs.update(job)

                except Exception as e:
                    failed_count += len(batch_chunks)
                    job.failed_chunks = failed_count
                    await self.embedding_jobs.update(job)
                    raise RepositoryEmbeddingError(f"Batch embedding failed: {e}") from e

            # Mark as completed
            job.status = "completed"
            job.completed_at = datetime.utcnow()
            await self.embedding_jobs.update(job)

            await self.session.commit()

        except Exception as e:
            job.status = "failed"
            job.error_message = str(e)
            job.completed_at = datetime.utcnow()
            await self.embedding_jobs.update(job)
            await self.session.commit()
            raise

        return job

    async def search_similar_chunks(
        self,
        project_id: UUID,
        repository_id: UUID,
        query_text: str,
        model_name: str = "text-embedding-3-small",
        limit: int = 10,
    ) -> list[dict]:
        """
        Search for chunks similar to query text.

        Args:
            project_id: Project ID
            repository_id: Repository ID
            query_text: Query text to search for
            model_name: Embedding model to use
            limit: Maximum results

        Returns:
            List of similar chunks with scores
        """
        # Validate
        repository = await self.repositories.get_by_id(repository_id)
        if repository is None or repository.project_id != project_id:
            raise RepositoryEmbeddingError(f"Repository {repository_id} not found")

        embedding_model = await self.embedding_models.get_by_name(model_name)
        if not embedding_model:
            raise RepositoryEmbeddingError(f"Embedding model {model_name} not found")

        # Create provider and embed query
        provider = EmbeddingProviderFactory.create(
            embedding_model.provider,
            embedding_model.config or {},
        )

        query_embedding = await provider.embed([query_text])
        if not query_embedding:
            return []

        # Search in Qdrant
        collection_name = f"repo_{repository_id.hex}_{embedding_model.name.replace('-', '_')}"

        try:
            results = await self.vector_db.search_similar(
                collection_name=collection_name,
                embedding=query_embedding[0],
                limit=limit,
            )

            return results
        except Exception as e:
            raise RepositoryEmbeddingError(f"Similarity search failed: {e}") from e

    async def get_embedding_status(
        self,
        project_id: UUID,
        repository_id: UUID,
    ) -> dict:
        """Get embedding status for repository."""
        repository = await self.repositories.get_by_id(repository_id)
        if repository is None or repository.project_id != project_id:
            raise RepositoryEmbeddingError(f"Repository {repository_id} not found")

        job = await self.embedding_jobs.get_latest_by_repository(repository_id)

        if not job:
            return {
                "repository_id": repository_id,
                "status": "no_embeddings",
                "job": None,
            }

        return {
            "repository_id": repository_id,
            "status": job.status,
            "total_chunks": job.total_chunks,
            "embedded_chunks": job.embedded_chunks,
            "failed_chunks": job.failed_chunks,
            "progress_percentage": job.progress_percentage,
            "embedding_model": job.embedding_model,
            "started_at": job.started_at,
            "completed_at": job.completed_at,
            "error_message": job.error_message,
        }

    async def list_embedding_models(self) -> list[dict]:
        """List available embedding models."""
        models = await self.embedding_models.list_active()
        return [
            {
                "id": str(model.id),
                "name": model.name,
                "provider": model.provider,
                "vector_dimension": model.vector_dimension,
                "context_length": model.context_length,
                "max_batch_size": model.max_batch_size,
            }
            for model in models
        ]

    async def close(self) -> None:
        """Close connections."""
        await self.vector_db.close()
