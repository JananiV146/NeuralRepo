from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.schemas.error import ErrorResponse
from app.services.project_service import ProjectAlreadyExistsError


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ProjectAlreadyExistsError)
    async def handle_project_exists(
        _: Request,
        exc: ProjectAlreadyExistsError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=ErrorResponse(
                detail=f"Project '{exc.project_name}' already exists.",
                error_code="project_already_exists",
            ).model_dump(),
        )
