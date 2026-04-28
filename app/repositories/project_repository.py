from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project


class ProjectRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, project: Project) -> Project:
        self.session.add(project)
        await self.session.flush()
        await self.session.refresh(project)
        return project

    async def get_by_id(self, project_id: UUID) -> Project | None:
        result = await self.session.execute(select(Project).where(Project.id == project_id))
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> Project | None:
        result = await self.session.execute(select(Project).where(Project.name == name))
        return result.scalar_one_or_none()

