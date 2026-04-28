from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.core.config import get_settings
from app.schemas.repository import RepositoryCloneRequest, RepositoryRead
from app.services.repository_ingestion_service import (
    InvalidRepositorySourceError,
    ProjectNotFoundError,
    RepositoryIngestionError,
    RepositoryIngestionService,
)

router = APIRouter(prefix="/projects/{project_id}/repositories")


@router.post("/clone", response_model=RepositoryRead, status_code=status.HTTP_201_CREATED)
async def clone_repository(
    project_id: UUID,
    payload: RepositoryCloneRequest,
    session: AsyncSession = Depends(get_db_session),
) -> RepositoryRead:
    service = RepositoryIngestionService(session, get_settings())
    try:
        repository = await service.clone_repository(project_id, payload)
    except ProjectNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")
    except InvalidRepositorySourceError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except (SQLAlchemyError, OSError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is unavailable.",
        ) from exc
    except RepositoryIngestionError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    return RepositoryRead.model_validate(repository)


@router.post("/upload", response_model=RepositoryRead, status_code=status.HTTP_201_CREATED)
async def upload_repository(
    project_id: UUID,
    archive: Annotated[UploadFile, File(...)],
    name: Annotated[str | None, Form()] = None,
    session: AsyncSession = Depends(get_db_session),
) -> RepositoryRead:
    service = RepositoryIngestionService(session, get_settings())
    try:
        repository = await service.upload_repository(project_id, archive, name)
    except ProjectNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")
    except InvalidRepositorySourceError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except (SQLAlchemyError, OSError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is unavailable.",
        ) from exc
    except RepositoryIngestionError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    return RepositoryRead.model_validate(repository)


@router.get("", response_model=list[RepositoryRead])
async def list_repositories(
    project_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> list[RepositoryRead]:
    service = RepositoryIngestionService(session, get_settings())
    try:
        repositories = await service.list_repositories(project_id)
    except ProjectNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")
    except (SQLAlchemyError, OSError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is unavailable.",
        ) from exc
    return [RepositoryRead.model_validate(repository) for repository in repositories]


@router.get("/{repository_id}", response_model=RepositoryRead)
async def get_repository(
    project_id: UUID,
    repository_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> RepositoryRead:
    service = RepositoryIngestionService(session, get_settings())
    try:
        repository = await service.get_repository(project_id, repository_id)
    except (SQLAlchemyError, OSError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is unavailable.",
        ) from exc
    if repository is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found.")
    return RepositoryRead.model_validate(repository)
