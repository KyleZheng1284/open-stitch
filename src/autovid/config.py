"""YAML configuration loader.

Loads and validates config files from the config/ directory.
All model, agent, media, and prompt configurations are managed here.
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Environment-based settings loaded from .env or environment variables."""

    database_url: str = "postgresql+asyncpg://autovid:autovid_dev@localhost:5432/autovid"
    redis_url: str = "redis://localhost:6379/0"
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_secure: bool = False
    sandbox_image: str = "autovid-sandbox:latest"
    sandbox_network: str = "none"
    sandbox_cpu_limit: str = "4"
    sandbox_memory_limit: str = "8g"
    sandbox_timeout_s: int = 600
    otel_exporter_otlp_endpoint: str = "http://localhost:6006/v1/traces"
    config_dir: str = "config"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


class ModelConfig(BaseModel):
    """Parsed model configuration from config/models.yaml."""

    asr: dict[str, Any] = Field(default_factory=dict)
    vlm: dict[str, Any] = Field(default_factory=dict)
    vlm_cloud: dict[str, Any] = Field(default_factory=dict)
    llm: dict[str, Any] = Field(default_factory=dict)


class AgentConfig(BaseModel):
    """Parsed agent configuration from config/agents.yaml."""

    general: dict[str, Any] = Field(default_factory=dict)
    react_loop: dict[str, Any] = Field(default_factory=dict)
    subtitle: dict[str, Any] = Field(default_factory=dict)
    music: dict[str, Any] = Field(default_factory=dict)
    meme_sfx: dict[str, Any] = Field(default_factory=dict)
    assembly: dict[str, Any] = Field(default_factory=dict)
    publishing: dict[str, Any] = Field(default_factory=dict)
    ingestion: dict[str, Any] = Field(default_factory=dict)


def _load_yaml(filepath: str | Path) -> dict[str, Any]:
    """Load and parse a YAML file."""
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    with open(path) as f:
        data = yaml.safe_load(f)
    return data or {}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()


@lru_cache(maxsize=1)
def get_model_config() -> ModelConfig:
    """Load model configuration from config/models.yaml."""
    config_dir = Path(get_settings().config_dir)
    raw = _load_yaml(config_dir / "models.yaml")
    models = raw.get("models", raw)
    return ModelConfig(**models)


@lru_cache(maxsize=1)
def get_agent_config() -> AgentConfig:
    """Load agent configuration from config/agents.yaml."""
    config_dir = Path(get_settings().config_dir)
    raw = _load_yaml(config_dir / "agents.yaml")
    return AgentConfig(**raw)


def load_vlm_prompt() -> str:
    """Load the VLM edit-grade system prompt."""
    config_dir = Path(get_settings().config_dir)
    prompt_path = config_dir / "prompts" / "vlm_edit_grade.txt"
    if not prompt_path.exists():
        raise FileNotFoundError(f"VLM prompt not found: {prompt_path}")
    return prompt_path.read_text()


def load_subtitle_styles() -> dict[str, Any]:
    """Load subtitle style presets from config/subtitle_styles.yaml."""
    config_dir = Path(get_settings().config_dir)
    return _load_yaml(config_dir / "subtitle_styles.yaml")


def load_media_profiles() -> dict[str, Any]:
    """Load media output profiles from config/media_profiles.yaml."""
    config_dir = Path(get_settings().config_dir)
    return _load_yaml(config_dir / "media_profiles.yaml")
