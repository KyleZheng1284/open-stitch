"""Project lifecycle endpoints — file upload + ingestion + editing."""
from __future__ import annotations

import logging
import shutil
import time
import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile

from server.schemas.project import ClarifyAnswer, EditRequest, ProjectStatus, VideoInfo

logger = logging.getLogger(__name__)
router = APIRouter()

# In-memory store for MVP
_projects: dict[str, dict] = {}


@router.post("/upload", response_model=ProjectStatus)
async def upload_and_create(
    files: list[UploadFile] = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
):
    """Upload mp4/mov files, create project, start ingestion."""
    project_id = f"proj_{uuid.uuid4().hex[:12]}"
    upload_dir = Path("data/uploads") / project_id
    upload_dir.mkdir(parents=True, exist_ok=True)

    videos: list[VideoInfo] = []
    for f in files:
        if not f.filename:
            continue
        ext = Path(f.filename).suffix.lower()
        if ext not in (".mp4", ".mov"):
            continue

        vid_id = f"vid_{uuid.uuid4().hex[:8]}"
        dest = upload_dir / f.filename
        with open(dest, "wb") as out:
            shutil.copyfileobj(f.file, out)

        size_mb = dest.stat().st_size / 1e6
        logger.info("📁 Uploaded %s → %s (%.1f MB)", f.filename, dest, size_mb)
        videos.append(VideoInfo(
            id=vid_id,
            filename=f.filename,
            local_path=str(dest),
            ingestion_status="pending",
        ))

    if not videos:
        raise HTTPException(status_code=400, detail="No valid mp4/mov files uploaded")

    project = {
        "id": project_id,
        "status": "ingesting",
        "videos": videos,
        "ingestion_data": {},
        "structured_prompt": None,
        "output_uri": None,
        "error": None,
    }
    _projects[project_id] = project

    logger.info("🚀 Project %s created with %d video(s) — starting ingestion", project_id, len(videos))
    background_tasks.add_task(_run_ingestion, project_id)

    return ProjectStatus(id=project_id, status="ingesting", videos=videos)


@router.get("/{project_id}", response_model=ProjectStatus)
async def get_project(project_id: str):
    project = _projects.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return ProjectStatus(
        id=project["id"],
        status=project["status"],
        videos=project["videos"],
        output_uri=project.get("output_uri"),
        error=project.get("error"),
    )


@router.get("/{project_id}/questions")
async def get_questions(project_id: str):
    """Generate clarifying questions from video summaries via LLM."""
    project = _projects.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project["status"] not in ("ready_for_clarify", "editing", "complete"):
        raise HTTPException(status_code=400, detail="Ingestion not complete yet")

    summaries = []
    for vid in project["videos"]:
        vid_id = vid.id if hasattr(vid, "id") else vid.get("id", "")
        data = project.get("ingestion_data", {}).get(vid_id, {})
        summaries.append({
            "filename": vid.filename if hasattr(vid, "filename") else vid.get("filename", ""),
            "duration_s": data.get("duration_s", 0),
            "summary": data.get("summary", ""),
        })

    logger.info("💬 Generating clarifying questions for %s (%d videos)", project_id, len(summaries))
    from server.agents.clarifying import generate_initial_questions
    result = await generate_initial_questions(summaries)
    logger.info("💬 Generated %d questions", len(result.get("questions", [])))
    return result


@router.post("/{project_id}/clarify")
async def clarify(project_id: str, body: ClarifyAnswer):
    """Submit answers to the clarifying agent, get next question or final prompt."""
    project = _projects.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    logger.info("📝 Clarify answers for %s: %s", project_id, list(body.answers.keys()))
    from server.agents.clarifying import process_answers
    result = await process_answers(project, body.answers)
    logger.info("📝 Structured prompt built (%d chars)", len(result.get("structured_prompt", "")))
    return result


@router.post("/{project_id}/edit")
async def start_edit(project_id: str, body: EditRequest, background_tasks: BackgroundTasks):
    """Submit structured prompt and start the editing agent."""
    project = _projects.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    project["structured_prompt"] = body.structured_prompt
    project["status"] = "editing"

    logger.info("🎬 Edit requested for %s — starting editing agent", project_id)
    background_tasks.add_task(_run_editing, project_id)
    return {"status": "editing", "project_id": project_id}


