"""Project lifecycle endpoints — file upload + ingestion + editing."""
from __future__ import annotations

import asyncio
import logging
import shutil
import time
import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, Request, UploadFile
from pydantic import BaseModel

from server.config import get_settings
from server.schemas.project import ClarifyAnswer, EditRequest, ProjectStatus, VideoInfo

logger = logging.getLogger(__name__)
router = APIRouter()

# In-memory store for MVP
_projects: dict[str, dict] = {}


_VIDEO_EXTS = {".mp4", ".mov"}
_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
_ALLOWED_EXTS = _VIDEO_EXTS | _IMAGE_EXTS


@router.post("/upload", response_model=ProjectStatus)
async def upload_and_create(
    files: list[UploadFile] = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
):
    """Upload video/image files, create project, start ingestion."""
    project_id = f"proj_{uuid.uuid4().hex[:12]}"
    upload_dir = Path("data/uploads") / project_id
    upload_dir.mkdir(parents=True, exist_ok=True)

    videos: list[VideoInfo] = []
    for f in files:
        if not f.filename:
            continue
        ext = Path(f.filename).suffix.lower()
        if ext not in _ALLOWED_EXTS:
            continue

        media_type = "video" if ext in _VIDEO_EXTS else "image"
        vid_id = f"vid_{uuid.uuid4().hex[:8]}"
        dest = upload_dir / f.filename
        with open(dest, "wb") as out:
            shutil.copyfileobj(f.file, out)

        size_mb = dest.stat().st_size / 1e6
        logger.info("📁 Uploaded %s → %s (%.1f MB, %s)", f.filename, dest, size_mb, media_type)
        videos.append(VideoInfo(
            id=vid_id,
            filename=f.filename,
            local_path=str(dest),
            ingestion_status="pending",
            media_type=media_type,
        ))

    if not videos:
        raise HTTPException(status_code=400, detail="No valid video or image files uploaded")

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


class FromDriveRequest(BaseModel):
    file_ids: list[str]


@router.post("/from-drive", response_model=ProjectStatus)
async def create_from_drive(
    body: FromDriveRequest,
    background_tasks: BackgroundTasks = BackgroundTasks(),
):
    """Create a project from files already downloaded from Google Drive."""
    project_id = f"proj_{uuid.uuid4().hex[:12]}"
    downloads_dir = Path("data/downloads")

    videos: list[VideoInfo] = []
    for file_id in body.file_ids:
        # Drive download writes files as <file_id>.mp4 or <file_id>.mov
        local_path: Path | None = None
        for ext in (".mp4", ".mov"):
            candidate = downloads_dir / f"{file_id}{ext}"
            if candidate.exists():
                local_path = candidate
                break

        if local_path is None:
            raise HTTPException(
                status_code=404,
                detail=f"Downloaded file not found for Drive ID: {file_id}",
            )

        vid_id = f"vid_{uuid.uuid4().hex[:8]}"
        videos.append(VideoInfo(
            id=vid_id,
            filename=local_path.name,
            local_path=str(local_path),
            ingestion_status="pending",
        ))

    if not videos:
        raise HTTPException(status_code=400, detail="No valid downloaded files found")

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

    logger.info("🚀 Project %s created from Drive (%d videos) — starting ingestion", project_id, len(videos))
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
async def get_questions(project_id: str, request: Request):
    """Generate clarifying questions from video summaries via LLM."""
    project = _projects.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project["status"] not in ("ready_for_clarify", "editing", "complete"):
        raise HTTPException(status_code=400, detail="Ingestion not complete yet")

    from server.agents.clarifying import extract_video_summaries

    summaries = extract_video_summaries(project)

    request_id = request.headers.get("x-request-id", f"req_{uuid.uuid4().hex[:12]}")

    if get_settings().graph_enabled:
        try:
            logger.info("💬 [graph] Generating clarifying questions for %s", project_id)
            from server.graph import run_clarification_questions_graph

            result = await run_clarification_questions_graph(project, request_id=request_id)
            logger.info("💬 [graph] Generated %d questions", len(result.get("questions", [])))
            return result
        except Exception as exc:
            logger.exception("💬 [graph] Clarifying graph failed, falling back: %s", exc)

    logger.info("💬 Generating clarifying questions for %s (%d videos)", project_id, len(summaries))
    from server.agents.clarifying import generate_initial_questions
    result = await generate_initial_questions(
        summaries,
        project_id=project_id,
        request_id=request_id,
    )
    logger.info("💬 Generated %d questions", len(result.get("questions", [])))
    return result


