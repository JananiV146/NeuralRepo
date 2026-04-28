from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class RepositorySymbolRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    repository_id: UUID
    repository_file_id: UUID
    symbol_type: str
    name: str
    qualified_name: str
    parent_qualified_name: str | None
    line_start: int
    line_end: int
    docstring: str | None
    is_public: bool
    created_at: datetime
    updated_at: datetime


class RepositoryImportRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    repository_id: UUID
    repository_file_id: UUID
    import_type: str
    module_name: str | None
    imported_name: str | None
    alias: str | None
    line_number: int
    created_at: datetime
    updated_at: datetime


class RepositoryAstAnalysisResponse(BaseModel):
    repository_id: UUID
    analyzed_files: int
    failed_files: int
    symbol_count: int
    import_count: int
    parse_errors: dict[str, str]
