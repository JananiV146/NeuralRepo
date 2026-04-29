from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.schemas.embedding import (
    ChunkSearchResponse,
    EmbedRepositoryRequest,
    EmbeddingJobRead,
    EmbeddingModelsListResponse,
    EmbeddingModelRead,
    EmbeddingStatusResponse,
    SimilarChunk,
)
from app.services.repository_embedding_service import (
    RepositoryEmbeddingError,
    RepositoryEmbeddingService,
)
from app.services.repository_ingestion_service import ProjectNotFoundError

router = APIRouter(prefix="/projects/{project_id}/repositories/{repository_id}")


@router.post(
    "/embeddings/embed",
    response_model=EmbeddingJobRead,
    status_code=status.HTTP_202_ACCEPTED,
)
async def embed_repository(
    project_id: UUID,
    repository_id: UUID,
    request: EmbedRepositoryRequest = EmbedRepositoryRequest(),
    session: AsyncSession = Depends(get_db_session),
) -> EmbeddingJobRead:
    """
    Start embedding all code chunks in repository.

    This endpoint:
    - Generates embeddings for all chunks using specified model
    - Stores vectors in Qdrant vector database
    - Saves embeddings in code_chunks table
    - Returns job status for polling progress

    **Parameters:**
    - `model_name`: Embedding model to use (default: text-embedding-3-small)
    - `batch_size`: Batch size for processing (default: 100)

    **Supported Models:**
    - OpenAI: text-embedding-3-small (512d), text-embedding-3-large (3072d)
    - Local: all-MiniLM-L6-v2 (384d)

    **Response:**
    - Returns EmbeddingJob with initial status
    - Status can be: pending, processing, completed, failed
    - Poll /embeddings/status to track progress
    """
    try:
        service = RepositoryEmbeddingService(session)
        job = await service.embed_repository(
            project_id=project_id,
            repository_id=repository_id,
            model_name=request.model_name,
            batch_size=request.batch_size,
        )
        return job

    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except RepositoryEmbeddingError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get(
    "/embeddings/status",
    response_model=EmbeddingStatusResponse,
)
async def get_embedding_status(
    project_id: UUID,
    repository_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> EmbeddingStatusResponse:
    """
    Get current embedding status for repository.

    **Returns:**
    - `status`: no_embeddings | processing | completed | failed
    - `progress_percentage`: 0-100% if processing
    - `embedded_chunks`: Number successfully embedded
    - `failed_chunks`: Number failed to embed
    """
    try:
        service = RepositoryEmbeddingService(session)
        status_data = await service.get_embedding_status(project_id, repository_id)

        return EmbeddingStatusResponse(**status_data)

    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except RepositoryEmbeddingError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post(
    "/embeddings/search",
    response_model=ChunkSearchResponse,
)
async def search_similar_chunks(
    project_id: UUID,
    repository_id: UUID,
    query: str,
    model_name: str = "text-embedding-3-small",
    limit: int = 10,
    session: AsyncSession = Depends(get_db_session),
) -> ChunkSearchResponse:
    """
    Search for code chunks similar to query text using semantic similarity.

    This endpoint:
    - Embeds the query text
    - Searches Qdrant for similar embeddings
    - Returns ranked results with similarity scores

    **Parameters:**
    - `query`: Text to search for (function name, description, code snippet, etc.)
    - `model_name`: Embedding model to use (must match original)
    - `limit`: Maximum results to return (default: 10)

    **Query Examples:**
    - "authentication function"
    - "database connection"
    - "error handling"
    - Full code snippets

    **Returns:**
    - List of similar chunks ranked by similarity score (0-1)
    - Score 1.0 = identical, 0.0 = no similarity
    """
    try:
        if not query:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Query cannot be empty")

        service = RepositoryEmbeddingService(session)
        results = await service.search_similar_chunks(
            project_id=project_id,
            repository_id=repository_id,
            query_text=query,
            model_name=model_name,
            limit=limit,
        )

        similar_chunks = [
            SimilarChunk(
                chunk_id=UUID(result["chunk_id"]),
                score=result["score"],
                start_line=result["metadata"].get("start_line"),
                end_line=result["metadata"].get("end_line"),
                chunk_type=result["metadata"].get("chunk_type"),
                language=result["metadata"].get("language"),
            )
            for result in results
        ]

        return ChunkSearchResponse(
            query=query,
            total_results=len(similar_chunks),
            results=similar_chunks,
        )

    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except RepositoryEmbeddingError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get(
    "/embeddings/models",
    response_model=EmbeddingModelsListResponse,
)
async def list_embedding_models(
    session: AsyncSession = Depends(get_db_session),
) -> EmbeddingModelsListResponse:
    """
    List available embedding models.

    **Returns:**
    - List of supported embedding models with their specs
    - Includes: provider, dimension, context length, batch size
    """
    try:
        service = RepositoryEmbeddingService(session)
        models = await service.list_embedding_models()

        return EmbeddingModelsListResponse(
            total_models=len(models),
            models=models,
        )

    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))
