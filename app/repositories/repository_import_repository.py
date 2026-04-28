from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.repository_import import RepositoryImport


class RepositoryImportRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def bulk_create(self, imports: list[RepositoryImport]) -> None:
        self.session.add_all(imports)
        await self.session.flush()

    async def delete_by_repository_id(self, repository_id: UUID) -> None:
        await self.session.execute(
            delete(RepositoryImport).where(RepositoryImport.repository_id == repository_id)
        )

    async def list_by_repository_id(self, repository_id: UUID) -> list[RepositoryImport]:
        result = await self.session.execute(
            select(RepositoryImport)
            .where(RepositoryImport.repository_id == repository_id)
            .order_by(RepositoryImport.module_name.asc(), RepositoryImport.line_number.asc())
        )
        return list(result.scalars().all())
