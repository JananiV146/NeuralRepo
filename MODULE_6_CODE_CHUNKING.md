# Module 6: Code Chunking Engine

## Overview

The Code Chunking Engine transforms analyzed source code into semantically meaningful chunks optimized for embedding and RAG (Retrieval-Augmented Generation) retrieval. This module is critical for the intelligence assistant as it determines how code is fragmented for vector embedding.

## 📊 Module Architecture

```
Input: Repository Files + AST Analysis (Module 5 output)
  ↓
┌─────────────────────────────────────────────────┐
│  Chunking Strategy Layer                        │
├─────────────────────────────────────────────────┤
│ • SemanticChunkingStrategy                      │
│ • FixedSizeChunkingStrategy                     │
│ • SlidingWindowChunkingStrategy                 │
│ • ChunkingStrategyFactory                       │
└─────────────────────────────────────────────────┘
  ↓
┌─────────────────────────────────────────────────┐
│  RepositoryChunkingService                      │
├─────────────────────────────────────────────────┤
│ • chunk_repository()                            │
│ • _chunk_file()                                 │
│ • update_file_chunks()                          │
│ • get_chunking_statistics()                     │
└─────────────────────────────────────────────────┘
  ↓
┌─────────────────────────────────────────────────┐
│  API Layer (/projects/{id}/repositories/{id})   │
├─────────────────────────────────────────────────┤
│ • POST /chunks/process                          │
│ • GET /chunks                                   │
│ • GET /chunks/statistics                        │
│ • POST /files/{id}/chunks/update                │
└─────────────────────────────────────────────────┘
  ↓
Output: CodeChunk records in PostgreSQL database
```

## 🗄️ Database Schema

### code_chunks Table

```sql
CREATE TABLE code_chunks (
    id UUID PRIMARY KEY,
    repository_id UUID NOT NULL (FK: repositories),
    repository_file_id UUID NOT NULL (FK: repository_files),
    chunk_index INT NOT NULL,
    
    -- Content
    content TEXT NOT NULL,
    content_hash VARCHAR(64) NOT NULL,
    
    -- Position tracking
    start_line INT NOT NULL,
    end_line INT NOT NULL,
    start_char INT NOT NULL,
    end_char INT NOT NULL,
    
    -- Size metrics
    token_count INT NOT NULL,
    character_count INT NOT NULL,
    
    -- Chunking metadata
    chunking_strategy VARCHAR(50) NOT NULL (INDEX),
    chunk_type VARCHAR(50) NOT NULL (INDEX),
    
    -- Symbol relationship
    primary_symbol_id UUID (FK: repository_symbols, nullable),
    related_symbol_ids JSON (nullable),
    
    -- Language info
    language VARCHAR(20) NOT NULL (INDEX),
    
    -- Embedding (populated by Module 7)
    embedding BYTEA (nullable),
    embedding_model VARCHAR(100) (nullable),
    
    -- Overlap tracking
    is_overlapped BOOLEAN DEFAULT false,
    overlap_source_chunk_ids JSON (nullable),
    
    -- Additional metadata
    metadata JSON (nullable),
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT now(),
    updated_at TIMESTAMP DEFAULT now(),
    
    -- Constraints
    UNIQUE(repository_file_id, chunk_index, chunking_strategy),
    INDEX(repository_id),
    INDEX(chunk_type),
    INDEX(language)
);
```

## 🔧 Implementation Details

### 1. **Chunking Strategies**

#### Semantic Chunking (Recommended for code)
```python
# Groups code by semantic boundaries
- Functions → one chunk each
- Classes → one chunk each  
- Remaining code → paragraph chunks
- Best for: Understanding code structure
- Trade-off: Varying chunk sizes
```

**Advantages:**
- Respects code structure
- Functions/classes are complete units
- Better for symbol-to-code mapping
- Aligns with developer mental models

**Disadvantages:**
- Variable chunk sizes
- Large classes → very large chunks
- May exceed token limits

#### Fixed-Size Chunking
```python
# Splits into fixed character/token count chunks
- Max characters: 2000 (default)
- Consistent size
- Predictable for embedding
```

**Advantages:**
- Predictable sizes
- Works for any language
- Efficient for token-based models

