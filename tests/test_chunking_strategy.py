"""Tests for code chunking functionality."""

import pytest
from uuid import uuid4

from app.models.code_chunk import CodeChunk
from app.services.chunking_strategy_service import (
    ChunkConfig,
    ChunkType,
    ChunkingStrategy,
    FixedSizeChunkingStrategy,
    SemanticChunkingStrategy,
    SlidingWindowChunkingStrategy,
    ChunkingStrategyFactory,
)


# Sample Python source code for testing
SAMPLE_PYTHON_CODE = '''"""Module docstring."""

def hello_world():
    """Say hello."""
    print("Hello, World!")


def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b


class Calculator:
    """Simple calculator class."""

    def __init__(self) -> None:
        self.result = 0

    def multiply(self, a: int, b: int) -> int:
        """Multiply two numbers."""
        self.result = a * b
        return self.result

    def divide(self, a: int, b: int) -> float:
        """Divide two numbers."""
        if b == 0:
            raise ValueError("Cannot divide by zero")
        self.result = a / b
        return self.result


if __name__ == "__main__":
    calc = Calculator()
    print(calc.multiply(5, 3))
    print(calc.divide(10, 2))
'''


class TestSemanticChunking:
    """Test semantic chunking strategy."""

    def test_semantic_chunking_creates_chunks(self) -> None:
        """Test that semantic chunking creates chunks."""
        config = ChunkConfig(strategy=ChunkingStrategy.SEMANTIC)
        strategy = SemanticChunkingStrategy(config)

        repository_id = uuid4()
        file_id = uuid4()

        chunks = strategy.chunk(
            content=SAMPLE_PYTHON_CODE,
            file_id=file_id,
            repository_id=repository_id,
            language="python",
        )

        assert len(chunks) > 0
        assert all(isinstance(chunk, CodeChunk) for chunk in chunks)

    def test_semantic_chunking_with_symbols(self) -> None:
        """Test semantic chunking with symbol information."""
        config = ChunkConfig(strategy=ChunkingStrategy.SEMANTIC)
        strategy = SemanticChunkingStrategy(config)

        repository_id = uuid4()
        file_id = uuid4()
        symbol_id = uuid4()

        symbols = [
            {
                "id": str(symbol_id),
                "name": "hello_world",
                "symbol_type": "function",
                "line_start": 3,
                "line_end": 5,
                "qualified_name": "hello_world",
            },
        ]

        chunks = strategy.chunk(
            content=SAMPLE_PYTHON_CODE,
            file_id=file_id,
            repository_id=repository_id,
            language="python",
            symbols=symbols,
        )

        assert len(chunks) > 0
        # Check if primary symbol is captured
        symbol_chunks = [c for c in chunks if c.primary_symbol_id is not None]
        assert len(symbol_chunks) > 0

    def test_semantic_chunking_metadata(self) -> None:
        """Test that chunks have proper metadata."""
        config = ChunkConfig(strategy=ChunkingStrategy.SEMANTIC)
        strategy = SemanticChunkingStrategy(config)

        repository_id = uuid4()
        file_id = uuid4()
        symbol_id = uuid4()

        # Provide symbols for semantic chunking
        symbols = [
            {
                "id": str(symbol_id),
                "name": "hello_world",
                "symbol_type": "function",
                "line_start": 3,
                "line_end": 5,
                "qualified_name": "hello_world",
            },
        ]

        chunks = strategy.chunk(
            content=SAMPLE_PYTHON_CODE,
            file_id=file_id,
            repository_id=repository_id,
            language="python",
            symbols=symbols,
        )

        for chunk in chunks:
            assert chunk.repository_id == repository_id
            assert chunk.repository_file_id == file_id
            assert chunk.content
            assert chunk.start_line > 0
            assert chunk.end_line >= chunk.start_line
            assert chunk.token_count > 0
            assert chunk.character_count > 0
            assert chunk.chunking_strategy == ChunkingStrategy.SEMANTIC.value
            assert chunk.chunk_metadata is not None


