import uuid
from typing import Any

from sqlalchemy import and_, delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.code_chunk import CodeChunk


class CodeChunkRepository:
    """Repository for managing CodeChunk database operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, chunk: CodeChunk) -> CodeChunk:
        """Create a new code chunk."""
        self.session.add(chunk)
        await self.session.flush()
        return chunk

    async def create_many(self, chunks: list[CodeChunk]) -> list[CodeChunk]:
        """Create multiple code chunks in bulk."""
        self.session.add_all(chunks)
        await self.session.flush()
        return chunks

    async def get_by_id(self, chunk_id: uuid.UUID) -> CodeChunk | None:
        """Retrieve a code chunk by ID."""
        stmt = select(CodeChunk).where(CodeChunk.id == chunk_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def list_by_repository_id(
        self,
        repository_id: uuid.UUID,
        strategy: str | None = None,
        chunk_type: str | None = None,
    ) -> list[CodeChunk]:
        """List code chunks for a repository, optionally filtered by strategy or type."""
        conditions = [CodeChunk.repository_id == repository_id]

        if strategy:
            conditions.append(CodeChunk.chunking_strategy == strategy)
        if chunk_type:
            conditions.append(CodeChunk.chunk_type == chunk_type)

        stmt = select(CodeChunk).where(and_(*conditions)).order_by(CodeChunk.chunk_index)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def list_by_file_id(
        self,
        file_id: uuid.UUID,
        strategy: str | None = None,
    ) -> list[CodeChunk]:
        """List code chunks for a specific file."""
        conditions = [CodeChunk.repository_file_id == file_id]

        if strategy:
            conditions.append(CodeChunk.chunking_strategy == strategy)

        stmt = select(CodeChunk).where(and_(*conditions)).order_by(CodeChunk.chunk_index)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def list_by_symbol_id(self, symbol_id: uuid.UUID) -> list[CodeChunk]:
        """List code chunks associated with a specific symbol."""
        stmt = select(CodeChunk).where(CodeChunk.primary_symbol_id == symbol_id)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_chunks_by_lines(
        self,
        file_id: uuid.UUID,
        start_line: int,
        end_line: int,
    ) -> list[CodeChunk]:
        """Get chunks that overlap with specified line range."""
        stmt = select(CodeChunk).where(
            and_(
                CodeChunk.repository_file_id == file_id,
                CodeChunk.start_line <= end_line,
                CodeChunk.end_line >= start_line,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def update_embedding(
        self,
        chunk_id: uuid.UUID,
        embedding: bytes,
        model: str,
    ) -> CodeChunk | None:
        """Update embedding for a chunk."""
        chunk = await self.get_by_id(chunk_id)
        if chunk:
            chunk.embedding = embedding
            chunk.embedding_model = model
            await self.session.flush()
        return chunk

    async def delete_by_repository_id(self, repository_id: uuid.UUID) -> int:
        """Delete all code chunks for a repository."""
        stmt = delete(CodeChunk).where(CodeChunk.repository_id == repository_id)
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount

    async def delete_by_file_id(self, file_id: uuid.UUID) -> int:
        """Delete all code chunks for a specific file."""
        stmt = delete(CodeChunk).where(CodeChunk.repository_file_id == file_id)
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount

    async def get_statistics(self, repository_id: uuid.UUID) -> dict[str, Any]:
        """Get chunking statistics for a repository."""
        from sqlalchemy import func

        # Total chunks
        total_stmt = select(func.count(CodeChunk.id)).where(CodeChunk.repository_id == repository_id)
        total_result = await self.session.execute(total_stmt)
        total_chunks = total_result.scalar() or 0

        # By strategy
        strategy_stmt = (
            select(CodeChunk.chunking_strategy, func.count(CodeChunk.id))
            .where(CodeChunk.repository_id == repository_id)
            .group_by(CodeChunk.chunking_strategy)
        )
        strategy_result = await self.session.execute(strategy_stmt)
        by_strategy = {row[0]: row[1] for row in strategy_result.all()}

        # By type
        type_stmt = (
            select(CodeChunk.chunk_type, func.count(CodeChunk.id))
            .where(CodeChunk.repository_id == repository_id)
            .group_by(CodeChunk.chunk_type)
        )
        type_result = await self.session.execute(type_stmt)
        by_type = {row[0]: row[1] for row in type_result.all()}

        # Embeddings status
        embedded_stmt = select(func.count(CodeChunk.id)).where(
            and_(
                CodeChunk.repository_id == repository_id,
                CodeChunk.embedding.isnot(None),
            )
        )
        embedded_result = await self.session.execute(embedded_stmt)
        embedded_count = embedded_result.scalar() or 0

        return {
            "total_chunks": total_chunks,
            "embedded_chunks": embedded_count,
            "by_strategy": by_strategy,
            "by_type": by_type,
        }
