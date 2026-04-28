import hashlib
from collections import Counter
from pathlib import Path
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.repository_file import RepositoryFile
from app.repositories.repository_file_repository import RepositoryFileRepository
from app.repositories.repository_repository import RepositoryRepository
from app.schemas.repository_file import RepositoryScanResponse
from app.services.language_detection_service import LanguageDetectionService
from app.services.repository_ingestion_service import ProjectNotFoundError


class RepositoryScanError(Exception):
    pass


class RepositoryScannerService:
    SKIP_DIRECTORIES = {
        ".git",
        ".hg",
        ".svn",
        "__pycache__",
        "node_modules",
        ".next",
        "dist",
        "build",
        ".venv",
        "venv",
    }

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repositories = RepositoryRepository(session)
        self.repository_files = RepositoryFileRepository(session)
        self.language_detector = LanguageDetectionService()

    async def scan_repository(self, project_id: UUID, repository_id: UUID) -> RepositoryScanResponse:
        repository = await self.repositories.get_by_id(repository_id)
        if repository is None or repository.project_id != project_id:
            raise ProjectNotFoundError(str(project_id))

        if repository.status != "ready":
            raise RepositoryScanError("Repository must be in 'ready' status before scanning.")

        root = Path(repository.local_path)
        if not root.exists() or not root.is_dir():
            raise RepositoryScanError("Repository source path does not exist.")

        file_models: list[RepositoryFile] = []
        language_counter: Counter[str] = Counter()

        for file_path in self._iter_files(root):
            raw_bytes = file_path.read_bytes()
            relative_path = file_path.relative_to(root).as_posix()
            language = self.language_detector.detect_language(file_path)
            content_type = self.language_detector.detect_content_type(file_path, raw_bytes)

            file_models.append(
                RepositoryFile(
                    repository_id=repository.id,
                    relative_path=relative_path,
                    file_name=file_path.name,
                    extension=file_path.suffix.lower() or None,
                    language=language,
                    size_bytes=file_path.stat().st_size,
                    content_type=content_type,
                    sha256=hashlib.sha256(raw_bytes).hexdigest(),
                )
            )
            language_counter[language] += 1

        try:
            await self.repository_files.delete_by_repository_id(repository.id)
            if file_models:
                await self.repository_files.bulk_create(file_models)
            await self.session.commit()
        except SQLAlchemyError as exc:
            await self.session.rollback()
            raise RepositoryScanError("Failed to persist repository scan results.") from exc

        return RepositoryScanResponse(
            repository_id=repository.id,
            status="completed",
            scanned_files=len(file_models),
            detected_languages=dict(sorted(language_counter.items())),
        )

    async def list_repository_files(self, project_id: UUID, repository_id: UUID) -> list[RepositoryFile]:
        repository = await self.repositories.get_by_id(repository_id)
        if repository is None or repository.project_id != project_id:
            raise ProjectNotFoundError(str(project_id))
        return await self.repository_files.list_by_repository_id(repository_id)

    def _iter_files(self, root: Path) -> list[Path]:
        paths: list[Path] = []
        for path in root.rglob("*"):
            if path.is_dir():
                continue

            if any(part in self.SKIP_DIRECTORIES for part in path.parts):
                continue

            paths.append(path)
        return sorted(paths)
