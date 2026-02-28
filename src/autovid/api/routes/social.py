"""Social account management REST endpoints."""
from __future__ import annotations

import logging

from fastapi import APIRouter

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/social-accounts")
async def register_social_account(
    platform: str,
    access_token: str,
    refresh_token: str | None = None,
) -> dict:
    """Register OAuth tokens for a social platform."""
    logger.info("Registering %s social account", platform)
    # TODO: Encrypt and store tokens in database
    return {"platform": platform, "status": "connected"}


@router.get("/social-accounts")
async def list_social_accounts() -> dict:
    """List connected social accounts."""
    # TODO: Query database for connected accounts
    return {"accounts": []}
