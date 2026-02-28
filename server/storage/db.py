"""PostgreSQL models and session management."""
from __future__ import annotations

import logging
from sqlalchemy import JSON, Column, DateTime, Float, Integer, String, Text, func
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from server.config import get_settings

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass


class ProjectRow(Base):
    __tablename__ = "projects"
    id = Column(String, primary_key=True)
    creator_id = Column(String, nullable=True)
    status = Column(String, default="active")
    video_sequence = Column(JSON, default=list)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class VideoRow(Base):
    __tablename__ = "videos"
    id = Column(String, primary_key=True)
    project_id = Column(String, index=True)
    drive_file_id = Column(String, nullable=True)
    local_path = Column(String, nullable=True)
    filename = Column(String, default="")
    duration_ms = Column(Integer, default=0)
    width = Column(Integer, default=0)
    height = Column(Integer, default=0)
    fps = Column(Float, default=30.0)
    summary = Column(Text, default="")
    ingestion_status = Column(String, default="pending")
    sequence_index = Column(Integer, default=0)


class JobRow(Base):
    __tablename__ = "jobs"
    id = Column(String, primary_key=True)
    project_id = Column(String, index=True)
    status = Column(String, default="queued")
    phase = Column(String, default="")
    progress = Column(Float, default=0.0)
    error = Column(Text, nullable=True)
    output_uri = Column(String, nullable=True)
    ingestion_data = Column(JSON, nullable=True)
    structured_prompt = Column(Text, nullable=True)
    edit_plan = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=func.now())


_engine = None
_session_factory = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = create_async_engine(get_settings().database_url, echo=False)
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    return _session_factory


async def init_db():
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created")
