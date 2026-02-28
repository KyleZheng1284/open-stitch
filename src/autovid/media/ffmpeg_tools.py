"""FFmpeg command builders for media processing.

All FFmpeg commands run inside the Docker sandbox. These builders generate
the command strings that sandbox_run_ffmpeg() executes.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def build_normalize_cmd(
    input_path: str,
    output_path: str,
    width: int = 1080,
    height: int = 1920,
    crf: int = 23,
) -> list[str]:
    """Build FFmpeg command for video normalization to target profile."""
    return [
        "-i", input_path,
        "-vf", f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2",
        "-c:v", "libx264", "-preset", "fast", "-crf", str(crf),
        "-c:a", "aac", "-ar", "44100",
        "-y", output_path,
    ]


def build_extract_audio_cmd(
    input_path: str,
    output_path: str,
    sample_rate: int = 16000,
) -> list[str]:
    """Build FFmpeg command to extract audio for ASR."""
    return [
        "-i", input_path,
        "-vn", "-acodec", "pcm_s16le",
        "-ar", str(sample_rate), "-ac", "1",
        "-y", output_path,
    ]


def build_scene_detect_cmd(
    input_path: str,
    output_pattern: str,
    threshold: float = 0.3,
) -> list[str]:
    """Build FFmpeg command for scene-change detection and chunking."""
    return [
        "-i", input_path,
        "-filter_complex", f"select='gt(scene,{threshold})',metadata=print",
        "-vsync", "vfr",
        "-y", output_pattern,
    ]


def build_audio_mix_cmd(
    video_path: str,
    music_path: str,
    output_path: str,
    music_volume: float = 0.15,
    sfx_inputs: list[dict[str, Any]] | None = None,
) -> list[str]:
    """Build FFmpeg command for audio mixing (music ducking + SFX layering).

    This is the post-Remotion audio processing step. Remotion renders
    visual layers; FFmpeg handles all audio mixing.
    """
    args = ["-i", video_path, "-i", music_path]
    filter_parts = [f"[1:a]volume={music_volume}[bg]"]

    # Add SFX inputs
    sfx_list = sfx_inputs or []
    for idx, sfx in enumerate(sfx_list):
        input_idx = idx + 2
        args.extend(["-i", sfx["path"]])
        delay_ms = sfx.get("at_ms", 0)
        volume = sfx.get("volume", 0.8)
        filter_parts.append(
            f"[{input_idx}:a]adelay={delay_ms}|{delay_ms},volume={volume}[sfx{idx}]"
        )

    # Mix all audio streams
    mix_inputs = "[0:a][bg]"
    for idx in range(len(sfx_list)):
        mix_inputs += f"[sfx{idx}]"
    total_inputs = 2 + len(sfx_list)
    filter_parts.append(
        f"{mix_inputs}amix=inputs={total_inputs}:duration=first[out]"
    )

    filter_complex = ";".join(filter_parts)
    args.extend([
        "-filter_complex", filter_complex,
        "-map", "0:v", "-map", "[out]",
        "-c:v", "copy", "-c:a", "aac",
        "-y", output_path,
    ])
    return args


def build_burn_subtitles_cmd(
    input_path: str,
    subtitle_path: str,
    output_path: str,
) -> list[str]:
    """Build FFmpeg command to burn ASS subtitles into video."""
    return [
        "-i", input_path,
        "-vf", f"ass={subtitle_path}",
        "-c:v", "libx264", "-c:a", "copy",
        "-y", output_path,
    ]


def build_sample_frames_cmd(
    input_path: str,
    output_pattern: str,
    fps: int = 1,
) -> list[str]:
    """Build FFmpeg command to extract frames at specified FPS."""
    return [
        "-i", input_path,
        "-vf", f"fps={fps}",
        "-q:v", "2",
        "-y", output_pattern,
    ]
