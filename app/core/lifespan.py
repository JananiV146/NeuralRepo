from collections.abc import AsyncIterator

from fastapi import FastAPI

from app.core.config import get_settings
from app.db.session import engine


async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    settings.repositories_root.mkdir(parents=True, exist_ok=True)
    yield
    await engine.dispose()
