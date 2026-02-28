"""Google Drive API client — list and download mp4 files."""
from __future__ import annotations

import logging
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

DRIVE_FILES_URL = "https://www.googleapis.com/drive/v3/files"


async def list_mp4_files(access_token: str, page_token: str | None = None) -> dict:
    """List user's mp4 files from Google Drive."""
    params = {
        "q": "mimeType='video/mp4' and trashed=false",
        "fields": "nextPageToken,files(id,name,mimeType,size,thumbnailLink,videoMediaMetadata)",
        "pageSize": 50,
        "orderBy": "modifiedTime desc",
    }
    if page_token:
        params["pageToken"] = page_token

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            DRIVE_FILES_URL,
            params=params,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        resp.raise_for_status()
        data = resp.json()

    files = []
    for f in data.get("files", []):
        meta = f.get("videoMediaMetadata", {})
        files.append({
            "id": f["id"],
            "name": f["name"],
            "mime_type": f.get("mimeType", ""),
            "size_bytes": int(f.get("size", 0)),
            "thumbnail_url": f.get("thumbnailLink", ""),
            "duration_s": int(meta.get("durationMillis", 0)) / 1000,
        })

    return {"files": files, "next_page_token": data.get("nextPageToken")}


async def download_file(access_token: str, file_id: str, dest_dir: str) -> Path:
    """Download a single file from Drive to local disk."""
    dest = Path(dest_dir)
    dest.mkdir(parents=True, exist_ok=True)

    # Get filename
    async with httpx.AsyncClient() as client:
        meta = await client.get(
            f"{DRIVE_FILES_URL}/{file_id}",
            params={"fields": "name"},
            headers={"Authorization": f"Bearer {access_token}"},
        )
        meta.raise_for_status()
        filename = meta.json()["name"]

    out_path = dest / filename
    logger.info("Downloading %s → %s", file_id, out_path)

    async with httpx.AsyncClient(timeout=600.0) as client:
        async with client.stream(
            "GET",
            f"{DRIVE_FILES_URL}/{file_id}",
            params={"alt": "media"},
            headers={"Authorization": f"Bearer {access_token}"},
        ) as resp:
            resp.raise_for_status()
            with open(out_path, "wb") as f:
                async for chunk in resp.aiter_bytes(chunk_size=8192):
                    f.write(chunk)

    logger.info("Downloaded %s (%d bytes)", filename, out_path.stat().st_size)
    return out_path
