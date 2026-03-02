"""Helpers shared by phase-2 graph node implementations."""
from __future__ import annotations

import json
from typing import Any


def parse_json_content(raw: str) -> dict[str, Any]:
    """Parse plain JSON or fenced JSON from model output."""
    clean = raw.strip()
    if clean.startswith("```"):
        clean = clean.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    parsed = json.loads(clean)
    if not isinstance(parsed, dict):
        raise ValueError("Expected JSON object")
    return parsed


def summaries_to_text(summaries: list[dict[str, Any]]) -> str:
    """Render summaries into compact prompt text."""
    return "\n\n".join(
        f"Video {idx + 1} ({s.get('filename', 'unknown')}, {float(s.get('duration_s', 0)):.0f}s):\n"
        f"{s.get('summary', 'No summary')}"
        for idx, s in enumerate(summaries)
    )
