"""Remotion composition tool wrappers.

These are the Remotion-first action vocabulary tools that agents call to
incrementally build the RemotionComposition. Each function maps to a
specific Remotion primitive and is registered as a LangGraph tool.
"""
from __future__ import annotations

import logging
from typing import Any

from autovid.schemas.clip_spec import Keyframe
from autovid.schemas.composition import (
    RemotionAudio,
    RemotionComposition,
    RemotionOverlay,
    RemotionSequence,
    RemotionSubtitle,
)

logger = logging.getLogger(__name__)


def remotion_add_sequence(
    composition: RemotionComposition,
    chunk_uri: str,
    start_ms: int,
    end_ms: int,
    speed: float = 1.0,
    crop: dict[str, float] | None = None,
    position_in_timeline_ms: int = 0,
    transition_in: dict[str, Any] | None = None,
) -> str:
    """Add a video segment to the base layer (z=0).

    Maps to Remotion <Sequence> + <OffthreadVideo>.
    Returns the sequence ID.
    """
    seq = RemotionSequence(
        chunk_uri=chunk_uri,
        start_ms=start_ms,
        end_ms=end_ms,
        speed=speed,
        crop=crop,
        position_in_timeline_ms=position_in_timeline_ms,
        transition_in=transition_in,
    )
    composition.add_sequence(seq)
    logger.info(
        "Added sequence: %s [%d-%d ms] at timeline %d ms",
        chunk_uri, start_ms, end_ms, position_in_timeline_ms,
    )
    return seq.id


def remotion_add_overlay(
    composition: RemotionComposition,
    asset_uri: str,
    at_ms: int,
    duration_ms: int,
    x: float,
    y: float,
    scale: float = 1.0,
    rotation: float = 0.0,
    opacity: float = 1.0,
    z_index: int = 10,
    animation: str = "none",
    keyframes: list[dict[str, Any]] | None = None,
    paired_sfx: str | None = None,
) -> str:
    """Add a meme/emoji/GIF overlay with coordinates and animation.

    Maps to Remotion <Img> with absolute positioning + spring()/interpolate().
    Returns the overlay ID.
    """
    kf_models = [Keyframe(**kf) for kf in (keyframes or [])]
    overlay = RemotionOverlay(
        asset_uri=asset_uri,
        at_ms=at_ms,
        duration_ms=duration_ms,
        x=x,
        y=y,
        scale=scale,
        rotation=rotation,
        opacity=opacity,
        z_index=z_index,
        animation=animation,
        keyframes=kf_models,
        paired_sfx=paired_sfx,
    )
    composition.add_overlay(overlay)
    logger.info("Added overlay: %s at %d ms, pos=(%.2f, %.2f)", asset_uri, at_ms, x, y)

    # If paired SFX, also add an audio layer
    if paired_sfx:
        remotion_add_audio(composition, paired_sfx, start_ms=at_ms, volume=0.8)

    return overlay.id


def remotion_add_subtitle(
    composition: RemotionComposition,
    text: str,
    start_ms: int,
    end_ms: int,
    style_preset: str = "tiktok_pop",
    position: str = "center_bottom",
    keyframes: list[dict[str, Any]] | None = None,
    word_timings: list[dict[str, Any]] | None = None,
) -> str:
    """Add a kinetic subtitle layer.

    Maps to Remotion <KineticSubtitle> with per-word animation.
    Returns the subtitle ID.
    """
    kf_models = [Keyframe(**kf) for kf in (keyframes or [])]
    sub = RemotionSubtitle(
        text=text,
        start_ms=start_ms,
        end_ms=end_ms,
        style_preset=style_preset,
        position=position,
        keyframes=kf_models,
        word_timings=word_timings or [],
    )
    composition.add_subtitle(sub)
    logger.info("Added subtitle: '%s' [%d-%d ms]", text[:50], start_ms, end_ms)
    return sub.id


def remotion_add_audio(
    composition: RemotionComposition,
    audio_uri: str,
    start_ms: int = 0,
    volume: float = 1.0,
    duck_points: list[dict[str, Any]] | None = None,
    pitch_shift: float = 0.0,
    fade_in_ms: int = 0,
    fade_out_ms: int = 0,
) -> str:
    """Add a background music or SFX audio layer.

    Maps to FFmpeg post-processing inside the sandbox.
    Returns the audio layer ID.
    """
    audio = RemotionAudio(
        audio_uri=audio_uri,
        start_ms=start_ms,
        volume=volume,
        duck_points=duck_points or [],
        pitch_shift=pitch_shift,
        fade_in_ms=fade_in_ms,
        fade_out_ms=fade_out_ms,
    )
    composition.add_audio(audio)
    logger.info("Added audio: %s at %d ms, vol=%.2f", audio_uri, start_ms, volume)
    return audio.id


def remotion_remove_layer(
    composition: RemotionComposition, layer_id: str
) -> bool:
    """Remove a layer by ID. Returns True if found and removed."""
    removed = composition.remove_layer(layer_id)
    if removed:
        logger.info("Removed layer: %s", layer_id)
    else:
        logger.warning("Layer not found: %s", layer_id)
    return removed
