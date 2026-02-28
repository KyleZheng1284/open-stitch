# Open-Stitch (Auto-Vid)

**An open, model-pluggable AI agent system that ingests raw footage and autonomously produces edited short-form videos with subtitles, transitions, memes, background music, and sound effects — then publishes them to social platforms.**

Built with LangGraph, Remotion, FastAPI, React Flow, and Qwen3.5-397B-A17B.

---

## Architecture Overview

The system runs in **two overlapping phases**:

```
Phase 1: Async Ingestion (starts on upload)
  Upload → Chunking → ASR + Audio Analysis → Dense VLM Analysis → ChunkStore

Phase 2: Agentic Editing (starts on style prompt)
  ReAct Loop → Subtitle/Music/Meme Agents (parallel) → Assembly → Publish
```

**Key design principles:**
- **Remotion-first action vocabulary** — Agents emit Remotion operations directly (`remotion_add_sequence`, `remotion_add_overlay`), building a composition incrementally
- **Dense per-second VLM analysis** — Qwen3.5-397B-A17B produces edit signals, bounding boxes, and energy scores per second of video
- **Docker sandbox per job** — Isolated container with Remotion + FFmpeg, no network access
- **Model pluggability** — Swap ASR/VLM/LLM by editing `config/models.yaml`, no code changes

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11+, FastAPI, LangGraph, SQLAlchemy, Arq |
| Frontend | Next.js 15, React Flow (@xyflow/react), @dnd-kit, Tailwind CSS |
| Rendering | Remotion (visual) + FFmpeg (audio), Docker sandbox |
| Models | Qwen3.5-397B-A17B (VLM), Whisper v3 (ASR), Llama 3.3 (LLM) |
| Storage | PostgreSQL, Redis, MinIO (S3-compatible) |
| Observability | OpenTelemetry → Phoenix |

---

## Project Structure

### Root Files

| File | Purpose |
|------|---------|
| `SPEC.md` | Full specification document (architecture, schemas, API, UI) |
| `pyproject.toml` | Python package config with all dependencies |
| `docker-compose.yaml` | Local dev stack: Postgres, Redis, MinIO, Phoenix, backend |
| `Dockerfile` | Backend container image (Python 3.11 + FFmpeg) |
| `.env.example` | All environment variables with defaults |

### `config/` — YAML Configuration

| File | Purpose |
|------|---------|
| `models.yaml` | Model provider config (ASR, VLM, LLM endpoints + parameters) |
| `agents.yaml` | Agent pipeline config (ReAct iterations, telemetry, sandbox settings) |
| `media_profiles.yaml` | Output profiles (1080x1920 short-form, 1920x1080 long-form, FFmpeg templates) |
| `subtitle_styles.yaml` | 4 subtitle presets (tiktok_pop, minimal, karaoke, outline) with ASS templates |
| `prompts/vlm_edit_grade.txt` | VLM system prompt for dense per-second edit-grade analysis |

### `src/autovid/schemas/` — Pydantic Data Models

| File | Key Classes | Purpose |
|------|-------------|---------|
| `transcript.py` | `WordSegment`, `Transcript` | ASR output with word-level timing, speech segment detection, Remotion export |
| `vlm.py` | `SecondAnalysis`, `ChunkVLMAnalysis`, `BoundingBox`, `SubjectPosition` | Dense per-second VLM output: edit signals, spatial grounding, scene composition |
| `chunk.py` | `ChunkMetadata`, `AudioFeatures` | Phase 1 output per chunk: transcript + VLM + audio aggregated |
| `project.py` | `ProjectRequest`, `EditPreferences`, `Platform`, `ProjectResult` | API request/response models for project lifecycle |
| `clip_spec.py` | `ClipSpec`, `EditSegment`, `ZoomSpec`, `OverlaySpec`, `Keyframe` | ReAct loop output: complete edit plan with segments, transitions, meme points |
| `music.py` | `MusicTrack`, `DuckPoint` | Music agent output: track selection with auto-ducking during speech |
| `meme.py` | `MemeInsert`, `SFXInsert`, `MemeLayer` | Meme/SFX agent output: overlays with VLM-derived coordinates + paired SFX |
| `composition.py` | `RemotionComposition`, `RemotionSequence`, `RemotionOverlay`, `RemotionSubtitle`, `RemotionAudio` | Thread-safe in-memory composition state — the central accumulator agents write to |
| `timeline.py` | `TimelineJSON`, `TimelineLayer`, `TimelineOutput` | Serialized composition → Remotion render props (1:1 mapping to React components) |

