"""Google OAuth endpoints."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from server.drive.auth import exchange_code

router = APIRouter()


class AuthCodeRequest(BaseModel):
    code: str


class AuthTokenResponse(BaseModel):
    access_token: str
    refresh_token: str | None = None
    expires_in: int = 3600


@router.post("/google", response_model=AuthTokenResponse)
async def google_auth(body: AuthCodeRequest):
    """Exchange Google OAuth code for tokens."""
    try:
        tokens = await exchange_code(body.code)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    return AuthTokenResponse(
        access_token=tokens["access_token"],
        refresh_token=tokens.get("refresh_token"),
        expires_in=tokens.get("expires_in", 3600),
    )