async def _run_ingestion(project_id: str):
    """Background: two-phase ingestion.

    Phase 1 (fast): Run Flash Lite summary on all videos (~10-20s each).
                    Sets status to 'ready_for_clarify' so the user can start
                    answering questions while deep analysis continues.

    Phase 2 (deep): Run ASR + dense VLM in parallel on all videos.
                    Updates ingestion_data in place. The editing agent will
                    use whatever data is available when it runs.
    """
    project = _projects.get(project_id)
    if not project:
        return

    from server.ingestion.pipeline import ingest_video_summary, ingest_video_deep

    total = len(project["videos"])

    # ── Phase 1: Fast summaries ──────────────────────────────────────
    try:
        logger.info("⚡ [%s] Phase 1: Fast summaries for %d video(s)", project_id, total)
        t0 = time.time()
        results = {}

        for idx, vid in enumerate(project["videos"], 1):
            local_path = vid.local_path if hasattr(vid, "local_path") else ""
            if not local_path:
                continue

            logger.info("⚡ [%s] Summarizing video %d/%d: %s", project_id, idx, total, vid.filename)
            vid.ingestion_status = "summarizing"

            partial = await ingest_video_summary(local_path)
            results[vid.id] = partial
            vid.summary = partial.get("summary", "")
            vid.duration_s = partial.get("duration_s", 0)
            vid.ingestion_status = "summarized"

        project["ingestion_data"] = results
        project["status"] = "ready_for_clarify"
        elapsed = time.time() - t0
        logger.info(
            "⚡ [%s] Phase 1 done in %.1fs — summaries ready, user can start clarifying",
            project_id, elapsed,
        )
    except Exception as e:
        logger.exception("❌ [%s] Summary phase failed: %s", project_id, e)
        project["status"] = "error"
        project["error"] = str(e)
        return

    # ── Phase 2: Deep analysis (ASR + VLM) — all videos in parallel ─
    import asyncio
    try:
        logger.info("🔬 [%s] Phase 2: Deep analysis (ASR + VLM) for %d video(s) in parallel", project_id, total)
        t0 = time.time()

        async def deep_one(vid, idx):
            if vid.id not in results:
                return
            logger.info("🔬 [%s] Deep analysis %d/%d: %s", project_id, idx, total, vid.filename)
            vid.ingestion_status = "analyzing"
            await ingest_video_deep(results[vid.id])
            vid.ingestion_status = "complete"
            logger.info(
                "✅ [%s] Video %d/%d deep done — ASR=%d words, VLM=%d entries",
                project_id, idx, total,
                len(results[vid.id].get("asr", {}).get("words", [])),
                len(results[vid.id].get("timeline", [])),
            )

        await asyncio.gather(*(
            deep_one(vid, idx) for idx, vid in enumerate(project["videos"], 1)
        ))

        elapsed = time.time() - t0
        logger.info("🏁 [%s] Phase 2 done in %.1fs — full ingestion complete", project_id, elapsed)
    except Exception as e:
        logger.exception("⚠️ [%s] Deep analysis failed (summaries still usable): %s", project_id, e)
        # Don't set error status — summaries are still valid for clarifying


async def _run_editing(project_id: str):
    """Background: run the editing agent."""
    project = _projects.get(project_id)
    if not project:
        return

    from server.agents.editing import run_editing_agent
    try:
        t0 = time.time()
        logger.info("🎬 [%s] Editing agent started", project_id)
        output_uri = await run_editing_agent(project)
        elapsed = time.time() - t0

        project["output_uri"] = output_uri
        project["status"] = "complete"
        logger.info("🎉 [%s] Editing complete in %.1fs — output: %s", project_id, elapsed, output_uri)
    except Exception as e:
        logger.exception("❌ [%s] Editing failed: %s", project_id, e)
        project["status"] = "error"
        project["error"] = str(e)