### `src/autovid/api/` — FastAPI Application

| File | Purpose |
|------|---------|
| `app.py` | FastAPI app with CORS, lifespan hooks, route registration |
| `routes/projects.py` | `POST /projects`, `POST /upload`, `PUT /order`, `POST /edit` |
| `routes/jobs.py` | `GET /jobs/{id}`, `WS /jobs/{id}/stream` (real-time agent updates) |
| `routes/clips.py` | `GET /clips/{id}`, `POST /clips/{id}/publish` |
| `routes/social.py` | `POST /social-accounts`, `GET /social-accounts` |

### `src/autovid/agents/` — Agentic Pipeline

| File | Purpose |
|------|---------|
| `director.py` | Top-level orchestrator: spawns sandbox, runs ReAct → parallel agents → assembly → publish |
| `react_loop.py` | ReAct (Observe/Think/Act/Check) cycle: reads VLM analysis, emits Remotion operations, 2-5 iterations |
| `remotion_tools.py` | Remotion tool wrappers: `remotion_add_sequence`, `remotion_add_overlay`, `remotion_add_subtitle`, `remotion_add_audio` |
| `composition_state.py` | Manages in-memory `RemotionComposition` lifecycle, serialization to TimelineJSON |
| `subtitle.py` | Subtitle Agent: generates kinetic subtitles from word-level transcript (z=2-4) |
| `music.py` | Music Agent: selects track, generates duck points from transcript (audio layer) |
| `meme_sfx.py` | Meme/SFX Agent: places overlays at VLM-detected moments with spatial coordinates (z=5-10) |
| `assembly.py` | Assembly Agent (thin): validates composition, resolves URIs, triggers sandbox render |
| `publishing.py` | Publishing Agent: uploads to YouTube/TikTok/Instagram with OAuth handling |

### `src/autovid/ingestion/` — Async Ingestion Pipeline (Phase 1)

| File | Purpose |
|------|---------|
| `pipeline.py` | Orchestrates per-video ingestion: chunk → ASR+Audio (parallel) → VLM (with context) |
| `chunker.py` | Scene-detect + temporal splitting into 10-30s chunks via FFmpeg |
| `asr_worker.py` | Per-chunk speech recognition → word-level `Transcript` |
| `vlm_worker.py` | Per-chunk dense VLM analysis → `ChunkVLMAnalysis` with edit signals and bounding boxes |
| `audio_analyzer.py` | Loudness, silence detection, energy profile, adaptive FPS decision |

### `src/autovid/models/` — Model Pluggability

| File | Purpose |
|------|---------|
| `contracts.py` | `ASRProvider`, `VLMProvider`, `LLMProvider` — typed Protocol interfaces |
| `adapters/whisper_local.py` | Local Whisper ASR via faster-whisper (809M params, 99 languages) |
| `adapters/qwen35_vl.py` | Primary VLM: Qwen3.5-397B-A17B via vLLM/NIM (native video input) |
| `adapters/llama_local.py` | Local LLM: Llama 3.3 via vLLM OpenAI-compatible API |

### `src/autovid/media/` — Media Processing

| File | Purpose |
|------|---------|
| `ffmpeg_tools.py` | FFmpeg command builders: normalize, extract audio, scene-detect, audio mix, burn subtitles |
| `audio_mixer.py` | Post-Remotion audio mixing: music ducking + SFX layering via FFmpeg |

