# Codebase Intelligence Assistant

Production-grade AI system for repository understanding, architecture analysis, RAG search, documentation generation, and engineering intelligence workflows.

## Module 1 Scope

This module sets up:

- FastAPI application skeleton
- PostgreSQL integration with async SQLAlchemy
- Alembic migrations
- Environment-based configuration
- Structured logging
- Health and readiness endpoints
- Minimal `projects` domain for future repository ingestion
- Docker and Docker Compose for local development
- Baseline automated tests

## Quick Start

### 1. Copy environment variables

```powershell
Copy-Item .env.example .env
```

### 2. Start local infrastructure

```powershell
docker compose up --build
```

### 3. Run migrations

```powershell
docker compose exec api alembic upgrade head
```

### 4. Open the API docs

- Swagger UI: `http://localhost:8000/docs`
- Health: `http://localhost:8000/api/v1/health`
- Readiness: `http://localhost:8000/api/v1/health/ready`

## Local Development

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .[dev]
uvicorn app.main:app --reload
```

## Tests

```powershell
pytest
```