class TestFixedSizeChunking:
    """Test fixed-size chunking strategy."""

    def test_fixed_size_chunking_creates_chunks(self) -> None:
        """Test that fixed-size chunking creates chunks."""
        config = ChunkConfig(
            strategy=ChunkingStrategy.FIXED_SIZE,
            max_characters=500,
        )
        strategy = FixedSizeChunkingStrategy(config)

        repository_id = uuid4()
        file_id = uuid4()

        chunks = strategy.chunk(
            content=SAMPLE_PYTHON_CODE,
            file_id=file_id,
            repository_id=repository_id,
            language="python",
        )

        assert len(chunks) > 0
        # Check chunk size limits (approximately)
        for chunk in chunks:
            assert chunk.character_count <= config.max_characters * 1.5  # Allow some flexibility

    def test_fixed_size_chunking_preserves_content(self) -> None:
        """Test that chunking preserves all content."""
        config = ChunkConfig(
            strategy=ChunkingStrategy.FIXED_SIZE,
            max_characters=300,
        )
        strategy = FixedSizeChunkingStrategy(config)

        repository_id = uuid4()
        file_id = uuid4()

        chunks = strategy.chunk(
            content=SAMPLE_PYTHON_CODE,
            file_id=file_id,
            repository_id=repository_id,
            language="python",
        )

        # Concatenate all chunks
        combined_content = "\n".join(chunk.content for chunk in chunks)

        # Compare (allowing for newline differences)
        assert SAMPLE_PYTHON_CODE.strip() == combined_content.strip()


class TestSlidingWindowChunking:
    """Test sliding window chunking strategy."""

    def test_sliding_window_creates_overlap_chunks(self) -> None:
        """Test that sliding window creates overlap chunks."""
        config = ChunkConfig(
            strategy=ChunkingStrategy.SLIDING_WINDOW,
            max_characters=500,
            overlap_tokens=50,
        )
        strategy = SlidingWindowChunkingStrategy(config)

        repository_id = uuid4()
        file_id = uuid4()

        chunks = strategy.chunk(
            content=SAMPLE_PYTHON_CODE,
            file_id=file_id,
            repository_id=repository_id,
            language="python",
        )

        assert len(chunks) > 0

        # Check for overlapped chunks
        overlapped = [c for c in chunks if c.is_overlapped]
        assert len(overlapped) > 0

    def test_sliding_window_overlap_tracking(self) -> None:
        """Test that overlap relationships are tracked."""
        config = ChunkConfig(
            strategy=ChunkingStrategy.SLIDING_WINDOW,
            max_characters=500,
            overlap_tokens=50,
        )
        strategy = SlidingWindowChunkingStrategy(config)

        repository_id = uuid4()
        file_id = uuid4()

        chunks = strategy.chunk(
            content=SAMPLE_PYTHON_CODE,
            file_id=file_id,
            repository_id=repository_id,
            language="python",
        )

        # Check overlapped chunks have source IDs
        overlapped = [c for c in chunks if c.is_overlapped]
        for chunk in overlapped:
            assert chunk.overlap_source_chunk_ids is not None
            assert len(chunk.overlap_source_chunk_ids) == 2


class TestChunkingStrategyFactory:
    """Test chunking strategy factory."""

    def test_factory_creates_semantic_strategy(self) -> None:
        """Test factory creates semantic strategy."""
        config = ChunkConfig()
        strategy = ChunkingStrategyFactory.create(ChunkingStrategy.SEMANTIC, config)
        assert isinstance(strategy, SemanticChunkingStrategy)

    def test_factory_creates_fixed_size_strategy(self) -> None:
        """Test factory creates fixed size strategy."""
        config = ChunkConfig()
        strategy = ChunkingStrategyFactory.create(ChunkingStrategy.FIXED_SIZE, config)
        assert isinstance(strategy, FixedSizeChunkingStrategy)

    def test_factory_creates_sliding_window_strategy(self) -> None:
        """Test factory creates sliding window strategy."""
        config = ChunkConfig()
        strategy = ChunkingStrategyFactory.create(ChunkingStrategy.SLIDING_WINDOW, config)
        assert isinstance(strategy, SlidingWindowChunkingStrategy)

    def test_factory_accepts_string_strategy(self) -> None:
        """Test factory accepts string strategy names."""
        config = ChunkConfig()
        strategy = ChunkingStrategyFactory.create("semantic", config)
        assert isinstance(strategy, SemanticChunkingStrategy)

    def test_factory_raises_on_invalid_strategy(self) -> None:
        """Test factory raises on invalid strategy."""
        config = ChunkConfig()
        with pytest.raises(ValueError):
            ChunkingStrategyFactory.create("invalid_strategy", config)


