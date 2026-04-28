from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class RepositoryDependencyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    repository_id: UUID
    source_repository_file_id: UUID
    target_repository_file_id: UUID | None
    import_record_id: UUID
    source_module_name: str
    target_module_name: str
    import_type: str
    is_internal: bool
    is_resolved: bool
    created_at: datetime
    updated_at: datetime


class RepositoryDependencyGraphResponse(BaseModel):
    repository_id: UUID
    dependency_count: int
    internal_dependencies: int
    resolved_dependencies: int
    external_dependencies: int
    unresolved_dependencies: int
