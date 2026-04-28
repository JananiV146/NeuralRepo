from collections.abc import AsyncIterator

from fastapi import FastAPI

from app.db.session import engine


async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    yield
    await engine.dispose()