@router.post("/{project_id}/clarify")
async def clarify(project_id: str, body: ClarifyAnswer, request: Request):
    """Submit answers to the clarifying agent, get next question or final prompt."""
    project = _projects.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    logger.info("📝 Clarify answers for %s: %s", project_id, list(body.answers.keys()))
    request_id = request.headers.get("x-request-id", f"req_{uuid.uuid4().hex[:12]}")

    if get_settings().graph_enabled:
        try:
            logger.info("📝 [graph] Verifying clarify answers for %s", project_id)
            from server.graph import run_user_verification_graph

            result = await run_user_verification_graph(
                project,
                answers=body.answers,
                request_id=request_id,
            )
            logger.info("📝 [graph] Structured prompt built (%d chars)", len(result.get("structured_prompt", "")))
            return result
        except Exception as exc:
            logger.exception("📝 [graph] User verification graph failed, falling back: %s", exc)

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

    from server.events import emit
    from server.ingestion.pipeline import ingest_video_summary, ingest_video_deep, ingest_image_summary

    total = len(project["videos"])

    emit(project_id, "ingestion.start", node_id="ingestion", parent_id="pipeline")

    # ── Phase 1: Fast summaries ──────────────────────────────────────
    #   Videos run sequentially (heavy ffmpeg + VLM).
    #   Images run in parallel batches of 5 (lightweight VLM-only).
    _IMAGE_BATCH_SIZE = 5

    try:
        logger.info("[%s] Phase 1: Fast summaries for %d file(s)", project_id, total)
        t0 = time.time()
        results = {}

        images = [(vid, idx) for idx, vid in enumerate(project["videos"], 1)
                  if getattr(vid, "media_type", "video") == "image"
                  and (vid.local_path if hasattr(vid, "local_path") else "")]
        videos = [(vid, idx) for idx, vid in enumerate(project["videos"], 1)
                  if getattr(vid, "media_type", "video") == "video"
                  and (vid.local_path if hasattr(vid, "local_path") else "")]

        async def _summarize_one_image(vid, idx):
            local_path = vid.local_path if hasattr(vid, "local_path") else ""
            logger.info("[%s] Summarizing image %d/%d: %s", project_id, idx, total, vid.filename)
            vid.ingestion_status = "summarizing"
            emit(project_id, "summary.start",
                 node_id=f"summary:{vid.id}", parent_id="ingestion",
                 videoId=vid.id, filename=vid.filename)
            partial = await ingest_image_summary(local_path)
            results[vid.id] = partial
            vid.summary = partial.get("summary", "")
            vid.ingestion_status = "summarized"
            emit(project_id, "summary.end",
                 node_id=f"summary:{vid.id}",
                 videoId=vid.id, durationS=0)

        if images:
            logger.info("[%s] Batch-summarizing %d image(s) (%d concurrent)", project_id, len(images), _IMAGE_BATCH_SIZE)
            for batch_start in range(0, len(images), _IMAGE_BATCH_SIZE):
                batch = images[batch_start:batch_start + _IMAGE_BATCH_SIZE]
                await asyncio.gather(*(_summarize_one_image(vid, idx) for vid, idx in batch))

        for vid, idx in videos:
            local_path = vid.local_path if hasattr(vid, "local_path") else ""
            logger.info("[%s] Summarizing video %d/%d: %s", project_id, idx, total, vid.filename)
            vid.ingestion_status = "summarizing"
            emit(project_id, "summary.start",
                 node_id=f"summary:{vid.id}", parent_id="ingestion",
                 videoId=vid.id, filename=vid.filename)
            partial = await ingest_video_summary(local_path)
            results[vid.id] = partial
            vid.summary = partial.get("summary", "")
            vid.duration_s = partial.get("duration_s", 0)
            vid.ingestion_status = "summarized"
            emit(project_id, "summary.end",
                 node_id=f"summary:{vid.id}",
                 videoId=vid.id, durationS=partial.get("duration_s", 0))

        project["ingestion_data"] = results
        project["status"] = "ready_for_clarify"
        elapsed = time.time() - t0
        logger.info(
            "[%s] Phase 1 done in %.1fs -- summaries ready, user can start clarifying",
            project_id, elapsed,
        )
    except Exception as e:
        logger.exception("[%s] Summary phase failed: %s", project_id, e)
        project["status"] = "error"
        project["error"] = str(e)
        return

    for vid in project["videos"]:
        if getattr(vid, "media_type", "video") == "image":
            vid.ingestion_status = "complete"

    # Yield to the event loop so pending HTTP requests (e.g. the frontend
    # polling for status) get served before Phase 2 starts.
    await asyncio.sleep(0)

    # ── Phase 2: Deep analysis (ASR + VLM) -- videos only, skip images ─
    video_items = [
        (vid, idx) for idx, vid in enumerate(project["videos"], 1)
        if getattr(vid, "media_type", "video") == "video" and vid.id in results
    ]
    if video_items:
        try:
            logger.info("[%s] Phase 2: Deep analysis (ASR + VLM) for %d video(s) in parallel", project_id, len(video_items))
            t0 = time.time()

            async def deep_one(vid, idx):
                logger.info("[%s] Deep analysis %d/%d: %s", project_id, idx, total, vid.filename)
                vid.ingestion_status = "analyzing"

                emit(project_id, "asr.start",
                     node_id=f"asr:{vid.id}", parent_id="ingestion",
                     videoId=vid.id, filename=vid.filename)
                emit(project_id, "vlm.start",
                     node_id=f"vlm:{vid.id}", parent_id="ingestion",
                     videoId=vid.id, filename=vid.filename)

                await ingest_video_deep(results[vid.id])
                vid.ingestion_status = "complete"

                emit(project_id, "asr.end",
                     node_id=f"asr:{vid.id}", videoId=vid.id)
                emit(project_id, "vlm.end",
                     node_id=f"vlm:{vid.id}", videoId=vid.id)

                logger.info(
                    "[%s] Video %d/%d deep done -- ASR=%d words, VLM=%d entries",
                    project_id, idx, total,
                    len(results[vid.id].get("asr", {}).get("words", [])),
                    len(results[vid.id].get("timeline", [])),
                )

            await asyncio.gather(*(deep_one(vid, idx) for vid, idx in video_items))

            elapsed = time.time() - t0
            logger.info("[%s] Phase 2 done in %.1fs -- full ingestion complete", project_id, elapsed)
        except Exception as e:
            logger.exception("[%s] Deep analysis failed (summaries still usable): %s", project_id, e)
    else:
        logger.info("[%s] No videos to deep-analyze (images only)", project_id)

    emit(project_id, "ingestion.end", node_id="ingestion")


