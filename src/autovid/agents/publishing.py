"""Publishing Agent — uploads rendered clips to social platforms.

Handles OAuth token refresh, rate limiting, retry logic, and
platform-specific metadata formatting.
"""
from __future__ import annotations

import logging
from typing import Any

from autovid.schemas.project import Platform

logger = logging.getLogger(__name__)


class PublishResult:
    """Result of a single platform publish attempt."""

    def __init__(
        self,
        platform: Platform,
        status: str,
        share_url: str | None = None,
        error: str | None = None,
    ):
        self.platform = platform
        self.status = status
        self.share_url = share_url
        self.error = error


class PublishingAgent:
    """Uploads clips to social platforms."""

    async def run(
        self,
        clip_uri: str,
        platforms: list[Platform],
        metadata: dict[str, Any],
    ) -> list[PublishResult]:
        """Publish a clip to all specified platforms."""
        results: list[PublishResult] = []

        for platform in platforms:
            logger.info("Publishing to %s: %s", platform.value, clip_uri)
            try:
                result = await self._publish_to_platform(
                    clip_uri=clip_uri,
                    platform=platform,
                    metadata=metadata,
                )
                results.append(result)
            except Exception as e:
                logger.error("Failed to publish to %s: %s", platform.value, e)
                results.append(
                    PublishResult(
                        platform=platform,
                        status="failed",
                        error=str(e),
                    )
                )

        return results

    async def _publish_to_platform(
        self,
        clip_uri: str,
        platform: Platform,
        metadata: dict[str, Any],
    ) -> PublishResult:
        """Dispatch to platform-specific upload logic."""
        match platform:
            case Platform.YOUTUBE_SHORTS | Platform.YOUTUBE_LONG:
                return await self._upload_youtube(clip_uri, metadata)
            case Platform.TIKTOK:
                return await self._upload_tiktok(clip_uri, metadata)
            case Platform.INSTAGRAM:
                return await self._upload_instagram(clip_uri, metadata)

    async def _upload_youtube(
        self, clip_uri: str, metadata: dict[str, Any]
    ) -> PublishResult:
        """Upload to YouTube via Data API v3."""
        # TODO: OAuth token refresh
        # TODO: Resumable upload
        # TODO: Set metadata (title, description, tags, privacyStatus)
        return PublishResult(platform=Platform.YOUTUBE_SHORTS, status="pending")

    async def _upload_tiktok(
        self, clip_uri: str, metadata: dict[str, Any]
    ) -> PublishResult:
        """Upload to TikTok via Content Posting API."""
        # TODO: OAuth token refresh
        # TODO: Init upload -> PUT binary -> inbox confirmation
        return PublishResult(platform=Platform.TIKTOK, status="pending")

    async def _upload_instagram(
        self, clip_uri: str, metadata: dict[str, Any]
    ) -> PublishResult:
        """Upload to Instagram via Graph API."""
        # TODO: OAuth token refresh
        # TODO: Create media container -> poll status -> publish
        return PublishResult(platform=Platform.INSTAGRAM, status="pending")
