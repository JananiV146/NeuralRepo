import hashlib
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import UUID

from app.models.code_chunk import CodeChunk


class ChunkType(str, Enum):
    """Types of code chunks."""

    MODULE = "module"
    CLASS = "class"
    FUNCTION = "function"
    METHOD = "method"
    BLOCK = "block"
    PARAGRAPH = "paragraph"


class ChunkingStrategy(str, Enum):
    """Code chunking strategies."""

    SEMANTIC = "semantic"
    FIXED_SIZE = "fixed_size"
    SLIDING_WINDOW = "sliding_window"


@dataclass
class ChunkConfig:
    """Configuration for code chunking."""

    strategy: ChunkingStrategy = ChunkingStrategy.SEMANTIC
    max_tokens: int = 512  # Approximate, based on character estimation
    max_characters: int = 2000
    overlap_tokens: int = 50
    chunk_by_symbols: bool = True
    include_docstrings: bool = True
    preserve_context: bool = True


@dataclass
class ChunkingResult:
    """Result of chunking a file."""

    chunks: list[CodeChunk]
    total_chunks: int
    errors: list[str]


class BaseChunkingStrategy(ABC):
    """Abstract base class for chunking strategies."""

    def __init__(self, config: ChunkConfig) -> None:
        self.config = config

    @abstractmethod
    def chunk(
        self,
        content: str,
        file_id: UUID,
        repository_id: UUID,
        language: str,
        symbols: list[dict[str, Any]] | None = None,
    ) -> list[CodeChunk]:
        """
        Chunk content according to strategy.

        Args:
            content: Source code content
            file_id: Repository file ID
            repository_id: Repository ID
            language: Programming language
            symbols: Optional AST symbols from repository

        Returns:
            List of CodeChunk objects
        """
        pass

    def _calculate_token_count(self, text: str) -> int:
        """
        Estimate token count using simple heuristic.
        Rough estimate: 1 token ≈ 4 characters on average.
        """
        return len(text) // 4

    def _create_content_hash(self, content: str) -> str:
        """Create SHA256 hash of chunk content."""
        return hashlib.sha256(content.encode()).hexdigest()

    def _extract_metadata(self, content: str, symbol: dict[str, Any] | None = None) -> dict[str, Any]:
        """Extract metadata from chunk."""
        lines = content.split("\n")
        return {
            "line_count": len(lines),
            "has_docstring": '"""' in content or "'''" in content,
            "symbol_name": symbol.get("name") if symbol else None,
            "symbol_type": symbol.get("symbol_type") if symbol else None,
        }