### `src/autovid/sandbox/` — Docker Sandbox Management

| File | Purpose |
|------|---------|
| `manager.py` | Container lifecycle: create, stage inputs from MinIO, collect outputs, destroy |
| `client.py` | HTTP client for sandbox-server.js API (files, exec, ffmpeg, remotion render) |
| `tools.py` | LangGraph tool wrappers: `sandbox_list_files`, `sandbox_exec`, `sandbox_render_remotion` |
| `schemas.py` | `FileInfo`, `ExecResult`, `RenderResult`, `AssetInfo` Pydantic models |

### `src/autovid/storage/` — Data Layer

| File | Purpose |
|------|---------|
| `object_store.py` | MinIO/S3 wrapper: upload, download, presigned URLs, URI parsing |
| `db.py` | SQLAlchemy ORM models (projects, videos, chunks, jobs, clips, social_accounts) + async session factory |
| `chunk_store.py` | ChunkMetadata read/write interface for Phase 1 → Phase 2 data flow |

### `src/autovid/social/` — Social Platform Integration

| File | Purpose |
|------|---------|
| `youtube.py` | YouTube Data API v3: OAuth + resumable upload |
| `tiktok.py` | TikTok Content Posting API: init → PUT binary → inbox |
| `instagram.py` | Instagram Graph API: create container → poll → publish |
| `auth.py` | OAuth token management: store, refresh, encrypt |

### `sandbox/` — Docker Sandbox Image

| File | Purpose |
|------|---------|
| `Dockerfile` | Sandbox image: Node 20 + FFmpeg + Python 3.11 + Remotion CLI |
| `sandbox-server.js` | Express HTTP API inside the container (filesystem, exec, ffmpeg, remotion render endpoints) |
| `package.json` | Express dependency for sandbox server |
| `remotion-compositions/Root.tsx` | Remotion entry point registering TimelineComposition |
| `remotion-compositions/TimelineComposition.tsx` | Reads TimelineJSON props, renders all layers sorted by z_index |
| `remotion-compositions/VideoLayer.tsx` | Base video segment with crop, speed, and transition effects |
| `remotion-compositions/MemeOverlay.tsx` | Meme overlay with spring physics, bounce, slide-down animations + custom keyframes |
| `remotion-compositions/KineticSubtitle.tsx` | Per-word animated subtitles with style presets (tiktok_pop, minimal, karaoke, outline) |
| `remotion-compositions/TransitionEffect.tsx` | Between-segment transitions: crossfade, swipe, zoom, glitch |

### `frontend/` — Next.js Web UI

| File | Purpose |
|------|---------|
| `package.json` | Dependencies: Next.js, React Flow, dnd-kit, Remotion, Tailwind |
| `next.config.js` | API proxy to backend (localhost:3000 → localhost:8080) |
| `tailwind.config.ts` | Dark theme with canvas colors, status colors, pulse animations |
| **App** | |
| `src/app/page.tsx` | Main editor: Sidebar (25%) + React Flow Canvas (75%) |
| `src/app/traces/page.tsx` | Phoenix trace dashboard (iframe embed) |
| `src/app/layout.tsx` | Root layout with dark theme |
| **Canvas Components** | |
| `src/components/canvas/CanvasPanel.tsx` | React Flow provider with custom node types and dark background |
| `src/components/canvas/VideoNode.tsx` | Draggable video node: thumbnail, filename, duration, ingestion status |
| `src/components/canvas/AgentNode.tsx` | Agent pipeline node: rounded, color-coded status, iteration counter |
| `src/components/canvas/ToolNode.tsx` | Tool invocation node: smaller, dashed border, latency display |
| `src/components/canvas/graph-layout.ts` | Graph layout builder: video chain → ReAct → parallel agents → assembly → publish |
| **Sidebar Components** | |
| `src/components/sidebar/SidebarPanel.tsx` | Container: upload zone + dnd-kit sortable video list + style prompt + clip previews |
| `src/components/sidebar/UploadZone.tsx` | Drag-and-drop file upload area |
| `src/components/sidebar/VideoCard.tsx` | Sortable video card with drag handle, thumbnail, status |
| `src/components/sidebar/StylePrompt.tsx` | Style prompt textarea + GO button |
| `src/components/sidebar/ClipPreview.tsx` | Rendered clip preview with accept/reject/publish actions |
| **Common** | |
| `src/components/common/StatusDot.tsx` | Color-coded status indicator (idle/running/success/error) |
| `src/components/common/ProgressBadge.tsx` | Progress percentage badge |
| `src/components/traces/PhoenixEmbed.tsx` | Phoenix UI iframe embed |
| **Hooks** | |
| `src/hooks/useWebSocket.ts` | WebSocket hook for real-time pipeline status → agent state updates |
| `src/hooks/useProjectState.ts` | Project state: videos, clips, sequence, style prompt, upload/reorder/edit actions |
| **Lib** | |
| `src/lib/api.ts` | REST API client for all backend endpoints |
| `src/lib/sync.ts` | Sidebar ↔ canvas sequence sync utilities |

