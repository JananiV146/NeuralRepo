from pathlib import Path
from uuid import UUID

from app.core.config import Settings


class RepositoryStorageService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def ensure_repository_directories(self, project_id: UUID, repository_id: UUID) -> dict[str, Path]:
        root = self.settings.repositories_root / str(project_id) / str(repository_id)
        repo_dir = root / "source"
        uploads_dir = root / "uploads"

        repo_dir.mkdir(parents=True, exist_ok=True)
        uploads_dir.mkdir(parents=True, exist_ok=True)

        return {
            "root": root,
            "source": repo_dir,
            "uploads": uploads_dir,
        }
