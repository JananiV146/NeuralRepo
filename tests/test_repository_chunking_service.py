"""Integration tests for repository chunking service."""

import pytest
from pathlib import Path
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.repository import Repository
from app.models.repository_file import RepositoryFile
from app.models.code_chunk import CodeChunk
from app.services.chunking_strategy_service import ChunkConfig, ChunkingStrategy
from app.services.repository_chunking_service import RepositoryChunkingService


# Test fixtures can be added here
# Using pytest-asyncio for async test support


class TestRepositoryChunkingService:
    """Integration tests for RepositoryChunkingService."""

    @pytest.mark.asyncio
    async def test_chunk_repository_creates_chunks(self, session: AsyncSession) -> None:
        """Test that chunking a repository creates chunks."""
        # Create test project and repository
        project_id = uuid4()
        repository_id = uuid4()

        repository = Repository(
            id=repository_id,
            project_id=project_id,
            name="test-repo",
            repository_url="https://github.com/test/repo",
            status="ready",
            local_path="/tmp/test-repo",
        )
        session.add(repository)

        # Create a test file
        file_id = uuid4()
        file = RepositoryFile(
            id=file_id,
            repository_id=repository_id,
            relative_path="test.py",
            file_name="test.py",
            extension=".py",
            language="python",
            size_bytes=100,
            content_type="text",
            sha256="abc123",
        )
        session.add(file)
        await session.flush()

        # Create test service
        service = RepositoryChunkingService(session)

        # Note: This test would need proper file system setup
        # In real tests, use temporary directories or mock file operations

    @pytest.mark.asyncio
    async def test_chunking_statistics(self, session: AsyncSession) -> None:
        """Test retrieving chunking statistics."""
        project_id = uuid4()
        repository_id = uuid4()

        # Create repository
        repository = Repository(
            id=repository_id,
            project_id=project_id,
            name="test-repo",
            repository_url="https://github.com/test/repo",
            status="ready",
            local_path="/tmp/test-repo",
        )
        session.add(repository)

        # Create chunks
        file_id = uuid4()
        for i in range(5):
            chunk = CodeChunk(
                repository_id=repository_id,
                repository_file_id=file_id,
                chunk_index=i,
                content=f"chunk {i}",
                content_hash=f"hash{i}",
                start_line=i * 10,
                end_line=(i + 1) * 10,
                start_char=i * 100,
                end_char=(i + 1) * 100,
                token_count=50,
                character_count=500,
                chunking_strategy="semantic",
                chunk_type="function",
                language="python",
            )
            session.add(chunk)

        await session.flush()

        # Test service
        service = RepositoryChunkingService(session)
        stats = await service.get_chunking_statistics(project_id, repository_id)

        assert stats["total_chunks"] == 5
        assert "by_strategy" in stats
        assert "by_type" in stats

    @pytest.mark.asyncio
    async def test_list_file_chunks(self, session: AsyncSession) -> None:
        """Test listing chunks for a specific file."""
        project_id = uuid4()
        repository_id = uuid4()
        file_id = uuid4()

        # Create repository
        repository = Repository(
            id=repository_id,
            project_id=project_id,
            name="test-repo",
            repository_url="https://github.com/test/repo",
            status="ready",
            local_path="/tmp/test-repo",
        )
        session.add(repository)

        # Create chunks for file
        for i in range(3):
            chunk = CodeChunk(
                repository_id=repository_id,
                repository_file_id=file_id,
                chunk_index=i,
                content=f"chunk {i}",
                content_hash=f"hash{i}",
                start_line=i * 10,
                end_line=(i + 1) * 10,
                start_char=i * 100,
                end_char=(i + 1) * 100,
                token_count=50,
                character_count=500,
                chunking_strategy="semantic",
                chunk_type="function",
                language="python",
            )
            session.add(chunk)

        await session.flush()

        service = RepositoryChunkingService(session)
        chunks = await service.list_file_chunks(project_id, repository_id, file_id)

        assert len(chunks) == 3
        assert all(chunk.repository_file_id == file_id for chunk in chunks)
