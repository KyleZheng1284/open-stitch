"""Pydantic models for sandbox tool inputs/outputs."""
from __future__ import annotations

from pydantic import BaseModel, Field


class FileInfo(BaseModel):
    """File metadata from sandbox filesystem."""

    name: str
    type: str = Field(description="'file' or 'directory'")
    size: int | None = None
    modified: str | None = None


class ExecResult(BaseModel):
    """Result of a sandbox command execution."""

    exit_code: int
    stdout: str = ""
    stderr: str = ""


class RenderResult(BaseModel):
    """Result of a Remotion render."""

    exit_code: int
    output_path: str = ""
    output_size: int = 0


class AssetInfo(BaseModel):
    """Metadata for an asset in the sandbox."""

    name: str
    path: str
    full_path: str = ""
    size: int = 0
    ext: str = ""
