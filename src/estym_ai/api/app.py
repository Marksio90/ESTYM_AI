"""FastAPI application — REST API for the ESTYM_AI platform."""

from __future__ import annotations

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ..config.settings import get_settings
from .routes import cases, files, health, quotes

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    settings = get_settings()
    logger.info("app_starting", env=settings.app_env.value)

    # Initialize database (dev only — use Alembic in production)
    if settings.app_debug:
        try:
            from ..db.session import init_db
            await init_db()
            logger.info("database_initialized")
        except Exception as e:
            logger.warning("database_init_skipped", error=str(e))

    yield

    logger.info("app_shutting_down")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="ESTYM_AI",
        description=(
            "AI-powered steel product estimation platform. "
            "Automates RFQ processing from email intake through CAD analysis, "
            "cost calculation, and ERP export."
        ),
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.app_debug else None,
        redoc_url="/redoc" if settings.app_debug else None,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.app_debug else [],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routers
    app.include_router(health.router, tags=["health"])
    app.include_router(cases.router, prefix="/api/v1/cases", tags=["cases"])
    app.include_router(files.router, prefix="/api/v1/files", tags=["files"])
    app.include_router(quotes.router, prefix="/api/v1/quotes", tags=["quotes"])

    return app
