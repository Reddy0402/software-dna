from fastapi import APIRouter
from app.api.v1.endpoints import health, repositories, scan

api_router = APIRouter()

# Include endpoint routers
api_router.include_router(health.router, tags=["health"])
api_router.include_router(repositories.router, prefix="/repositories", tags=["repositories"])
api_router.include_router(scan.router, prefix="/repositories", tags=["scanner"])