**Disadvantages:**
- May split functions/classes
- Loses semantic boundaries
- Can duplicate code between chunks

#### Sliding Window Chunking
```python
# Fixed-size chunks + overlap for context
- Base chunks: 2000 characters
- Overlap: ~50 tokens between chunks
- Preserves context between chunks
```

**Advantages:**
- Preserves context
- No information loss between chunks
- Best for RAG (Module 8)

**Disadvantages:**
- Increased chunk count (≈2x)
- More storage needed
- Duplicate content

### 2. **Core Components**

#### ChunkConfig
```python
@dataclass
class ChunkConfig:
    strategy: ChunkingStrategy = ChunkingStrategy.SEMANTIC
    max_tokens: int = 512
    max_characters: int = 2000
    overlap_tokens: int = 50
    chunk_by_symbols: bool = True  # Use AST symbols
    include_docstrings: bool = True
    preserve_context: bool = True
```

#### CodeChunk Model
- Stores chunk content
- Tracks source location (line/char ranges)
- Links to primary symbol
- Pre-reserves space for embeddings (Module 7)
- Tracks overlap relationships

#### RepositoryChunkingService
Main orchestrator:
- `chunk_repository()` - Full repository chunking
- `_chunk_file()` - Single file chunking
- `update_file_chunks()` - Incremental updates
- `get_chunking_statistics()` - Analytics

### 3. **Metadata Tracking**

Each chunk stores:
```json
{
  "line_count": 25,
  "has_docstring": true,
  "symbol_name": "process_data",
  "symbol_type": "function",
  "complexity": "medium",  // optional
  "imports": ["os", "sys"],  // optional
  "dependencies": ["numpy", "pandas"]  // optional
}
```

### 4. **Token Counting**

Simple estimation: **1 token ≈ 4 characters**
- GPT-3 tokenizer uses: ~4 chars/token
- Better approach in Module 7: actual tokenization

## 📡 API Endpoints

### 1. Process Repository Chunks
```http
POST /projects/{project_id}/repositories/{repository_id}/chunks/process

Request:
{
  "strategy": "semantic",
  "max_tokens": 512,
  "max_characters": 2000,
  "overlap_tokens": 50,
  "chunk_by_symbols": true,
  "include_docstrings": true,
  "preserve_context": true
}

Response (202 Accepted):
{
  "repository_id": "uuid",
  "status": "success|partial",
  "total_chunks_created": 245,
  "files_processed": 12,
  "failed_files": 0,
  "strategy_used": "semantic",
  "chunking_errors": {}
}
```

### 2. List Repository Chunks
```http
GET /projects/{project_id}/repositories/{repository_id}/chunks?strategy=semantic&chunk_type=function

Response:
[
  {
    "id": "uuid",
    "repository_id": "uuid",
    "repository_file_id": "uuid",
    "chunk_index": 0,
    "content": "def hello():\n    print('Hello')",
    "content_hash": "abc123...",
    "start_line": 5,
    "end_line": 7,
    "start_char": 120,
    "end_char": 160,
    "token_count": 10,
    "character_count": 40,
    "chunking_strategy": "semantic",
    "chunk_type": "function",
    "primary_symbol_id": "uuid",
    "related_symbol_ids": ["uuid1", "uuid2"],
    "language": "python",
    "embedding_model": null,
    "is_overlapped": false,
    "metadata": { "symbol_name": "hello" }
  }
  // ... more chunks
]
```

### 3. Get Chunking Statistics
```http
GET /projects/{project_id}/repositories/{repository_id}/chunks/statistics

Response:
{
  "repository_id": "uuid",
  "total_chunks": 245,
  "embedded_chunks": 0,
  "embedding_coverage": 0.0,
  "by_strategy": {
    "semantic": 200,
    "fixed_size": 45
  },
  "by_type": {
    "function": 120,
    "class": 45,
    "module": 30,
    "paragraph": 50
  }
}
```

### 4. List File Chunks
```http
GET /projects/{project_id}/repositories/{repository_id}/files/{file_id}/chunks

Response: List of CodeChunkRead objects for that file
```

