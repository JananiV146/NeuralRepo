from pathlib import Path
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.code_chunk import CodeChunk
from app.models.repository_symbol import RepositorySymbol
from app.repositories.code_chunk_repository import CodeChunkRepository
from app.repositories.repository_file_repository import RepositoryFileRepository
from app.repositories.repository_repository import RepositoryRepository
from app.repositories.repository_symbol_repository import RepositorySymbolRepository
from app.schemas.code_chunk import RepositoryChunkingResponse
from app.services.chunking_strategy_service import ChunkConfig, ChunkingStrategyFactory
from app.services.repository_ingestion_service import ProjectNotFoundError


class RepositoryChunkingError(Exception):
    """Raised when chunking operations fail."""

    pass


class RepositoryChunkingService:
    """Service for chunking repository code into semantically meaningful pieces."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repositories = RepositoryRepository(session)
        self.repository_files = RepositoryFileRepository(session)
        self.symbols = RepositorySymbolRepository(session)
        self.chunks = CodeChunkRepository(session)

    async def chunk_repository(
        self,
        project_id: UUID,
        repository_id: UUID,
        config: ChunkConfig | None = None,
    ) -> RepositoryChunkingResponse:
        """
        Chunk all files in a repository using specified strategy.

        Args:
            project_id: Project ID
            repository_id: Repository ID
            config: Chunking configuration

        Returns:
            Response with chunking statistics

        Raises:
            ProjectNotFoundError: If project/repository not found
            RepositoryChunkingError: If chunking fails
        """
        config = config or ChunkConfig()

        # Validate repository exists
        repository = await self.repositories.get_by_id(repository_id)
        if repository is None or repository.project_id != project_id:
            raise ProjectNotFoundError(f"Repository {repository_id} not found")

        # Delete existing chunks for fresh chunking
        await self.chunks.delete_by_repository_id(repository_id)

        # Get all repository files
        repository_files = await self.repository_files.list_by_repository_id(repository_id)

        if not repository_files:
            return RepositoryChunkingResponse(
                repository_id=repository_id,
                status="success",
                total_chunks_created=0,
                files_processed=0,
                failed_files=0,
                strategy_used=config.strategy.value,
                chunking_errors={},
            )

        # Filter to code files (Python for now)
        code_files = [f for f in repository_files if f.language == "python" and f.content_type == "text"]

        total_chunks = 0
        files_processed = 0
        failed_files = 0
        chunking_errors: dict[str, str] = {}

        for repository_file in code_files:
            try:
                chunks_count = await self._chunk_file(repository_id, repository_file, config)
                total_chunks += chunks_count
                files_processed += 1
            except Exception as exc:
                failed_files += 1
                chunking_errors[repository_file.relative_path] = str(exc)

        try:
            await self.session.commit()
        except SQLAlchemyError as exc:
            await self.session.rollback()
            raise RepositoryChunkingError(f"Database error during chunking: {exc}") from exc

        return RepositoryChunkingResponse(
            repository_id=repository_id,
            status="success" if failed_files == 0 else "partial",
            total_chunks_created=total_chunks,
            files_processed=files_processed,
            failed_files=failed_files,
            strategy_used=config.strategy.value,
            chunking_errors=chunking_errors,
        )

    async def _chunk_file(
        self,
        repository_id: UUID,
        repository_file,
        config: ChunkConfig,
    ) -> int:
        """
        Chunk a single file.

        Args:
            repository_id: Repository ID
            repository_file: Repository file model
            config: Chunking configuration

        Returns:
            Number of chunks created
        """
        repository = await self.repositories.get_by_id(repository_id)
        if not repository:
            raise RepositoryChunkingError(f"Repository {repository_id} not found")

        # Read file content
        file_path = Path(repository.local_path) / repository_file.relative_path

        try:
            content = file_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            raise RepositoryChunkingError(f"Cannot read file {repository_file.relative_path}: {exc}") from exc

        if not content.strip():
            return 0

        # Get symbols for semantic chunking if available
        symbols = None
        if config.chunk_by_symbols:
            symbols_list = await self.symbols.list_by_file_id(repository_file.id)
            if symbols_list:
                symbols = [
                    {
                        "id": str(s.id),
                        "name": s.name,
                        "symbol_type": s.symbol_type,
                        "line_start": s.line_start,
                        "line_end": s.line_end,
                        "qualified_name": s.qualified_name,
                    }
                    for s in symbols_list
                ]

        # Create chunking strategy
        strategy = ChunkingStrategyFactory.create(config.strategy, config)

        # Generate chunks
        chunks = strategy.chunk(
            content=content,
            file_id=repository_file.id,
            repository_id=repository_id,
            language=repository_file.language,
            symbols=symbols,
        )

        if chunks:
            # Save chunks to database
            await self.chunks.create_many(chunks)

        return len(chunks)

    async def update_file_chunks(
        self,
        project_id: UUID,
        repository_id: UUID,
        file_id: UUID,
        config: ChunkConfig | None = None,
    ) -> int:
        """
        Update chunks for a specific file (useful for incremental updates).

        Args:
            project_id: Project ID
            repository_id: Repository ID
            file_id: File ID
            config: Chunking configuration

        Returns:
            Number of chunks created
        """
        config = config or ChunkConfig()

        # Validate entities exist
        repository = await self.repositories.get_by_id(repository_id)
        if repository is None or repository.project_id != project_id:
            raise ProjectNotFoundError(f"Repository {repository_id} not found")

        repository_file = await self.repository_files.get_by_id(file_id)
        if repository_file is None or repository_file.repository_id != repository_id:
            raise RepositoryChunkingError(f"File {file_id} not found")

        # Delete existing chunks for this file
        await self.chunks.delete_by_file_id(file_id)

        # Chunk the file
        chunks_count = await self._chunk_file(repository_id, repository_file, config)

        await self.session.commit()

        return chunks_count

    async def list_file_chunks(
        self,
        project_id: UUID,
        repository_id: UUID,
        file_id: UUID,
    ) -> list[CodeChunk]:
        """List chunks for a specific file."""
        # Validate entities
        repository = await self.repositories.get_by_id(repository_id)
        if repository is None or repository.project_id != project_id:
            raise ProjectNotFoundError(f"Repository {repository_id} not found")

        return await self.chunks.list_by_file_id(file_id)

    async def list_repository_chunks(
        self,
        project_id: UUID,
        repository_id: UUID,
        strategy: str | None = None,
        chunk_type: str | None = None,
    ) -> list[CodeChunk]:
        """List chunks in repository with optional filters."""
        repository = await self.repositories.get_by_id(repository_id)
        if repository is None or repository.project_id != project_id:
            raise ProjectNotFoundError(f"Repository {repository_id} not found")

        return await self.chunks.list_by_repository_id(repository_id, strategy, chunk_type)

    async def get_chunking_statistics(
        self,
        project_id: UUID,
        repository_id: UUID,
    ) -> dict:
        """Get statistics about repository chunking."""
        repository = await self.repositories.get_by_id(repository_id)
        if repository is None or repository.project_id != project_id:
            raise ProjectNotFoundError(f"Repository {repository_id} not found")

        stats = await self.chunks.get_statistics(repository_id)

        # Calculate coverage percentage
        embedded_count = stats.get("embedded_chunks", 0)
        total_count = stats.get("total_chunks", 0)
        coverage = (embedded_count / total_count * 100) if total_count > 0 else 0

        return {
            "repository_id": repository_id,
            "total_chunks": total_count,
            "embedded_chunks": embedded_count,
            "embedding_coverage": round(coverage, 2),
            "by_strategy": stats.get("by_strategy", {}),
            "by_type": stats.get("by_type", {}),
        }

    async def rechunk_repository(
        self,
        project_id: UUID,
        repository_id: UUID,
        config: ChunkConfig,
    ) -> RepositoryChunkingResponse:
        """
        Rechunk repository with different strategy/config.
        Deletes existing chunks and creates new ones.
        """
        return await self.chunk_repository(project_id, repository_id, config)
