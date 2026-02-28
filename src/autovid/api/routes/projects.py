"""Project management REST endpoints.

Handles project creation, video uploads, video sequencing, and
triggering the agentic editing pipeline.
"""
from __future__ import annotations

import logging
from uuid import uuid4

from fastapi import APIRouter, HTTPException, UploadFile, File

from autovid.schemas import ProjectRequest, EditPreferences, Platform

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/projects")
async def create_project(request: ProjectRequest) -> dict:
    """Create a new editing project. Immediately starts async ingestion."""
    logger.info("Creating project %s with %d videos", request.project_id, len(request.video_uris))
    # TODO: Persist project to database
    # TODO: Enqueue async ingestion jobs for each video
    return {
        "project_id": request.project_id,
        "status": "created",
        "video_count": len(request.video_uris),
        "message": "Ingestion started for all videos",
    }


@router.post("/projects/{project_id}/upload")
async def upload_video(project_id: str, file: UploadFile = File(...)) -> dict:
    """Upload a raw video file. Triggers async chunking + ingestion."""
    video_id = str(uuid4())
    logger.info("Uploading video %s to project %s: %s", video_id, project_id, file.filename)
    # TODO: Upload to MinIO object store
    # TODO: Enqueue chunking + ingestion pipeline
    return {
        "video_id": video_id,
        "project_id": project_id,
        "filename": file.filename,
        "status": "uploading",
    }


@router.get("/projects/{project_id}")
async def get_project(project_id: str) -> dict:
    """Get project status, video list, ingestion progress, and clip results."""
    # TODO: Query database for project details
    return {
        "project_id": project_id,
        "status": "active",
        "videos": [],
        "clips": [],
        "ingestion_progress": {},
    }


@router.put("/projects/{project_id}/order")
async def reorder_videos(project_id: str, video_ids: list[str]) -> dict:
    """Update video sequence order (from user drag-and-drop)."""
    logger.info("Reordering videos in project %s: %s", project_id, video_ids)
    # TODO: Update video_sequence in database
    return {
        "project_id": project_id,
        "video_sequence": video_ids,
        "status": "updated",
    }


@router.post("/projects/{project_id}/edit")
async def start_editing(
    project_id: str,
    style_prompt: str,
    preferences: EditPreferences | None = None,
    target_platforms: list[Platform] | None = None,
) -> dict:
    """Submit style prompt to trigger the agentic editing pipeline (Phase 2)."""
    job_id = str(uuid4())
    logger.info(
        "Starting edit job %s for project %s with prompt: %s",
        job_id, project_id, style_prompt[:100],
    )
    # TODO: Validate that ingestion is complete (or at least sufficient)
    # TODO: Enqueue the Director Agent pipeline
    return {
        "job_id": job_id,
        "project_id": project_id,
        "status": "queued",
        "style_prompt": style_prompt,
    }
