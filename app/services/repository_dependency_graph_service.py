from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.repository_dependency import RepositoryDependency
from app.repositories.repository_dependency_repository import RepositoryDependencyRepository
from app.repositories.repository_file_repository import RepositoryFileRepository
from app.repositories.repository_import_repository import RepositoryImportRepository
from app.repositories.repository_repository import RepositoryRepository
from app.schemas.repository_dependency import RepositoryDependencyGraphResponse
from app.services.repository_ingestion_service import ProjectNotFoundError


class RepositoryDependencyGraphError(Exception):
    pass


class RepositoryDependencyGraphService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repositories = RepositoryRepository(session)
        self.repository_files = RepositoryFileRepository(session)
        self.repository_imports = RepositoryImportRepository(session)
        self.dependencies = RepositoryDependencyRepository(session)

    async def build_graph(self, project_id: UUID, repository_id: UUID) -> RepositoryDependencyGraphResponse:
        repository = await self.repositories.get_by_id(repository_id)
        if repository is None or repository.project_id != project_id:
            raise ProjectNotFoundError(str(project_id))

        repository_files = await self.repository_files.list_by_repository_id(repository_id)
        repository_imports = await self.repository_imports.list_by_repository_id(repository_id)

        file_by_id = {file.id: file for file in repository_files}
        python_files = [file for file in repository_files if file.language == "python"]
        module_index = {
            self._module_name_from_path(file.relative_path): file.id for file in python_files
        }
        module_roots = {module.split(".")[0] for module in module_index}

        dependencies: list[RepositoryDependency] = []

        for import_record in repository_imports:
            source_file = file_by_id.get(import_record.repository_file_id)
            if source_file is None:
                continue

            source_module_name = self._module_name_from_path(source_file.relative_path)
            target_module_name, target_file_id, is_internal = self._resolve_import_target(
                source_module_name=source_module_name,
                import_type=import_record.import_type,
                module_name=import_record.module_name,
                imported_name=import_record.imported_name,
                module_index=module_index,
                module_roots=module_roots,
            )

            dependencies.append(
                RepositoryDependency(
                    repository_id=repository.id,
                    source_repository_file_id=source_file.id,
                    target_repository_file_id=target_file_id,
                    import_record_id=import_record.id,
                    source_module_name=source_module_name,
                    target_module_name=target_module_name,
                    import_type=import_record.import_type,
                    is_internal=is_internal,
                    is_resolved=target_file_id is not None,
                )
            )

        try:
            await self.dependencies.delete_by_repository_id(repository.id)
            if dependencies:
                await self.dependencies.bulk_create(dependencies)
            await self.session.commit()
        except SQLAlchemyError as exc:
            await self.session.rollback()
            raise RepositoryDependencyGraphError("Failed to persist dependency graph results.") from exc

        internal_count = sum(1 for dep in dependencies if dep.is_internal)
        resolved_count = sum(1 for dep in dependencies if dep.is_resolved)
        external_count = sum(1 for dep in dependencies if not dep.is_internal)

        return RepositoryDependencyGraphResponse(
            repository_id=repository.id,
            dependency_count=len(dependencies),
            internal_dependencies=internal_count,
            resolved_dependencies=resolved_count,
            external_dependencies=external_count,
            unresolved_dependencies=len(dependencies) - resolved_count,
        )

    async def list_dependencies(self, project_id: UUID, repository_id: UUID) -> list[RepositoryDependency]:
        repository = await self.repositories.get_by_id(repository_id)
        if repository is None or repository.project_id != project_id:
            raise ProjectNotFoundError(str(project_id))
        return await self.dependencies.list_by_repository_id(repository_id)

    def _resolve_import_target(
        self,
        source_module_name: str,
        import_type: str,
        module_name: str | None,
        imported_name: str | None,
        module_index: dict[str, UUID],
        module_roots: set[str],
    ) -> tuple[str, UUID | None, bool]:
        candidates = self._candidate_modules(source_module_name, import_type, module_name, imported_name)

        for candidate in candidates:
            if candidate in module_index:
                return candidate, module_index[candidate], True

        target_module_name = candidates[0] if candidates else (module_name or imported_name or "unknown")
        top_level = target_module_name.split(".")[0] if target_module_name else ""
        is_internal = (module_name or "").startswith(".") or top_level in module_roots
        return target_module_name, None, is_internal

    def _candidate_modules(
        self,
        source_module_name: str,
        import_type: str,
        module_name: str | None,
        imported_name: str | None,
    ) -> list[str]:
        if import_type == "import":
            return [module_name or "unknown"]

        base_module = self._resolve_relative_module(source_module_name, module_name or "")
        candidates: list[str] = []
        if imported_name and imported_name != "*":
            if base_module:
                candidates.append(f"{base_module}.{imported_name}")
            else:
                candidates.append(imported_name)
        if base_module:
            candidates.append(base_module)
        return candidates or [imported_name or module_name or "unknown"]

    def _resolve_relative_module(self, source_module_name: str, module_name: str) -> str:
        if not module_name.startswith("."):
            return module_name

        level = len(module_name) - len(module_name.lstrip("."))
        suffix = module_name.lstrip(".")
        source_parts = source_module_name.split(".")
        package_parts = source_parts[:-1]
        cutoff = len(package_parts) - (level - 1)
        base_parts = package_parts[: max(cutoff, 0)]
        if suffix:
            base_parts.extend(suffix.split("."))
        return ".".join(part for part in base_parts if part)

    def _module_name_from_path(self, relative_path: str) -> str:
        normalized = relative_path.replace("\\", "/")
        parts = normalized.split("/")
        if parts[-1] == "__init__.py":
            parts = parts[:-1]
        else:
            parts[-1] = parts[-1].rsplit(".", 1)[0]
        return ".".join(part for part in parts if part)