### 5. Update File Chunks
```http
POST /projects/{project_id}/repositories/{repository_id}/files/{file_id}/chunks/update

Request:
{
  "strategy": "sliding_window",
  "max_tokens": 512,
  "overlap_tokens": 75
}

Response (202 Accepted):
{
  "file_id": "uuid",
  "chunks_created": 42
}
```

## 🎯 Integration with Previous Modules

### Module 5 → Module 6 Flow

```
Module 5: Dependency Graph
  ↓ (provides: RepositorySymbol, RepositoryImport)
Module 6: Code Chunking
  ├─ Reads repository files (Module 2, 3)
  ├─ Uses AST symbols (Module 4)
  ├─ Respects module structure (Module 5)
  ↓ (provides: CodeChunk with semantic links)
Module 7: Embedding Pipeline (next)
  ├─ Vectorizes chunk content
  ├─ Stores embeddings in code_chunks.embedding
  ↓ (provides: Vector DB entries)
Module 8: RAG Retrieval
  ├─ Queries by semantic similarity
  ├─ Retrieves related chunks
```

## 📝 Usage Examples

### Example 1: Chunk Python Repository with Semantic Strategy

```python
from app.services.repository_chunking_service import RepositoryChunkingService
from app.schemas.code_chunk import ChunkingConfigRequest

# Create service
service = RepositoryChunkingService(session)

# Configure chunking
config = ChunkConfig(
    strategy=ChunkingStrategy.SEMANTIC,
    max_tokens=512,
    chunk_by_symbols=True,
)

# Chunk repository
response = await service.chunk_repository(
    project_id=uuid.uuid4(),
    repository_id=uuid.uuid4(),
    config=config
)

# Response:
# {
#   "repository_id": "...",
#   "status": "success",
#   "total_chunks_created": 245,
#   "files_processed": 12,
#   "failed_files": 0,
#   "strategy_used": "semantic",
#   "chunking_errors": {}
# }
```

### Example 2: Get Chunks for RAG Retrieval

```python
# List all chunks in repository
chunks = await service.list_repository_chunks(
    project_id=project_id,
    repository_id=repository_id,
    strategy="semantic"
)

# Filter by type
function_chunks = [c for c in chunks if c.chunk_type == "function"]
class_chunks = [c for c in chunks if c.chunk_type == "class"]
```

### Example 3: Update Chunks for Modified File

```python
# When a file changes, rechunk it
chunks_count = await service.update_file_chunks(
    project_id=project_id,
    repository_id=repository_id,
    file_id=file_id,
    config=ChunkConfig(strategy=ChunkingStrategy.SEMANTIC)
)
```

## ✅ Key Features Implemented

### 1. ✓ Three Chunking Strategies
- Semantic: By functions/classes
- Fixed-size: By character count
- Sliding-window: With context overlap

### 2. ✓ AST Integration
- Uses Module 4 symbols for semantic chunking
- Links chunks to primary symbols
- Tracks related symbols

### 3. ✓ Precise Position Tracking
- Line ranges (start_line, end_line)
- Character positions (start_char, end_char)
- Enables precise source navigation

### 4. ✓ Content Hashing
- SHA256 hashes for deduplication
- Change detection
- Integrity verification

### 5. ✓ Overlap Management
- Sliding window creates overlapped chunks
- Tracks source relationships
- Preserves context between chunks

### 6. ✓ Statistics & Monitoring
- Chunk count by strategy
- Chunk count by type
- Embedding coverage percentage
- Error tracking

## 🧪 Testing

### Unit Tests: `test_chunking_strategy.py`
- Semantic chunking with/without symbols
- Fixed-size chunking consistency
- Sliding window overlap creation
- Token estimation accuracy
- Content hashing
- Line range tracking

### Integration Tests: `test_repository_chunking_service.py`
- Full repository chunking workflow
- Statistics calculation
- File-level chunking
- Database operations

Run tests:
```bash
pytest tests/test_chunking_strategy.py -v
pytest tests/test_repository_chunking_service.py -v
```

## 🚀 Running the Module

### 1. Start Database
```bash
docker-compose up -d
```

### 2. Apply Migration
```bash
alembic upgrade head
```

