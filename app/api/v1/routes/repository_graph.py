from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.schemas.repository_dependency import (
    RepositoryDependencyGraphResponse,
    RepositoryDependencyRead,
)
from app.services.repository_dependency_graph_service import (
    RepositoryDependencyGraphError,
    RepositoryDependencyGraphService,
)
from app.services.repository_ingestion_service import ProjectNotFoundError

router = APIRouter(prefix="/projects/{project_id}/repositories/{repository_id}/graph")


@router.post("/build", response_model=RepositoryDependencyGraphResponse, status_code=status.HTTP_202_ACCEPTED)
async def build_repository_graph(
    project_id: UUID,
    repository_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> RepositoryDependencyGraphResponse:
    service = RepositoryDependencyGraphService(session)
    try:
        return await service.build_graph(project_id, repository_id)
    except ProjectNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found.")
    except RepositoryDependencyGraphError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except (SQLAlchemyError, OSError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is unavailable.",
        ) from exc


@router.get("/dependencies", response_model=list[RepositoryDependencyRead])
async def list_repository_dependencies(
    project_id: UUID,
    repository_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> list[RepositoryDependencyRead]:
    service = RepositoryDependencyGraphService(session)
    try:
        dependencies = await service.list_dependencies(project_id, repository_id)
    except ProjectNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found.")
    except (SQLAlchemyError, OSError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is unavailable.",
        ) from exc
    return [RepositoryDependencyRead.model_validate(item) for item in dependencies]