class SemanticChunkingStrategy(BaseChunkingStrategy):
    """
    Chunks code at semantic boundaries (functions, classes, modules).
    Best for understanding code structure and symbol relationships.
    """

    def chunk(
        self,
        content: str,
        file_id: UUID,
        repository_id: UUID,
        language: str,
        symbols: list[dict[str, Any]] | None = None,
    ) -> list[CodeChunk]:
        """Chunk by semantic units (functions, classes, modules)."""
        chunks: list[CodeChunk] = []

        if language != "python":
            # Fallback to fixed size for non-Python
            return FixedSizeChunkingStrategy(self.config).chunk(
                content, file_id, repository_id, language, symbols
            )

        lines = content.split("\n")

        if not symbols:
            # No symbols available, use fixed size chunking
            return FixedSizeChunkingStrategy(self.config).chunk(
                content, file_id, repository_id, language, None
            )

        # Group symbols by type and line ranges
        chunk_index = 0
        processed_lines = set()

        for symbol in sorted(symbols, key=lambda s: s.get("line_start", 0)):
            line_start = symbol.get("line_start", 0)
            line_end = symbol.get("line_end", len(lines))
            symbol_type = symbol.get("symbol_type", "block")

            # Skip if already processed
            if any(line in processed_lines for line in range(line_start, line_end)):
                continue

            # Extract chunk content
            chunk_lines = lines[line_start - 1 : line_end]
            chunk_content = "\n".join(chunk_lines)

            if not chunk_content.strip():
                continue

            # Create chunk
            chunk = CodeChunk(
                repository_id=repository_id,
                repository_file_id=file_id,
                chunk_index=chunk_index,
                content=chunk_content,
                content_hash=self._create_content_hash(chunk_content),
                start_line=line_start,
                end_line=line_end,
                start_char=sum(len(lines[i]) + 1 for i in range(line_start - 1)),
                end_char=sum(len(lines[i]) + 1 for i in range(line_end)),
                token_count=self._calculate_token_count(chunk_content),
                character_count=len(chunk_content),
                chunking_strategy=ChunkingStrategy.SEMANTIC.value,
                chunk_type=symbol_type,
                primary_symbol_id=UUID(symbol.get("id")) if symbol.get("id") else None,
                language=language,
                metadata=self._extract_metadata(chunk_content, symbol),
            )

            chunks.append(chunk)
            processed_lines.update(range(line_start, line_end))
            chunk_index += 1

        # Add remaining content as paragraph chunks
        uncovered_lines = set(range(1, len(lines) + 1)) - processed_lines
        if uncovered_lines:
            current_block = []
            for line_num in sorted(uncovered_lines):
                line_content = lines[line_num - 1]
                current_block.append((line_num, line_content))

                if (
                    len("\n".join(content for _, content in current_block))
                    > self.config.max_characters
                    or line_num == max(uncovered_lines)
                ):
                    if current_block:
                        block_start = current_block[0][0]
                        block_end = current_block[-1][0]
                        block_content = "\n".join(content for _, content in current_block)

                        chunk = CodeChunk(
                            repository_id=repository_id,
                            repository_file_id=file_id,
                            chunk_index=chunk_index,
                            content=block_content,
                            content_hash=self._create_content_hash(block_content),
                            start_line=block_start,
                            end_line=block_end,
                            start_char=sum(len(lines[i]) + 1 for i in range(block_start - 1)),
                            end_char=sum(len(lines[i]) + 1 for i in range(block_end)),
                            token_count=self._calculate_token_count(block_content),
                            character_count=len(block_content),
                            chunking_strategy=ChunkingStrategy.SEMANTIC.value,
                            chunk_type=ChunkType.PARAGRAPH.value,
                            language=language,
                            metadata=self._extract_metadata(block_content),
                        )

                        chunks.append(chunk)
                        chunk_index += 1
                        current_block = []

        return chunks


