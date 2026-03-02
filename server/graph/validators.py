"""Validation helpers for synthesis and QA graph nodes."""
from __future__ import annotations

from typing import Literal

from server.graph.artifacts import CompositionDraft, EditSpec, VerificationIssue, VerificationReport
from server.graph.base import EDITING_SYNTHESIS_AGENT, REMOTION_SYNTHESIS_AGENT, SYNTHESIS_AGENT


def verify_edit_spec(edit_spec: EditSpec | None) -> list[VerificationIssue]:
    """Validate structured edit spec."""
    issues: list[VerificationIssue] = []
    if edit_spec is None:
        issues.append(_issue("error", "edit_spec.missing", "Edit spec is missing."))
        return issues
    if not edit_spec.clips:
        issues.append(_issue("error", "edit_spec.empty", "Edit spec contains no clips."))
        return issues

    for idx, clip in enumerate(edit_spec.clips):
        if clip.end_s <= clip.start_s:
            issues.append(
                _issue(
                    "error",
                    "edit_spec.clip_range",
                    f"Clip {idx} has invalid range: {clip.start_s}-{clip.end_s}.",
                    field=f"clips[{idx}]",
                )
            )
        if clip.start_s < 0:
            issues.append(
                _issue(
                    "error",
                    "edit_spec.clip_start",
                    f"Clip {idx} start must be >= 0.",
                    field=f"clips[{idx}].start_s",
                )
            )
    return issues


def verify_composition_draft(draft: CompositionDraft | None) -> list[VerificationIssue]:
    """Validate remotion timeline and composition payload."""
    issues: list[VerificationIssue] = []
    if draft is None:
        issues.append(_issue("error", "composition.missing", "Composition draft is missing."))
        return issues

    layers = draft.timeline.get("layers", [])
    if not isinstance(layers, list) or not layers:
        issues.append(_issue("error", "timeline.empty", "Timeline layers are empty."))

    sequences = draft.composition.get("sequences", [])
    image_slides = draft.composition.get("image_slides", [])
    if (not sequences or not isinstance(sequences, list)) and (not image_slides or not isinstance(image_slides, list)):
        issues.append(_issue("error", "composition.empty", "Composition has no sequences or image slides."))

    return issues


def build_report(issues: list[VerificationIssue]) -> VerificationReport:
    """Convert issue list into pass/fail report."""
    passed = not any(issue.severity == "error" for issue in issues)
    return VerificationReport(passed=passed, issues=issues)


def retry_target_from_report(report: VerificationReport) -> str:
    """Pick the synthesis stage to retry from failed validation issues."""
    for issue in report.issues:
        if issue.code.startswith("edit_spec."):
            return SYNTHESIS_AGENT
        if issue.code.startswith("timeline."):
            return REMOTION_SYNTHESIS_AGENT
        if issue.code.startswith("composition."):
            return EDITING_SYNTHESIS_AGENT
    return EDITING_SYNTHESIS_AGENT


def _issue(
    severity: Literal["info", "warning", "error"],
    code: str,
    message: str,
    *,
    field: str | None = None,
) -> VerificationIssue:
    return VerificationIssue(severity=severity, code=code, message=message, field=field)
