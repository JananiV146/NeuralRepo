from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.repository_dependency import RepositoryDependency


class RepositoryDependencyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def bulk_create(self, dependencies: list[RepositoryDependency]) -> None:
        self.session.add_all(dependencies)
        await self.session.flush()

    async def delete_by_repository_id(self, repository_id: UUID) -> None:
        await self.session.execute(
            delete(RepositoryDependency).where(RepositoryDependency.repository_id == repository_id)
        )

    async def list_by_repository_id(self, repository_id: UUID) -> list[RepositoryDependency]:
        result = await self.session.execute(
            select(RepositoryDependency)
            .where(RepositoryDependency.repository_id == repository_id)
            .order_by(
                RepositoryDependency.source_module_name.asc(),
                RepositoryDependency.target_module_name.asc(),
            )
        )
        return list(result.scalars().all())
