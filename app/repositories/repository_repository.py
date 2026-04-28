from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.repository import Repository


class RepositoryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, repository: Repository) -> Repository:
        self.session.add(repository)
        await self.session.flush()
        await self.session.refresh(repository)
        return repository

    async def update(self, repository: Repository) -> Repository:
        self.session.add(repository)
        await self.session.flush()
        await self.session.refresh(repository)
        return repository

    async def get_by_id(self, repository_id: UUID) -> Repository | None:
        result = await self.session.execute(
            select(Repository).where(Repository.id == repository_id)
        )
        return result.scalar_one_or_none()

    async def list_by_project_id(self, project_id: UUID) -> list[Repository]:
        result = await self.session.execute(
            select(Repository)
            .where(Repository.project_id == project_id)
            .order_by(Repository.created_at.desc())
        )
        return list(result.scalars().all())
