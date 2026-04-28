from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class RepositoryFileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    repository_id: UUID
    relative_path: str
    file_name: str
    extension: str | None
    language: str
    size_bytes: int
    content_type: str
    sha256: str
    created_at: datetime
    updated_at: datetime


class RepositoryScanResponse(BaseModel):
    repository_id: UUID
    status: str
    scanned_files: int
    detected_languages: dict[str, int]
