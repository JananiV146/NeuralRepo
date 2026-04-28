from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project
from app.repositories.project_repository import ProjectRepository
from app.schemas.project import ProjectCreate


class ProjectAlreadyExistsError(Exception):
    """Raised when a project name already exists."""

    def __init__(self, project_name: str) -> None:
        super().__init__(project_name)
        self.project_name = project_name


class ProjectService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = ProjectRepository(session)

    async def create_project(self, payload: ProjectCreate) -> Project:
        project = Project(name=payload.name.strip(), description=payload.description)
        try:
            created = await self.repository.create(project)
            await self.session.commit()
            return created
        except IntegrityError as exc:
            await self.session.rollback()
            raise ProjectAlreadyExistsError(payload.name) from exc

    async def get_project(self, project_id: UUID) -> Project | None:
        return await self.repository.get_by_id(project_id)
