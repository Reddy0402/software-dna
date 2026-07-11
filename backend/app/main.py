from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.router import api_router
from app.config import settings
from app.core import setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup actions
    setup_logging()
    yield
    # Shutdown actions (if any)


def create_application() -> FastAPI:
    application = FastAPI(
        title=settings.PROJECT_NAME,
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        lifespan=lifespan,
    )

    # Set all CORS enabled origins
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Adjust in production environments
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register API Version 1 Router
    application.include_router(api_router, prefix=settings.API_V1_STR)

    return application


app = create_application()
