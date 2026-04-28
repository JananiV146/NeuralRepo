from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.schemas.repository_file import RepositoryFileRead, RepositoryScanResponse
from app.services.repository_ingestion_service import ProjectNotFoundError
from app.services.repository_scanner_service import RepositoryScanError, RepositoryScannerService

router = APIRouter(prefix="/projects/{project_id}/repositories/{repository_id}")


@router.post("/scan", response_model=RepositoryScanResponse, status_code=status.HTTP_202_ACCEPTED)
async def scan_repository(
    project_id: UUID,
    repository_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> RepositoryScanResponse:
    service = RepositoryScannerService(session)
    try:
        return await service.scan_repository(project_id, repository_id)
    except ProjectNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found.")
    except RepositoryScanError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except (SQLAlchemyError, OSError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is unavailable.",
        ) from exc


@router.get("/files", response_model=list[RepositoryFileRead])
async def list_repository_files(
    project_id: UUID,
    repository_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> list[RepositoryFileRead]:
    service = RepositoryScannerService(session)
    try:
        files = await service.list_repository_files(project_id, repository_id)
    except ProjectNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found.")
    except (SQLAlchemyError, OSError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is unavailable.",
        ) from exc
    return [RepositoryFileRead.model_validate(file) for file in files]
