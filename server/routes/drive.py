"""Google Drive file listing and download endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from server.drive.client import list_mp4_files, download_file

router = APIRouter()


def _get_token(authorization: str) -> str:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    return authorization[7:]


@router.get("/files")
async def list_files(authorization: str = Header(...), page_token: str | None = None):
    """List user's mp4 files from Google Drive."""
    token = _get_token(authorization)
    try:
        return await list_mp4_files(token, page_token)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Drive API error: {e}")


class DownloadRequest(BaseModel):
    file_ids: list[str]


@router.post("/download")
async def download_files(body: DownloadRequest, authorization: str = Header(...)):
    """Download selected videos from Drive to local storage."""
    token = _get_token(authorization)
    results = []
    for fid in body.file_ids:
        try:
            path = await download_file(token, fid, "data/downloads")
            results.append({"file_id": fid, "local_path": str(path), "status": "ok"})
        except Exception as e:
            results.append({"file_id": fid, "error": str(e), "status": "error"})
    return {"downloads": results}
