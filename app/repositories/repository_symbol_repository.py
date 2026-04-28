from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.repository_symbol import RepositorySymbol


class RepositorySymbolRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def bulk_create(self, symbols: list[RepositorySymbol]) -> None:
        self.session.add_all(symbols)
        await self.session.flush()

    async def delete_by_repository_id(self, repository_id: UUID) -> None:
        await self.session.execute(
            delete(RepositorySymbol).where(RepositorySymbol.repository_id == repository_id)
        )

    async def list_by_repository_id(self, repository_id: UUID) -> list[RepositorySymbol]:
        result = await self.session.execute(
            select(RepositorySymbol)
            .where(RepositorySymbol.repository_id == repository_id)
            .order_by(RepositorySymbol.qualified_name.asc(), RepositorySymbol.line_start.asc())
        )
        return list(result.scalars().all())
