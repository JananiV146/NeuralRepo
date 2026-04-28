from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.schemas.code_chunk import (
    ChunkingConfigRequest,
    ChunkingStatisticsResponse,
    CodeChunkRead,
    RepositoryChunkingResponse,
)
from app.services.chunking_strategy_service import ChunkConfig, ChunkingStrategy
from app.services.repository_chunking_service import (
    RepositoryChunkingError,
    RepositoryChunkingService,
)
from app.services.repository_ingestion_service import ProjectNotFoundError

router = APIRouter(prefix="/projects/{project_id}/repositories/{repository_id}")


@router.post("/chunks/process", response_model=RepositoryChunkingResponse, status_code=status.HTTP_202_ACCEPTED)
async def process_repository_chunks(
    project_id: UUID,
    repository_id: UUID,
    config: ChunkingConfigRequest = ChunkingConfigRequest(),
    session: AsyncSession = Depends(get_db_session),
) -> RepositoryChunkingResponse:
    """
    Process repository files and create code chunks.

    This endpoint:
    - Deletes existing chunks
    - Reads all code files
    - Chunks them using specified strategy
    - Saves chunks to database

    **Query Parameters:**
    - `strategy`: semantic | fixed_size | sliding_window (default: semantic)
    - `max_tokens`: Max tokens per chunk (default: 512)
    - `max_characters`: Max characters per chunk (default: 2000)

    **Strategies:**
    - **semantic**: Chunks by functions, classes, modules (best for understanding)
    - **fixed_size**: Fixed character/token chunks (predictable)
    - **sliding_window**: Fixed chunks with overlap (best for RAG)

    **Response:**
    - `total_chunks_created`: Number of chunks successfully created
    - `files_processed`: Number of files processed
    - `chunking_errors`: Map of files to error messages
    """
    try:
        chunk_config = ChunkConfig(
            strategy=ChunkingStrategy(config.strategy),
            max_tokens=config.max_tokens,
            max_characters=config.max_characters,
            overlap_tokens=config.overlap_tokens,
            chunk_by_symbols=config.chunk_by_symbols,
            include_docstrings=config.include_docstrings,
            preserve_context=config.preserve_context,
        )

        service = RepositoryChunkingService(session)
        response = await service.chunk_repository(project_id, repository_id, chunk_config)
        return response

    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except RepositoryChunkingError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database error")


@router.get("/chunks", response_model=list[CodeChunkRead])
async def list_repository_chunks(
    project_id: UUID,
    repository_id: UUID,
    strategy: str | None = None,
    chunk_type: str | None = None,
    session: AsyncSession = Depends(get_db_session),
) -> list[CodeChunkRead]:
    """
    List code chunks in repository.

    **Query Parameters:**
    - `strategy`: Filter by chunking strategy (semantic, fixed_size, sliding_window)
    - `chunk_type`: Filter by chunk type (module, class, function, method, block, paragraph)

    **Returns:** List of CodeChunk objects
    """
    try:
        service = RepositoryChunkingService(session)
        chunks = await service.list_repository_chunks(project_id, repository_id, strategy, chunk_type)
        return chunks

    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except SQLAlchemyError:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database error")


@router.get("/chunks/statistics", response_model=ChunkingStatisticsResponse)
async def get_chunking_statistics(
    project_id: UUID,
    repository_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> ChunkingStatisticsResponse:
    """
    Get chunking statistics for repository.

    **Returns:**
    - `total_chunks`: Total number of chunks
    - `embedded_chunks`: Number of chunks with embeddings
    - `by_strategy`: Chunks breakdown by strategy
    - `by_type`: Chunks breakdown by type
    - `embedding_coverage`: Percentage of chunks with embeddings
    """
    try:
        service = RepositoryChunkingService(session)
        stats = await service.get_chunking_statistics(project_id, repository_id)

        return ChunkingStatisticsResponse(
            repository_id=repository_id,
            total_chunks=stats["total_chunks"],
            embedded_chunks=stats["embedded_chunks"],
            embedding_coverage=stats["embedding_coverage"],
            by_strategy=stats["by_strategy"],
            by_type=stats["by_type"],
        )

    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except SQLAlchemyError:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database error")


@router.get("/files/{file_id}/chunks", response_model=list[CodeChunkRead])
async def list_file_chunks(
    project_id: UUID,
    repository_id: UUID,
    file_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> list[CodeChunkRead]:
    """
    List chunks for a specific file.

    **Path Parameters:**
    - `file_id`: Repository file ID

    **Returns:** List of CodeChunk objects for the file
    """
    try:
        service = RepositoryChunkingService(session)
        chunks = await service.list_file_chunks(project_id, repository_id, file_id)
        return chunks

    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except RepositoryChunkingError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except SQLAlchemyError:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database error")


@router.post("/files/{file_id}/chunks/update", response_model=dict, status_code=status.HTTP_202_ACCEPTED)
async def update_file_chunks(
    project_id: UUID,
    repository_id: UUID,
    file_id: UUID,
    config: ChunkingConfigRequest = ChunkingConfigRequest(),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """
    Update chunks for a specific file (incremental update).

    Useful when individual file is modified and needs rechunking.

    **Path Parameters:**
    - `file_id`: Repository file ID

    **Returns:** Number of chunks created
    """
    try:
        chunk_config = ChunkConfig(
            strategy=ChunkingStrategy(config.strategy),
            max_tokens=config.max_tokens,
            max_characters=config.max_characters,
            overlap_tokens=config.overlap_tokens,
            chunk_by_symbols=config.chunk_by_symbols,
        )

        service = RepositoryChunkingService(session)
        chunks_count = await service.update_file_chunks(project_id, repository_id, file_id, chunk_config)

        return {"file_id": file_id, "chunks_created": chunks_count}

    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except RepositoryChunkingError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except SQLAlchemyError:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database error")
