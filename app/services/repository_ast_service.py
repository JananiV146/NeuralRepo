from pathlib import Path
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.repository_import import RepositoryImport
from app.models.repository_symbol import RepositorySymbol
from app.repositories.repository_file_repository import RepositoryFileRepository
from app.repositories.repository_import_repository import RepositoryImportRepository
from app.repositories.repository_repository import RepositoryRepository
from app.repositories.repository_symbol_repository import RepositorySymbolRepository
from app.schemas.repository_ast import RepositoryAstAnalysisResponse
from app.services.python_ast_extractor_service import PythonAstExtractorService
from app.services.repository_ingestion_service import ProjectNotFoundError


class RepositoryAstAnalysisError(Exception):
    pass


class RepositoryAstService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repositories = RepositoryRepository(session)
        self.repository_files = RepositoryFileRepository(session)
        self.symbols = RepositorySymbolRepository(session)
        self.imports = RepositoryImportRepository(session)
        self.extractor = PythonAstExtractorService()

    async def analyze_repository(self, project_id: UUID, repository_id: UUID) -> RepositoryAstAnalysisResponse:
        repository = await self.repositories.get_by_id(repository_id)
        if repository is None or repository.project_id != project_id:
            raise ProjectNotFoundError(str(project_id))

        repository_files = await self.repository_files.list_by_repository_id(repository_id)
        python_files = [
            file
            for file in repository_files
            if file.language == "python" and file.content_type == "text"
        ]

        symbols: list[RepositorySymbol] = []
        imports: list[RepositoryImport] = []
        parse_errors: dict[str, str] = {}
        analyzed_files = 0

        for repository_file in python_files:
            file_path = Path(repository.local_path) / repository_file.relative_path
            try:
                source = file_path.read_text(encoding="utf-8")
                extraction = self.extractor.extract(repository_file.relative_path, source)
                analyzed_files += 1
            except (SyntaxError, UnicodeDecodeError, OSError) as exc:
                parse_errors[repository_file.relative_path] = str(exc)
                continue

            symbols.extend(
                RepositorySymbol(
                    repository_id=repository.id,
                    repository_file_id=repository_file.id,
                    symbol_type=item.symbol_type,
                    name=item.name,
                    qualified_name=item.qualified_name,
                    parent_qualified_name=item.parent_qualified_name,
                    line_start=item.line_start,
                    line_end=item.line_end,
                    docstring=item.docstring,
                    is_public=item.is_public,
                )
                for item in extraction.symbols
            )
            imports.extend(
                RepositoryImport(
                    repository_id=repository.id,
                    repository_file_id=repository_file.id,
                    import_type=item.import_type,
                    module_name=item.module_name,
                    imported_name=item.imported_name,
                    alias=item.alias,
                    line_number=item.line_number,
                )
                for item in extraction.imports
            )

        try:
            await self.symbols.delete_by_repository_id(repository.id)
            await self.imports.delete_by_repository_id(repository.id)
            if symbols:
                await self.symbols.bulk_create(symbols)
            if imports:
                await self.imports.bulk_create(imports)
            await self.session.commit()
        except SQLAlchemyError as exc:
            await self.session.rollback()
            raise RepositoryAstAnalysisError("Failed to persist AST analysis results.") from exc

        return RepositoryAstAnalysisResponse(
            repository_id=repository.id,
            analyzed_files=analyzed_files,
            failed_files=len(parse_errors),
            symbol_count=len(symbols),
            import_count=len(imports),
            parse_errors=parse_errors,
        )

    async def list_symbols(self, project_id: UUID, repository_id: UUID) -> list[RepositorySymbol]:
        repository = await self.repositories.get_by_id(repository_id)
        if repository is None or repository.project_id != project_id:
            raise ProjectNotFoundError(str(project_id))
        return await self.symbols.list_by_repository_id(repository_id)

    async def list_imports(self, project_id: UUID, repository_id: UUID) -> list[RepositoryImport]:
        repository = await self.repositories.get_by_id(repository_id)
        if repository is None or repository.project_id != project_id:
            raise ProjectNotFoundError(str(project_id))
        return await self.imports.list_by_repository_id(repository_id)
