"""MinIO/S3 object storage wrapper.

Handles all file uploads, downloads, and presigned URL generation.
Used by ingestion (storing chunks), sandbox staging (copying to containers),
and result export (final clips, thumbnails, subtitles).
"""
from __future__ import annotations

import io
import logging
from typing import BinaryIO

from autovid.config import get_settings

logger = logging.getLogger(__name__)

BUCKETS = {
    "raw": "autovid-raw",
    "chunks": "autovid-chunks",
    "assets": "autovid-assets",
    "output": "autovid-output",
    "thumbnails": "autovid-thumbnails",
}


class ObjectStore:
    """MinIO/S3 object storage client."""

    def __init__(self) -> None:
        self._client = None

    def _get_client(self):
        """Lazy-initialize MinIO client."""
        if self._client is None:
            from minio import Minio
            settings = get_settings()
            self._client = Minio(
                settings.minio_endpoint,
                access_key=settings.minio_access_key,
                secret_key=settings.minio_secret_key,
                secure=settings.minio_secure,
            )
        return self._client

    async def upload(
        self,
        bucket_key: str,
        object_name: str,
        data: bytes | BinaryIO,
        content_type: str = "application/octet-stream",
    ) -> str:
        """Upload a file and return its URI."""
        client = self._get_client()
        bucket = BUCKETS.get(bucket_key, bucket_key)

        if isinstance(data, bytes):
            data = io.BytesIO(data)
            length = len(data.getvalue())
        else:
            data.seek(0, 2)
            length = data.tell()
            data.seek(0)

        client.put_object(bucket, object_name, data, length, content_type)
        uri = f"minio://{bucket}/{object_name}"
        logger.info("Uploaded: %s (%d bytes)", uri, length)
        return uri

    async def download(self, uri: str) -> bytes:
        """Download a file by URI."""
        client = self._get_client()
        bucket, object_name = self._parse_uri(uri)
        response = client.get_object(bucket, object_name)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()

    async def presigned_url(self, uri: str, expires_hours: int = 1) -> str:
        """Generate a presigned download URL."""
        from datetime import timedelta
        client = self._get_client()
        bucket, object_name = self._parse_uri(uri)
        return client.presigned_get_object(
            bucket, object_name, expires=timedelta(hours=expires_hours)
        )

    async def exists(self, uri: str) -> bool:
        """Check if an object exists."""
        client = self._get_client()
        bucket, object_name = self._parse_uri(uri)
        try:
            client.stat_object(bucket, object_name)
            return True
        except Exception:
            return False

    @staticmethod
    def _parse_uri(uri: str) -> tuple[str, str]:
        """Parse minio://bucket/path into (bucket, path)."""
        if uri.startswith("minio://"):
            uri = uri[len("minio://"):]
        parts = uri.split("/", 1)
        if len(parts) != 2:
            raise ValueError(f"Invalid MinIO URI: {uri}")
        return parts[0], parts[1]
