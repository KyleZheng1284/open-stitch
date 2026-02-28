"""FastAPI application with REST endpoints and WebSocket support.

This is the API gateway for Auto-Vid. It handles:
- REST endpoints for project CRUD, video uploads, job management
- WebSocket connections for real-time pipeline status streaming
- CORS configuration for frontend development
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from autovid.config import get_settings

from .routes import clips, jobs, projects, social

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: startup and shutdown hooks."""
    settings = get_settings()
    logger.info("Starting Auto-Vid API server")
    logger.info("Database: %s", settings.database_url.split("@")[-1])
    logger.info("Redis: %s", settings.redis_url)
    logger.info("MinIO: %s", settings.minio_endpoint)
    # TODO: Initialize database connection pool
    # TODO: Initialize Redis connection
    # TODO: Initialize MinIO client
    # TODO: Initialize OpenTelemetry tracer
    yield
    logger.info("Shutting down Auto-Vid API server")
    # TODO: Close connection pools


app = FastAPI(
    title="Auto-Vid API",
    description="Agentic short-form video editing platform",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS for frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register route modules
app.include_router(projects.router, prefix="/api/v1", tags=["projects"])
app.include_router(jobs.router, prefix="/api/v1", tags=["jobs"])
app.include_router(clips.router, prefix="/api/v1", tags=["clips"])
app.include_router(social.router, prefix="/api/v1", tags=["social"])


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "autovid-api"}


def main() -> None:
    """Entry point for `autovid` CLI command (pyproject.toml [project.scripts])."""
    import uvicorn

    uvicorn.run(
        "autovid.api.app:app",
        host="0.0.0.0",
        port=8080,
        reload=True,
        log_level="info",
    )
