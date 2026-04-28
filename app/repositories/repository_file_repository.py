from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.repository_file import RepositoryFile


class RepositoryFileRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def bulk_create(self, files: list[RepositoryFile]) -> None:
        self.session.add_all(files)
        await self.session.flush()

    async def delete_by_repository_id(self, repository_id: UUID) -> None:
        await self.session.execute(
            delete(RepositoryFile).where(RepositoryFile.repository_id == repository_id)
        )

    async def list_by_repository_id(self, repository_id: UUID) -> list[RepositoryFile]:
        result = await self.session.execute(
            select(RepositoryFile)
            .where(RepositoryFile.repository_id == repository_id)
            .order_by(RepositoryFile.relative_path.asc())
        )
        return list(result.scalars().all())
