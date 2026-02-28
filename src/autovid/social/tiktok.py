"""TikTok Content Posting API integration."""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class TikTokUploader:
    """Upload videos to TikTok via Content Posting API."""

    def __init__(self, credentials: dict[str, str]) -> None:
        self.credentials = credentials

    async def upload(
        self,
        video_path: str,
        title: str,
    ) -> dict[str, str]:
        """Upload via init -> PUT binary -> inbox flow."""
        logger.info("TikTok upload: %s", title)
        # TODO: POST /v2/post/publish/inbox/video/init/
        # TODO: PUT binary to upload_url
        return {"status": "pending"}
