"""Clip management REST endpoints."""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/clips/{clip_id}")
async def get_clip(clip_id: str) -> dict:
    """Get clip metadata, download URL, and subtitle files."""
    # TODO: Query clip from database
    return {
        "clip_id": clip_id,
        "status": "rendered",
        "download_url": None,
        "thumbnail_url": None,
        "subtitles": [],
        "duration_ms": 0,
    }


@router.post("/clips/{clip_id}/publish")
async def publish_clip(clip_id: str, platforms: list[str]) -> dict:
    """Publish a rendered clip to specified social platforms."""
    logger.info("Publishing clip %s to %s", clip_id, platforms)
    # TODO: Enqueue publishing tasks per platform
    return {
        "clip_id": clip_id,
        "platforms": platforms,
        "status": "publishing",
        "results": [],
    }
