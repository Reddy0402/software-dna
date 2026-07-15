from fastapi import APIRouter
from app.api.v1.endpoints import health, repositories, scan, parse, extract, dependencies, graph

api_router = APIRouter()

# Include endpoint routers
api_router.include_router(health.router, tags=["health"])
api_router.include_router(repositories.router, prefix="/repositories", tags=["repositories"])
api_router.include_router(scan.router, prefix="/repositories", tags=["scanner"])
api_router.include_router(parse.router, prefix="/files", tags=["parser"])
api_router.include_router(extract.router, prefix="/files", tags=["extractor"])
api_router.include_router(dependencies.router, prefix="/repositories", tags=["dependencies"])
api_router.include_router(graph.router, prefix="/repositories", tags=["graph"])