async def _run_editing(project_id: str):
    """Background: run the editing agent."""
    project = _projects.get(project_id)
    if not project:
        return

    from server.config import get_settings
    from server.events import emit
    from server.agents.editing import run_editing_agent

    emit(project_id, "pipeline.start", node_id="pipeline")

    emit(project_id, "ingestion.complete", node_id="ingestion", parent_id="pipeline",
         videos=[{"id": v.id, "filename": v.filename} for v in project["videos"]])

    try:
        t0 = time.time()
        logger.info("[%s] Editing agent started", project_id)

        output_uri: str
        if get_settings().graph_enabled:
            try:
                from server.graph import run_editing_pipeline_graph

                logger.info("[%s] Running graph editing pipeline", project_id)
                graph_result = await run_editing_pipeline_graph(project)
                output_uri = str(graph_result["output_uri"])
            except Exception as exc:
                logger.exception("[%s] Graph editing failed: %s", project_id, exc)
                if not get_settings().graph_fail_open:
                    raise
                logger.info("[%s] Falling back to legacy editing agent", project_id)
                output_uri = await run_editing_agent(project)
        else:
            output_uri = await run_editing_agent(project)

        elapsed = time.time() - t0

        project["output_uri"] = output_uri
        project["status"] = "complete"
        logger.info("[%s] Editing complete in %.1fs -- output: %s", project_id, elapsed, output_uri)
        emit(project_id, "pipeline.end", node_id="pipeline", status="complete")
    except Exception as e:
        logger.exception("[%s] Editing failed: %s", project_id, e)
        project["status"] = "error"
        project["error"] = str(e)
        emit(project_id, "pipeline.end", node_id="pipeline", status="error", error=str(e))
