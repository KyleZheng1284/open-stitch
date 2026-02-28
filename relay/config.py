"""Relay configuration via environment variables."""
from __future__ import annotations

import os
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings


class RelaySettings(BaseSettings):
    relay_bind: str = "127.0.0.1:8090"
    relay_shared_token: str = ""

    upstream_base_url: str = Field(default="https://inference-api.nvidia.com/v1")
    upstream_api_key: str = ""

    allowed_models: str = "gcp/google/gemini-3-pro,gcp/google/gemini-2.5-flash-lite,azure/openai/gpt-5.2"

    request_timeout_s: int = 180

    connect_timeout_s: int = 10
    health_probe_timeout_s: int = 5

    model_config = {
        "env_file": (".env.relay", ".env"),
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    @property
    def model_allowlist(self) -> set[str]:
        return {m.strip() for m in self.allowed_models.split(",") if m.strip()}


@lru_cache(maxsize=1)
def get_settings() -> RelaySettings:
    s = RelaySettings()

    # Backward-compatible fallbacks to current project env names.
    if not s.upstream_api_key:
        s.upstream_api_key = os.getenv("NVIDIA_API_KEY", "")
    if s.upstream_base_url == "https://inference-api.nvidia.com/v1":
        s.upstream_base_url = os.getenv("NVIDIA_BASE_URL", s.upstream_base_url)

    return s
