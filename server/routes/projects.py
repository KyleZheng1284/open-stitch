"""Project lifecycle endpoints — file upload + ingestion + editing."""
from __future__ import annotations

import logging
import shutil
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

        logger.info("Uploaded %s → %s (%d bytes)", f.filename, dest, dest.stat().st_size)
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


@router.post("/{project_id}/clarify")
async def clarify(project_id: str, body: ClarifyAnswer):
    """Submit answers to the clarifying agent, get next question or final prompt."""
    project = _projects.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    from server.agents.clarifying import process_answers
    result = await process_answers(project, body.answers)
    return result


@router.post("/{project_id}/edit")
async def start_edit(project_id: str, body: EditRequest, background_tasks: BackgroundTasks):
    """Submit structured prompt and start the editing agent."""
    project = _projects.get(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    project["structured_prompt"] = body.structured_prompt
    project["status"] = "editing"

    background_tasks.add_task(_run_editing, project_id)
    return {"status": "editing", "project_id": project_id}


async def _run_ingestion(project_id: str):
    """Background: run ASR + VLM + summary on uploaded videos."""
    project = _projects.get(project_id)
    if not project:
        return

    from server.ingestion.pipeline import ingest_video
    try:
        results = {}
        for vid in project["videos"]:
            local_path = vid.local_path if hasattr(vid, "local_path") else ""
            if not local_path:
                continue
            logger.info("Ingesting %s", local_path)
            vid.ingestion_status = "processing"
            data = await ingest_video(local_path)
            results[vid.id] = data
            vid.summary = data.get("summary", "")
            vid.duration_s = data.get("duration_s", 0)
            vid.ingestion_status = "complete"

        project["ingestion_data"] = results
        project["status"] = "ready_for_clarify"
        logger.info("Ingestion complete for %s", project_id)
    except Exception as e:
        logger.exception("Ingestion failed for %s", project_id)
        project["status"] = "error"
        project["error"] = str(e)


async def _run_editing(project_id: str):
    """Background: run the editing agent."""
    project = _projects.get(project_id)
    if not project:
        return

    from server.agents.editing import run_editing_agent
    try:
        output_uri = await run_editing_agent(project)
        project["output_uri"] = output_uri
        project["status"] = "complete"
    except Exception as e:
        logger.exception("Editing failed for %s", project_id)
        project["status"] = "error"
        project["error"] = str(e)