### 3. Start Server
```bash
python -m uvicorn app.main:app --reload
```

### 4. Test Chunking Endpoint
```bash
curl -X POST "http://localhost:8000/projects/{project_id}/repositories/{repo_id}/chunks/process" \
  -H "Content-Type: application/json" \
  -d '{
    "strategy": "semantic",
    "max_tokens": 512,
    "max_characters": 2000,
    "chunk_by_symbols": true
  }'
```

## 📋 Performance Considerations

### Chunking Performance
- Semantic: O(files × symbols) - faster for well-structured code
- Fixed-size: O(files × content_size) - linear, consistent
- Sliding-window: O(files × content_size × 2) - doubled due to overlap

### Storage
- Chunk content stored in TEXT column
- Embeddings stored in BYTEA (Module 7)
- Metadata as JSON for flexibility

### Query Optimization
```python
# Indexes created for:
- repository_id (list by repo)
- repository_file_id (list by file)
- chunking_strategy (filter by strategy)
- chunk_type (filter by type)
- language (language-specific queries)
- UNIQUE(file_id, chunk_index, strategy) - prevents duplicates
```

## 🔄 Integration Checklist

Before moving to Module 7 (Embedding Pipeline):

- [x] Migration created and applied
- [x] CodeChunk model implemented
- [x] Repository layer with CRUD operations
- [x] Three chunking strategies implemented
- [x] Main orchestration service
- [x] API routes for all operations
- [x] Schemas for requests/responses
- [x] Unit tests for strategies
- [x] Integration tests for service
- [x] Error handling throughout
- [x] Database connections verified
- [x] Routes registered in main router

## 🎓 Best Practices Applied

1. **Strategy Pattern** - Multiple chunking algorithms
2. **Factory Pattern** - ChunkingStrategyFactory for strategy creation
3. **Repository Pattern** - Abstracted database operations
4. **Service Layer** - Business logic separated from routes
5. **Async/Await** - Efficient concurrent operations
6. **Type Hints** - Full type safety (Python 3.10+)
7. **Error Handling** - Custom exceptions with context
8. **Logging** - Integrated logging for debugging
9. **Testing** - Comprehensive unit + integration tests
10. **API Documentation** - Docstrings on all endpoints

## ⚠️ Common Mistakes to Avoid

1. **Not using symbols for chunking** - Hurts semantic understanding
2. **Too large chunks** - Exceed embedding model context limits
3. **Too small chunks** - Lose important context
4. **Ignoring overlap** - RAG performance suffers
5. **Not tracking positions** - Can't map back to source
6. **Storing duplicate content** - Wastes space and embeddings
7. **Not handling encoding errors** - Will crash on binary files
8. **Ignoring module structure** - Breaks dependency tracking

## 📊 Recommended Chunk Sizes

| Strategy | Max Chars | Max Tokens | Best For |
|----------|-----------|-----------|----------|
| Semantic | N/A (variable) | Variable | Understanding structure |
| Fixed-size | 2000 | 512 | Consistency |
| Sliding-window | 2000 | 512 | RAG retrieval |

## 🔮 Next Steps (Module 7)

The **Embedding Pipeline** module will:
- Vectorize chunk content using embeddings
- Store vectors in Qdrant vector database
- Handle batch embedding for efficiency
- Support multiple embedding models
- Track embedding versioning

## 📞 Support

For issues or questions:
1. Check error messages in chunking_errors response
2. Review test cases for usage examples
3. Check database migration for schema details
4. Review service docstrings for API details

---

**Module Status**: ✅ Complete and Ready for Integration

**Files Created/Modified**:
- Database: `alembic/versions/20260428_0006_create_code_chunks_table.py`
- Models: `app/models/code_chunk.py`
- Repositories: `app/repositories/code_chunk_repository.py`
- Services: `app/services/chunking_strategy_service.py`, `app/services/repository_chunking_service.py`
- Schemas: `app/schemas/code_chunk.py`
- Routes: `app/api/v1/routes/chunks.py`
- Tests: `tests/test_chunking_strategy.py`, `tests/test_repository_chunking_service.py`
- Router: Updated `app/api/router.py`

**Lines of Code**: ~2,500+ production code + ~400 test code
