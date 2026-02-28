"""Settings and YAML config loaders."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://autovid:autovid_dev@localhost:5432/autovid"
    redis_url: str = "redis://localhost:6379/0"
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_secure: bool = False

    # NVIDIA NIM
    nvidia_api_key: str = ""
    nvidia_base_url: str = "https://inference-api.nvidia.com/v1"

    # Models
    vlm_model: str = "gcp/google/gemini-3-pro"
    llm_model: str = "gcp/google/gemini-3-pro"
    llm_temperature: float = 0.4
    clarifying_model: str = "us/azure/openai/gpt-5-mini"
    clarifying_temperature: float = 0.2
    editing_model: str = "azure/openai/gpt-5.2"
    editing_temperature: float = 0.3
    summary_model: str = "gcp/google/gemini-2.5-flash-lite"
    summary_fps: int = 2
    asr_model: str = "openai/whisper-large-v3-turbo"
    asr_device: str = "cuda:0"

    # Google OAuth
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:5173/auth/callback"

    # Sandbox
    sandbox_image: str = "autovid-sandbox:latest"
    sandbox_timeout_s: int = 600

    config_dir: str = "config"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


def _load_yaml(filepath: str | Path) -> dict[str, Any]:
    path = Path(filepath)
    if not path.exists():
        return {}
    with open(path) as f:
        return yaml.safe_load(f) or {}


@lru_cache(maxsize=1)
def load_agents_config() -> dict[str, Any]:
    """Load config/agents.yaml once and cache it."""
    path = Path(get_settings().config_dir) / "agents.yaml"
    return _load_yaml(path)


def load_prompt(name: str) -> str:
    path = Path(get_settings().config_dir) / "prompts" / name
    if not path.exists():
        raise FileNotFoundError(f"Prompt not found: {path}")
    return path.read_text()
