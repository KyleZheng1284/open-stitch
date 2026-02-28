"""FastAPI application entry point."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles

from server.config import get_settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    settings = get_settings()
    logger.info("Starting Auto-Vid API — db=%s", settings.database_url.split("@")[-1])
    # Ensure upload dir exists
    from pathlib import Path
    Path("data/uploads").mkdir(parents=True, exist_ok=True)
    Path("data/output").mkdir(parents=True, exist_ok=True)
    yield
    logger.info("Shutting down")


app = FastAPI(title="Auto-Vid API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
from server.routes import projects, jobs  # noqa: E402

app.include_router(projects.router, prefix="/api/projects", tags=["projects"])
app.include_router(jobs.router, prefix="/api/jobs", tags=["jobs"])

# Serve uploaded/output files
app.mount("/files", StaticFiles(directory="data"), name="files")


@app.get("/health")
async def health():
    return {"status": "ok"}


def main():
    import uvicorn
    uvicorn.run("server.main:app", host="0.0.0.0", port=8080, reload=True, log_level="info")
