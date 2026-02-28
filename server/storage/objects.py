"""MinIO/S3 object storage wrapper."""
from __future__ import annotations

import io
import logging
from typing import BinaryIO

from server.config import get_settings

logger = logging.getLogger(__name__)

BUCKETS = {
    "raw": "autovid-raw",
    "output": "autovid-output",
}


class ObjectStore:
    def __init__(self):
        self._client = None

    def _get_client(self):
        if self._client is None:
            from minio import Minio
            s = get_settings()
            self._client = Minio(
                s.minio_endpoint,
                access_key=s.minio_access_key,
                secret_key=s.minio_secret_key,
                secure=s.minio_secure,
            )
        return self._client

    async def upload(self, bucket_key: str, name: str, data: bytes | BinaryIO, content_type: str = "application/octet-stream") -> str:
        client = self._get_client()
        bucket = BUCKETS.get(bucket_key, bucket_key)
        if isinstance(data, bytes):
            stream = io.BytesIO(data)
            length = len(data)
        else:
            data.seek(0, 2)
            length = data.tell()
            data.seek(0)
            stream = data
        client.put_object(bucket, name, stream, length, content_type)
        return f"minio://{bucket}/{name}"

    async def download(self, uri: str) -> bytes:
        client = self._get_client()
        bucket, name = self._parse(uri)
        resp = client.get_object(bucket, name)
        try:
            return resp.read()
        finally:
            resp.close()
            resp.release_conn()

    async def presigned_url(self, uri: str, hours: int = 1) -> str:
        from datetime import timedelta
        client = self._get_client()
        bucket, name = self._parse(uri)
        return client.presigned_get_object(bucket, name, expires=timedelta(hours=hours))

    @staticmethod
    def _parse(uri: str) -> tuple[str, str]:
        clean = uri.removeprefix("minio://")
        parts = clean.split("/", 1)
        return parts[0], parts[1]