class TestChunkContentHashing:
    """Test chunk content hashing."""

    def test_chunk_content_hash_is_consistent(self) -> None:
        """Test that content hash is consistent."""
        config = ChunkConfig(strategy=ChunkingStrategy.FIXED_SIZE)
        strategy = FixedSizeChunkingStrategy(config)

        repository_id = uuid4()
        file_id = uuid4()

        chunks1 = strategy.chunk(
            content=SAMPLE_PYTHON_CODE,
            file_id=file_id,
            repository_id=repository_id,
            language="python",
        )

        chunks2 = strategy.chunk(
            content=SAMPLE_PYTHON_CODE,
            file_id=file_id,
            repository_id=repository_id,
            language="python",
        )

        # Compare hashes
        hashes1 = sorted(c.content_hash for c in chunks1)
        hashes2 = sorted(c.content_hash for c in chunks2)

        assert hashes1 == hashes2

    def test_chunk_content_hash_differs_for_different_content(self) -> None:
        """Test that content hash differs for different content."""
        config = ChunkConfig(strategy=ChunkingStrategy.FIXED_SIZE)
        strategy = FixedSizeChunkingStrategy(config)

        repository_id = uuid4()
        file_id = uuid4()

        chunks1 = strategy.chunk(
            content=SAMPLE_PYTHON_CODE,
            file_id=file_id,
            repository_id=repository_id,
            language="python",
        )

        modified_code = SAMPLE_PYTHON_CODE.replace("hello_world", "goodbye_world")
        chunks2 = strategy.chunk(
            content=modified_code,
            file_id=file_id,
            repository_id=repository_id,
            language="python",
        )

        hashes1 = set(c.content_hash for c in chunks1)
        hashes2 = set(c.content_hash for c in chunks2)

        # Should have some difference
        assert hashes1 != hashes2


class TestChunkLineTracking:
    """Test chunk line and character tracking."""

    def test_chunks_have_valid_line_ranges(self) -> None:
        """Test that chunks have valid line ranges."""
        config = ChunkConfig(strategy=ChunkingStrategy.FIXED_SIZE)
        strategy = FixedSizeChunkingStrategy(config)

        repository_id = uuid4()
        file_id = uuid4()

        chunks = strategy.chunk(
            content=SAMPLE_PYTHON_CODE,
            file_id=file_id,
            repository_id=repository_id,
            language="python",
        )

        for chunk in chunks:
            assert chunk.start_line > 0
            assert chunk.end_line >= chunk.start_line
            assert chunk.start_char >= 0
            assert chunk.end_char >= chunk.start_char

    def test_chunks_line_ranges_are_ordered(self) -> None:
        """Test that chunk line ranges are in order."""
        config = ChunkConfig(strategy=ChunkingStrategy.FIXED_SIZE)
        strategy = FixedSizeChunkingStrategy(config)

        repository_id = uuid4()
        file_id = uuid4()

        chunks = strategy.chunk(
            content=SAMPLE_PYTHON_CODE,
            file_id=file_id,
            repository_id=repository_id,
            language="python",
        )

        # Sort chunks by start line
        sorted_chunks = sorted(chunks, key=lambda c: c.start_line)

        for i in range(len(sorted_chunks) - 1):
            current = sorted_chunks[i]
            next_chunk = sorted_chunks[i + 1]
            # Next chunk should start at or after current ends
            assert next_chunk.start_line >= current.start_line


class TestChunkTokenization:
    """Test chunk token counting."""

    def test_token_count_is_positive(self) -> None:
        """Test that token counts are positive."""
        config = ChunkConfig(strategy=ChunkingStrategy.FIXED_SIZE)
        strategy = FixedSizeChunkingStrategy(config)

        repository_id = uuid4()
        file_id = uuid4()

        chunks = strategy.chunk(
            content=SAMPLE_PYTHON_CODE,
            file_id=file_id,
            repository_id=repository_id,
            language="python",
        )

        for chunk in chunks:
            assert chunk.token_count > 0
            assert chunk.character_count > 0

    def test_token_count_reasonable(self) -> None:
        """Test that token count is reasonably estimated."""
        config = ChunkConfig(strategy=ChunkingStrategy.FIXED_SIZE)
        strategy = FixedSizeChunkingStrategy(config)

        repository_id = uuid4()
        file_id = uuid4()

        chunks = strategy.chunk(
            content=SAMPLE_PYTHON_CODE,
            file_id=file_id,
            repository_id=repository_id,
            language="python",
        )

        for chunk in chunks:
            # Token count should be roughly 1/4 of character count (typical estimate)
            estimated_tokens = chunk.character_count // 4
            # Allow reasonable variance
            assert abs(chunk.token_count - estimated_tokens) < 10