---

## Quick Start

```bash
# 1. Clone and configure
cp .env.example .env

# 2. Start infrastructure
docker compose up -d postgres redis minio minio-init phoenix

# 3. Build sandbox image
docker compose build sandbox-build

# 4. Install backend
pip install -e ".[dev]"

# 5. Start backend
uvicorn autovid.api.app:app --port 8080 --reload

# 6. Install and start frontend
cd frontend && npm install && npm run dev
```

Open `http://localhost:3000` for the editor UI, `http://localhost:6006` for Phoenix traces.

---

## Data Flow

```
User uploads video
    ↓
POST /api/v1/projects/{id}/upload
    ↓
Ingestion Pipeline (async, immediate)
    ├── Chunker: split at scene boundaries → 10-30s chunks
    ├── ASR Worker: Whisper → word-level WordSegment[]
    ├── Audio Analyzer: loudness, energy, silence, peaks
    └── VLM Worker: Qwen3.5 → SecondAnalysis per second
            (edit signals, bounding boxes, energy, emotion)
    ↓
ChunkStore (PostgreSQL JSONB)
    ↓
User submits style prompt → POST /api/v1/projects/{id}/edit
    ↓
Director Agent
    ├── Spawns Docker sandbox
    ├── ReAct Loop (2-5 iterations)
    │       Observe → Think → Act → Check
    │       (emits remotion_add_sequence, remotion_add_overlay, ...)
    │       → builds RemotionComposition incrementally
    ├── Parallel Post-Processing
    │       ├── Subtitle Agent (z=2-4) — kinetic word-by-word
    │       ├── Music Agent (audio) — auto-ducked background music
    │       └── Meme/SFX Agent (z=5-10) — overlays at VLM bounding boxes
    ├── Assembly Agent
    │       Validate → Serialize to TimelineJSON → Remotion render → FFmpeg audio mix
    └── Publishing Agent
            YouTube / TikTok / Instagram upload
```

---

## Configuration

All model and pipeline behavior is controlled via YAML — no code changes needed:

- **Swap ASR model**: Edit `config/models.yaml` → `models.asr.provider`
- **Swap VLM model**: Edit `config/models.yaml` → `models.vlm.provider`
- **Adjust ReAct iterations**: Edit `config/agents.yaml` → `react_loop.max_iterations`
- **Change subtitle style**: Edit `config/subtitle_styles.yaml` or set in `EditPreferences`
- **Customize VLM prompt**: Edit `config/prompts/vlm_edit_grade.txt`

---

## 112 Source Files | ~10,000 Lines of Code

Built for extensibility. Every model-dependent step is behind a typed `Protocol`. Every agent is independently testable. The sandbox isolates all code execution. The UI syncs sidebar drag-and-drop with the React Flow canvas in real-time.
