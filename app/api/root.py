from fastapi import APIRouter, Response, status

router = APIRouter()


@router.get("/", status_code=status.HTTP_200_OK)
async def root() -> dict[str, str]:
    return {
        "name": "Codebase Intelligence Assistant API",
        "docs": "/docs",
        "health": "/api/v1/health",
    }


@router.get("/favicon.ico", status_code=status.HTTP_204_NO_CONTENT)
async def favicon() -> Response:
    return Response(status_code=status.HTTP_204_NO_CONTENT)
