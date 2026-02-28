"""Auto-Vid Pydantic schemas and dataclasses."""
from .transcript import WordSegment, Transcript
from .vlm import (
    FrameAnalysis, BoundingBox, SubjectPosition,
    SceneComposition, SecondAnalysis, ChunkVLMAnalysis,
)
from .chunk import ChunkMetadata, AudioFeatures
from .project import ProjectRequest, EditPreferences, Platform, SubtitleStyle, ProjectResult
from .clip_spec import (
    ClipSpec, EditSegment, ZoomSpec, HookSpec, OutroSpec,
    TransitionSpec, MemePoint, SubtitleConfig, OverlaySpec,
    CropSpec, Keyframe,
)
from .music import MusicTrack, DuckPoint
from .meme import MemeLayer, MemeInsert, SFXInsert
from .composition import (
    RemotionComposition, RemotionSequence, RemotionOverlay,
    RemotionSubtitle, RemotionAudio,
)
from .timeline import TimelineJSON, TimelineLayer, TimelineOutput

__all__ = [
    # Transcript
    "WordSegment", "Transcript",
    # VLM
    "FrameAnalysis", "BoundingBox", "SubjectPosition", "SceneComposition",
    "SecondAnalysis", "ChunkVLMAnalysis",
    # Chunk
    "ChunkMetadata", "AudioFeatures",
    # Project
    "ProjectRequest", "EditPreferences", "Platform", "SubtitleStyle", "ProjectResult",
    # Clip
    "ClipSpec", "EditSegment", "ZoomSpec", "HookSpec", "OutroSpec",
    "TransitionSpec", "MemePoint", "SubtitleConfig", "OverlaySpec",
    "CropSpec", "Keyframe",
    # Music
    "MusicTrack", "DuckPoint",
    # Meme
    "MemeLayer", "MemeInsert", "SFXInsert",
    # Composition
    "RemotionComposition", "RemotionSequence", "RemotionOverlay",
    "RemotionSubtitle", "RemotionAudio",
    # Timeline
    "TimelineJSON", "TimelineLayer", "TimelineOutput",
]