class FixedSizeChunkingStrategy(BaseChunkingStrategy):
    """
    Fixed-size chunking by character or token count.
    Simple and predictable, works for all languages.
    """

    def chunk(
        self,
        content: str,
        file_id: UUID,
        repository_id: UUID,
        language: str,
        symbols: list[dict[str, Any]] | None = None,
    ) -> list[CodeChunk]:
        """Chunk content into fixed-size pieces."""
        chunks: list[CodeChunk] = []
        lines = content.split("\n")

        chunk_index = 0
        current_char_pos = 0

        for start_line_idx in range(0, len(lines), max(1, self._estimate_lines_per_chunk())):
            end_line_idx = min(
                start_line_idx + self._estimate_lines_per_chunk(),
                len(lines),
            )

            chunk_lines = lines[start_line_idx:end_line_idx]
            chunk_content = "\n".join(chunk_lines)

            if not chunk_content.strip():
                continue

            # Calculate character positions
            start_char = sum(len(lines[i]) + 1 for i in range(start_line_idx))
            end_char = start_char + len(chunk_content)

            chunk = CodeChunk(
                repository_id=repository_id,
                repository_file_id=file_id,
                chunk_index=chunk_index,
                content=chunk_content,
                content_hash=self._create_content_hash(chunk_content),
                start_line=start_line_idx + 1,
                end_line=end_line_idx,
                start_char=start_char,
                end_char=end_char,
                token_count=self._calculate_token_count(chunk_content),
                character_count=len(chunk_content),
                chunking_strategy=ChunkingStrategy.FIXED_SIZE.value,
                chunk_type=ChunkType.BLOCK.value,
                language=language,
                metadata=self._extract_metadata(chunk_content),
            )

            chunks.append(chunk)
            chunk_index += 1

        return chunks

    def _estimate_lines_per_chunk(self) -> int:
        """Estimate lines per chunk based on max_characters."""
        avg_line_length = 80
        return max(1, self.config.max_characters // avg_line_length)


class SlidingWindowChunkingStrategy(BaseChunkingStrategy):
    """
    Sliding window chunking with overlap.
    Preserves context between chunks for better RAG performance.
    """

    def chunk(
        self,
        content: str,
        file_id: UUID,
        repository_id: UUID,
        language: str,
        symbols: list[dict[str, Any]] | None = None,
    ) -> list[CodeChunk]:
        """Chunk content using sliding window with overlap."""
        chunks: list[CodeChunk] = []
        lines = content.split("\n")

        # Use fixed size first, then add overlap
        fixed_strategy = FixedSizeChunkingStrategy(self.config)
        base_chunks = fixed_strategy.chunk(content, file_id, repository_id, language, symbols)

        # Add overlapping chunks
        overlap_line_count = max(1, self._estimate_overlap_lines())
        chunk_index = len(base_chunks)

        for i in range(len(base_chunks) - 1):
            current_chunk = base_chunks[i]
            next_chunk = base_chunks[i + 1]

            # Create overlap chunk between current and next
            overlap_start = max(current_chunk.end_line - overlap_line_count, current_chunk.start_line + 1)
            overlap_end = min(next_chunk.start_line + overlap_line_count, next_chunk.end_line - 1)

            if overlap_start < overlap_end:
                overlap_lines = lines[overlap_start - 1 : overlap_end]
                overlap_content = "\n".join(overlap_lines)

                if overlap_content.strip():
                    chunk = CodeChunk(
                        repository_id=repository_id,
                        repository_file_id=file_id,
                        chunk_index=chunk_index,
                        content=overlap_content,
                        content_hash=self._create_content_hash(overlap_content),
                        start_line=overlap_start,
                        end_line=overlap_end,
                        start_char=sum(len(lines[idx]) + 1 for idx in range(overlap_start - 1)),
                        end_char=sum(len(lines[idx]) + 1 for idx in range(overlap_end)),
                        token_count=self._calculate_token_count(overlap_content),
                        character_count=len(overlap_content),
                        chunking_strategy=ChunkingStrategy.SLIDING_WINDOW.value,
                        chunk_type=ChunkType.BLOCK.value,
                        language=language,
                        is_overlapped=True,
                        overlap_source_chunk_ids=[base_chunks[i].id, base_chunks[i + 1].id],
                        metadata=self._extract_metadata(overlap_content),
                    )

                    chunks.append(chunk)
                    chunk_index += 1

        # Combine all chunks
        all_chunks = base_chunks + chunks
        return sorted(all_chunks, key=lambda c: (c.start_line, c.chunk_index))

    def _estimate_overlap_lines(self) -> int:
        """Estimate overlap lines based on overlap tokens."""
        avg_line_length = 80
        avg_tokens_per_line = avg_line_length // 4
        return max(1, self.config.overlap_tokens // avg_tokens_per_line)


class ChunkingStrategyFactory:
    """Factory for creating chunking strategies."""

    _strategies = {
        ChunkingStrategy.SEMANTIC: SemanticChunkingStrategy,
        ChunkingStrategy.FIXED_SIZE: FixedSizeChunkingStrategy,
        ChunkingStrategy.SLIDING_WINDOW: SlidingWindowChunkingStrategy,
    }

    @classmethod
    def create(
        self,
        strategy: ChunkingStrategy | str,
        config: ChunkConfig | None = None,
    ) -> BaseChunkingStrategy:
        """Create a chunking strategy instance."""
        if isinstance(strategy, str):
            strategy = ChunkingStrategy(strategy)

        config = config or ChunkConfig()
        strategy_class = self._strategies.get(strategy)

        if not strategy_class:
            raise ValueError(f"Unknown chunking strategy: {strategy}")

        return strategy_class(config)
