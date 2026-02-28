"""PostgreSQL database models and session management.

Uses SQLAlchemy 2.0 async engine with asyncpg driver.
"""
from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from autovid.config import get_settings

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass


# ─── ORM Models ──────────────────────────────────────────────────────

class ProjectRow(Base):
    __tablename__ = "projects"

    id = Column(String, primary_key=True)
    creator_id = Column(String, nullable=True)
    status = Column(String, default="active")
    style_prompt = Column(Text, default="")
    preferences = Column(JSON, default=dict)
    video_sequence = Column(JSON, default=list)  # ordered list of video_ids
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class VideoRow(Base):
    __tablename__ = "videos"

    id = Column(String, primary_key=True)
    project_id = Column(String, index=True)
    uri = Column(String)
    original_filename = Column(String)
    duration_ms = Column(Integer, default=0)
    width = Column(Integer, default=0)
    height = Column(Integer, default=0)
    fps = Column(Float, default=30.0)
    sequence_index = Column(Integer, default=0)
    ingestion_status = Column(String, default="pending")


class ChunkRow(Base):
    __tablename__ = "chunks"

    id = Column(String, primary_key=True)
    video_id = Column(String, index=True)
    project_id = Column(String, index=True)
    chunk_index = Column(Integer)
    start_ms = Column(Integer)
    end_ms = Column(Integer)
    video_uri = Column(String)
    audio_uri = Column(String)
    transcript = Column(JSON, nullable=True)
    vlm_analysis = Column(JSON, nullable=True)
    audio_features = Column(JSON, nullable=True)
    status = Column(String, default="pending")


class JobRow(Base):
    __tablename__ = "jobs"

    id = Column(String, primary_key=True)
    project_id = Column(String, index=True)
    status = Column(String, default="queued")
    current_phase = Column(String, nullable=True)
    current_step = Column(String, nullable=True)
    react_iteration = Column(Integer, default=0)
    progress = Column(Float, default=0.0)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    error = Column(Text, nullable=True)


class ClipRow(Base):
    __tablename__ = "clips"

    id = Column(String, primary_key=True)
    project_id = Column(String, index=True)
    job_id = Column(String, index=True)
    clip_spec = Column(JSON, default=dict)
    rendered_uri = Column(String, nullable=True)
    thumbnail_uri = Column(String, nullable=True)
    status = Column(String, default="pending")
    platform = Column(String, nullable=True)


class SocialAccountRow(Base):
    __tablename__ = "social_accounts"

    id = Column(String, primary_key=True)
    creator_id = Column(String, index=True)
    platform = Column(String)
    access_token = Column(String)  # TODO: encrypt at rest
    refresh_token = Column(String, nullable=True)
    expires_at = Column(DateTime, nullable=True)


class PublishRecordRow(Base):
    __tablename__ = "publish_records"

    id = Column(String, primary_key=True)
    clip_id = Column(String, index=True)
    social_account_id = Column(String)
    platform = Column(String)
    status = Column(String, default="pending")
    share_url = Column(String, nullable=True)
    published_at = Column(DateTime, nullable=True)


# ─── Session Factory ─────────────────────────────────────────────────

_engine = None
_session_factory = None


def get_engine():
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(settings.database_url, echo=False)
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    return _session_factory


async def init_db() -> None:
    """Create all tables (for development)."""
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created")
