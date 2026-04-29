from fastapi import APIRouter

from app.api.v1.routes.chunks import router as chunks_router
from app.api.v1.routes.embeddings import router as embeddings_router
from app.api.v1.routes.health import router as health_router
from app.api.v1.routes.projects import router as projects_router
from app.api.v1.routes.repository_ast import router as repository_ast_router
from app.api.v1.routes.repository_files import router as repository_files_router
from app.api.v1.routes.repository_graph import router as repository_graph_router
from app.api.v1.routes.repositories import router as repositories_router

api_router = APIRouter()
api_router.include_router(health_router, tags=["health"])
api_router.include_router(projects_router, prefix="/projects", tags=["projects"])
api_router.include_router(repositories_router, tags=["repositories"])
api_router.include_router(repository_files_router, tags=["repository-files"])
api_router.include_router(repository_ast_router, tags=["repository-ast"])
api_router.include_router(repository_graph_router, tags=["repository-graph"])
api_router.include_router(chunks_router, tags=["code-chunks"])
api_router.include_router(embeddings_router, tags=["embeddings"])
