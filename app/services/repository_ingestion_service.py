import asyncio
import shutil
import tarfile
import zipfile
from pathlib import Path
from urllib.parse import urlparse
from uuid import UUID

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.models.repository import Repository
from app.repositories.project_repository import ProjectRepository
from app.repositories.repository_repository import RepositoryRepository
from app.schemas.repository import RepositoryCloneRequest
from app.services.repository_storage_service import RepositoryStorageService


class ProjectNotFoundError(Exception):
    pass


class InvalidRepositorySourceError(Exception):
    pass


class RepositoryIngestionError(Exception):
    pass


class RepositoryIngestionService:
    ARCHIVE_EXTENSIONS = (".zip", ".tar", ".tar.gz", ".tgz")
    ALLOWED_GITHUB_HOSTS = {"github.com", "www.github.com"}

    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self.session = session
        self.settings = settings
        self.projects = ProjectRepository(session)
        self.repositories = RepositoryRepository(session)
        self.storage = RepositoryStorageService(settings)

    async def clone_repository(
        self,
        project_id: UUID,
        payload: RepositoryCloneRequest,
    ) -> Repository:
        project = await self.projects.get_by_id(project_id)
        if project is None:
            raise ProjectNotFoundError(str(project_id))

        normalized_url = self._validate_github_url(str(payload.source_url))
        repository = Repository(
            project_id=project_id,
            name=payload.name or self._derive_name_from_url(normalized_url),
            source_type="github",
            source_url=normalized_url,
            branch=payload.branch,
            status="pending",
            local_path="",
        )
        repository = await self.repositories.create(repository)
        directories = self.storage.ensure_repository_directories(project_id, repository.id)
        repository.local_path = str(directories["source"].resolve())
        repository.status = "cloning"
        await self.repositories.update(repository)
        await self.session.commit()

        try:
            await self._run_git_clone(
                source_url=normalized_url,
                target_path=directories["source"],
                branch=payload.branch,
            )
            repository.status = "ready"
            repository.error_message = None
        except Exception as exc:
            repository.status = "failed"
            repository.error_message = str(exc)
            await self.repositories.update(repository)
            await self.session.commit()
            raise RepositoryIngestionError(str(exc)) from exc

        await self.repositories.update(repository)
        await self.session.commit()
        return repository

    async def upload_repository(
        self,
        project_id: UUID,
        upload: UploadFile,
        name: str | None = None,
    ) -> Repository:
        project = await self.projects.get_by_id(project_id)
        if project is None:
            raise ProjectNotFoundError(str(project_id))

        filename = upload.filename or "uploaded-archive"
        self._validate_archive_filename(filename)

        repository = Repository(
            project_id=project_id,
            name=name or self._derive_name_from_filename(filename),
            source_type="upload",
            source_url=None,
            branch=None,
            status="pending",
            local_path="",
            archive_name=filename,
        )
        repository = await self.repositories.create(repository)
        directories = self.storage.ensure_repository_directories(project_id, repository.id)
        repository.local_path = str(directories["source"].resolve())
        repository.status = "extracting"
        await self.repositories.update(repository)
        await self.session.commit()

        archive_path = directories["uploads"] / filename

        try:
            await self._persist_upload(upload, archive_path)
            await self._extract_archive(archive_path, directories["source"])
            repository.status = "ready"
            repository.error_message = None
        except Exception as exc:
            repository.status = "failed"
            repository.error_message = str(exc)
            await self.repositories.update(repository)
            await self.session.commit()
            raise RepositoryIngestionError(str(exc)) from exc
        finally:
            await upload.close()

        await self.repositories.update(repository)
        await self.session.commit()
        return repository

    async def get_repository(self, project_id: UUID, repository_id: UUID) -> Repository | None:
        repository = await self.repositories.get_by_id(repository_id)
        if repository is None or repository.project_id != project_id:
            return None
        return repository

    async def list_repositories(self, project_id: UUID) -> list[Repository]:
        project = await self.projects.get_by_id(project_id)
        if project is None:
            raise ProjectNotFoundError(str(project_id))
        return await self.repositories.list_by_project_id(project_id)

    def _validate_github_url(self, source_url: str) -> str:
        parsed = urlparse(source_url)
        if parsed.scheme != "https" or parsed.netloc not in self.ALLOWED_GITHUB_HOSTS:
            raise InvalidRepositorySourceError("Only HTTPS GitHub repository URLs are supported.")

        path_parts = [part for part in parsed.path.split("/") if part]
        if len(path_parts) < 2:
            raise InvalidRepositorySourceError("GitHub repository URL must include owner and repo.")

        repository_name = path_parts[1]
        if repository_name.endswith(".git"):
            repository_name = repository_name[:-4]

        return f"https://github.com/{path_parts[0]}/{repository_name}"

    def _validate_archive_filename(self, filename: str) -> None:
        lowered = filename.lower()
        if not lowered.endswith(self.ARCHIVE_EXTENSIONS):
            raise InvalidRepositorySourceError(
                "Uploaded repository must be a .zip, .tar, .tar.gz, or .tgz archive."
            )

    def _derive_name_from_url(self, source_url: str) -> str:
        repo_name = source_url.rstrip("/").split("/")[-1]
        if repo_name.endswith(".git"):
            repo_name = repo_name[:-4]
        return repo_name

    def _derive_name_from_filename(self, filename: str) -> str:
        lowered = filename.lower()
        for extension in sorted(self.ARCHIVE_EXTENSIONS, key=len, reverse=True):
            if lowered.endswith(extension):
                return filename[: -len(extension)]
        return filename

    async def _run_git_clone(self, source_url: str, target_path: Path, branch: str | None) -> None:
        if any(target_path.iterdir()):
            shutil.rmtree(target_path)
            target_path.mkdir(parents=True, exist_ok=True)

        command = ["git", "clone", "--depth", "1"]
        if branch:
            command.extend(["--branch", branch])
        command.extend([source_url, str(target_path)])

        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await process.communicate()

        if process.returncode != 0:
            error_message = stderr.decode("utf-8", errors="ignore").strip() or "git clone failed"
            raise RepositoryIngestionError(error_message)

    async def _persist_upload(self, upload: UploadFile, archive_path: Path) -> None:
        archive_path.parent.mkdir(parents=True, exist_ok=True)
        max_bytes = self.settings.max_upload_size_mb * 1024 * 1024
        written = 0

        with archive_path.open("wb") as buffer:
            while True:
                chunk = await upload.read(1024 * 1024)
                if not chunk:
                    break

                written += len(chunk)
                if written > max_bytes:
                    raise InvalidRepositorySourceError(
                        f"Uploaded archive exceeds the {self.settings.max_upload_size_mb} MB limit."
                    )
                buffer.write(chunk)

    async def _extract_archive(self, archive_path: Path, destination: Path) -> None:
        destination.mkdir(parents=True, exist_ok=True)
        if any(destination.iterdir()):
            shutil.rmtree(destination)
            destination.mkdir(parents=True, exist_ok=True)

        lowered = archive_path.name.lower()
        if lowered.endswith(".zip"):
            await asyncio.to_thread(self._extract_zip, archive_path, destination)
            return

        if lowered.endswith((".tar", ".tar.gz", ".tgz")):
            await asyncio.to_thread(self._extract_tar, archive_path, destination)
            return

        raise InvalidRepositorySourceError("Unsupported archive format.")

    def _extract_zip(self, archive_path: Path, destination: Path) -> None:
        with zipfile.ZipFile(archive_path) as archive:
            for member in archive.infolist():
                self._assert_safe_member_path(destination, member.filename)
            archive.extractall(destination)

    def _extract_tar(self, archive_path: Path, destination: Path) -> None:
        with tarfile.open(archive_path) as archive:
            for member in archive.getmembers():
                self._assert_safe_member_path(destination, member.name)
            archive.extractall(destination)

    def _assert_safe_member_path(self, destination: Path, member_name: str) -> None:
        target_path = (destination / member_name).resolve()
        destination_root = destination.resolve()
        if destination_root not in target_path.parents and target_path != destination_root:
            raise InvalidRepositorySourceError("Archive contains invalid paths.")
