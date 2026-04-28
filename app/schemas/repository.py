from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class RepositoryCloneRequest(BaseModel):
    source_url: HttpUrl
    branch: str | None = Field(default=None, max_length=255)
    name: str | None = Field(default=None, min_length=1, max_length=255)


class RepositoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    name: str
    source_type: str
    source_url: str | None
    branch: str | None
    status: str
    local_path: str
    archive_name: str | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime
