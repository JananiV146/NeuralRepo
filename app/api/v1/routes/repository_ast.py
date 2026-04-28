from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.schemas.repository_ast import (
    RepositoryAstAnalysisResponse,
    RepositoryImportRead,
    RepositorySymbolRead,
)
from app.services.repository_ast_service import RepositoryAstAnalysisError, RepositoryAstService
from app.services.repository_ingestion_service import ProjectNotFoundError

router = APIRouter(prefix="/projects/{project_id}/repositories/{repository_id}/ast")


@router.post("/analyze", response_model=RepositoryAstAnalysisResponse, status_code=status.HTTP_202_ACCEPTED)
async def analyze_repository_ast(
    project_id: UUID,
    repository_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> RepositoryAstAnalysisResponse:
    service = RepositoryAstService(session)
    try:
        return await service.analyze_repository(project_id, repository_id)
    except ProjectNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found.")
    except RepositoryAstAnalysisError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except (SQLAlchemyError, OSError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is unavailable.",
        ) from exc


@router.get("/symbols", response_model=list[RepositorySymbolRead])
async def list_repository_symbols(
    project_id: UUID,
    repository_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> list[RepositorySymbolRead]:
    service = RepositoryAstService(session)
    try:
        symbols = await service.list_symbols(project_id, repository_id)
    except ProjectNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found.")
    except (SQLAlchemyError, OSError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is unavailable.",
        ) from exc
    return [RepositorySymbolRead.model_validate(symbol) for symbol in symbols]


@router.get("/imports", response_model=list[RepositoryImportRead])
async def list_repository_imports(
    project_id: UUID,
    repository_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> list[RepositoryImportRead]:
    service = RepositoryAstService(session)
    try:
        imports = await service.list_imports(project_id, repository_id)
    except ProjectNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found.")
    except (SQLAlchemyError, OSError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is unavailable.",
        ) from exc
    return [RepositoryImportRead.model_validate(item) for item in imports]
