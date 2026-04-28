from uuid import uuid4

import pytest

from app.core.config import Settings
from app.services.repository_ingestion_service import (
    InvalidRepositorySourceError,
    RepositoryIngestionService,
)


class _SessionStub:
    pass


@pytest.fixture()
def ingestion_service(tmp_path) -> RepositoryIngestionService:
    settings = Settings(storage_root=tmp_path)
    return RepositoryIngestionService(_SessionStub(), settings)


def test_validate_github_url_accepts_normal_repo_url(
    ingestion_service: RepositoryIngestionService,
) -> None:
    url = ingestion_service._validate_github_url("https://github.com/openai/openai-python")

    assert url == "https://github.com/openai/openai-python"


def test_validate_github_url_rejects_non_github_domain(
    ingestion_service: RepositoryIngestionService,
) -> None:
    with pytest.raises(InvalidRepositorySourceError):
        ingestion_service._validate_github_url("https://gitlab.com/group/project")


def test_validate_archive_filename_rejects_invalid_extension(
    ingestion_service: RepositoryIngestionService,
) -> None:
    with pytest.raises(InvalidRepositorySourceError):
        ingestion_service._validate_archive_filename("repository.exe")


def test_storage_layout_uses_project_and_repository_ids(tmp_path) -> None:
    settings = Settings(storage_root=tmp_path)
    service = RepositoryIngestionService(_SessionStub(), settings)
    project_id = uuid4()
    repository_id = uuid4()

    directories = service.storage.ensure_repository_directories(project_id, repository_id)

    assert directories["source"].exists()
    assert str(project_id) in str(directories["root"])
    assert str(repository_id) in str(directories["root"])
