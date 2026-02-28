# Open-Stitch: Agentic Short-Form Video Editing Platform -- Full Specification

---

## 1. Vision and Product Scope

**One-liner:** An open, model-pluggable AI agent system that ingests raw footage and autonomously produces edited short-form videos with subtitles, transitions, memes, background music, and sound effects -- then publishes them to social platforms.

**Target users:** TikTokers, Reels creators, YouTube Shorts creators, hackathon teams wanting a compiled recap.

### 1.1 User Flow

1. **Upload** -- Creator uploads one or more raw video files (drag-and-drop, S3 link, or phone upload). Async ingestion starts immediately per video (chunking, ASR, VLM, audio analysis) -- no waiting.
2. **Sequence** -- Uploaded videos appear as draggable thumbnail cards in a storyboard panel. The user grabs and reorders them vertically to define the narrative sequence. **The user's drag order is the source of truth** -- no unreliable EXIF timestamp extraction. While the user is arranging, ingestion continues in the background.
3. **Style Prompt** -- Creator writes a free-text prompt describing the style/vibe they want (e.g. "funny vlog recap with memes", "cinematic travel montage with chill beats", "fast-paced tech demo with hype energy"). This prompt drives every downstream agent decision.
4. **Watch the Pipeline** -- On the side panel, a live agent graph (inspired by NeMo Agent Toolkit's graph view) shows the pipeline nodes lighting up as they execute: Chunking -> ASR -> VLM -> ReAct Loop -> Subtitles/Music/Memes -> Assembly -> Publish. Each node is clickable to inspect traces, tool calls, reasoning, and latency.
5. **Review + Publish** -- User previews rendered clips in the storyboard panel, accepts/rejects, then publishes to selected platforms.

### 1.2 Core Use Cases

- **Single-creator flow:** Upload raw footage + style prompt -> receive multiple auto-cut short clips with subtitles, memes, sound effects, background music, and transitions -> one-click publish to TikTok/IG/YouTube.
- **Multi-creator compilation (hackathon demo):** Multiple teams submit vlog clips at defined checkpoints -> system weaves them into one YouTube recap + per-team short-form clips.
- **Multi-language subtitles:** Auto-generate word-level subtitles in source language, optionally translate to N target languages, with TikTok-style kinetic typography.

### 1.3 Output Artifacts

- Short-form MP4 clips (9:16 vertical, 15-60s, H.264, AAC) with burned-in subtitles, background music, meme overlays, sound effects
- Long-form compiled MP4 (16:9 or adaptive, variable length)
- Subtitle files (SRT/VTT) per clip per language
- Social upload confirmations with share URLs

---

## 2. High-Level Architecture

The architecture is split into two phases that overlap in time: **async ingestion** (starts on upload) and **agentic editing** (starts when style prompt is submitted).

### 2.1 Technology Stack

- **Backend language:** Python 3.11+
- **Frontend:** React + Next.js (App Router), React Flow (agent graph), @dnd-kit (drag reorder), Tailwind CSS (dark theme)
- **Agent framework:** LangGraph (via `deepagents` package) + NVIDIA NeMo Agent Toolkit (`nvidia-nat` v1.4+)
- **API:** FastAPI with WebSocket support for real-time job status + agent trace streaming
- **Sandbox:** Docker-based isolated execution environment per job (Remotion + FFmpeg + Node.js + Python)
- **Task queue:** Redis + Arq (or Celery) for long-running media jobs
- **Database:** PostgreSQL (projects, clips, social tokens, user prefs)
- **Object storage:** MinIO (local dev) / S3 (production)
- **Video processing:** FFmpeg (CLI) inside sandbox container
- **Audio/Music:** Epidemic Sound API, Mubert API, or local royalty-free library
- **Meme/SFX:** Voicy API (500K+ meme clips), Soundly library, or local curated SFX pack
- **Containerization:** Docker Compose (dev), sandbox containers spawned per job
- **Observability:** OpenTelemetry -> NAT profiler / Phoenix / Langfuse

### 2.2 Sandboxed Execution Environment

Every editing job runs inside an **isolated Docker container** (the "sandbox"). The agent does not execute Remotion renders, FFmpeg commands, or file operations on the host -- everything happens inside the sandbox.

**Why a sandbox:**
- **Security:** The LLM agent can generate and execute code. Running this on the host is dangerous. The sandbox is ephemeral, resource-limited, and network-isolated.
- **Reproducibility:** Each job gets a clean environment with known dependencies.
- **File awareness:** The agent needs to reason about what files exist. A well-structured sandbox filesystem gives the agent a predictable layout.
- **Portability:** The same sandbox image runs locally (Docker Compose) and in production (K8s pods).

**Sandbox lifecycle:**
1. **Spawn:** When Phase 2 starts, the Sandbox Manager creates a new container from the `autovid-sandbox` image.
2. **Stage inputs:** Sandbox Manager copies raw video chunks from MinIO into `/workspace/input/`, copies meme/SFX/music assets into `/workspace/assets/`.
3. **Agent operates:** The agent calls sandbox tools to execute commands, read/write files, and inspect the filesystem.
4. **Collect outputs:** When rendering completes, Sandbox Manager copies `/workspace/output/*` back to MinIO.
5. **Teardown:** Container is destroyed. Volume is cleaned up.

**Sandbox Docker image (`autovid-sandbox`):**

```dockerfile
FROM node:20-slim
RUN apt-get update && apt-get install -y ffmpeg python3 python3-pip
RUN npm install -g @remotion/cli remotion
WORKDIR /workspace
COPY remotion-compositions/ /workspace/code/
EXPOSE 9876
CMD ["node", "/workspace/code/sandbox-server.js"]
```

**Agent sandbox tools** (registered in LangGraph, callable by any agent):

```python
# Filesystem tools
sandbox_list_files(path: str) -> list[FileInfo]
sandbox_read_file(path: str) -> str | bytes
sandbox_write_file(path: str, content: str | bytes) -> None
sandbox_delete_file(path: str) -> None
sandbox_get_file_info(path: str) -> FileInfo

# Execution tools
sandbox_exec(command: str, timeout_s: int = 300) -> ExecResult
sandbox_render_remotion(timeline_json: dict, output_path: str) -> RenderResult
sandbox_run_ffmpeg(args: list[str], timeout_s: int = 300) -> ExecResult

# Asset tools
sandbox_list_assets(category: str) -> list[AssetInfo]
sandbox_search_assets(query: str, category: str) -> list[AssetInfo]

# Transfer tools
sandbox_stage_from_store(store_uri: str, sandbox_path: str) -> None
sandbox_export_to_store(sandbox_path: str) -> str  # returns MinIO URI
```

---

## 3. Async Ingestion Pipeline (Phase 1)

Ingestion starts **immediately when videos are uploaded**, before the user submits their style prompt. This eliminates the biggest latency bottleneck by overlapping it with user thinking time.

### 3.1 Chunking Strategy

Videos are split into time-aligned chunks for parallel processing:

1. **Temporal chunking** -- Split each video into 10-30 second segments at scene boundaries (detected via FFmpeg `select='gt(scene,0.3)'`). Fall back to fixed-interval splits if scene detection yields too few/many.
2. **Per-chunk async fan-out** -- Each chunk is processed by three workers:
   - **ASR Worker:** Transcribe the chunk's audio -> word-level timestamps + speaker labels.
   - **Audio Analyzer:** Compute loudness (LUFS), silence detection, speech rate, spectral energy, peak timestamps. Determines **adaptive FPS**: if any second has energy > 0.7, flag for high-FPS VLM analysis.
   - **VLM Worker (dense per-second analysis):** Sends the raw video chunk to Qwen3.5-397B-A17B via `analyze_video_chunk()`. Returns a full `ChunkVLMAnalysis` with one `SecondAnalysis` entry per second.
3. **Results stored in ChunkStore** -- Each chunk gets a `ChunkMetadata` record with transcript, dense VLM analysis, audio features, and timestamps.

### 3.2 Video Sequencing (User-Driven)

- **No auto-timestamp extraction.** The user defines the sequence by dragging video thumbnail cards in the storyboard UI.
- The backend stores this as an ordered list of `video_id`s on the project record.
- Reordering does not restart ingestion -- chunks are indexed per-video and re-sequenced on read.

---

## 4. Agentic Editing Pipeline (Phase 2)

Triggered when the user submits their **style prompt**. The pipeline reads pre-computed chunk metadata from Phase 1 and builds the final video bottom-up.

### 4.1 ReAct Reasoning Loop

The core of the editing intelligence is a **ReAct (Reason + Act) loop** implemented as a LangGraph cycle:

1. **Observe** -- Read chunk metadata (transcripts, VLM captions, audio features) from ChunkStore.
2. **Think** -- Given the user's style prompt and the observed content, reason about what makes good content.
3. **Act** -- Call tools to refine the plan: re-score highlights, request more VLM detail, adjust clip boundaries.
4. **Check** -- Evaluate: Does the plan match the style prompt? Are clips the right length? If not, loop back to Think.

This loop runs 2-5 iterations (configurable) before committing to a final edit plan.

### 4.2 Agent Definitions

**Core design principle: Remotion-first action vocabulary.** The agents' action vocabulary IS Remotion operations. Every tool call incrementally builds a `RemotionComposition` state object that maps 1:1 to what Remotion will render inside the sandbox.

**Director Agent (top-level orchestrator)**
- Role: Receives project + style prompt, spawns the sandbox, kicks off ReAct loop, then dispatches parallel post-processing agents.
- Framework: LangGraph Deep Agent with planning + sub-agent delegation.

**ReAct Reasoning Agent (the brain)**

Understanding tools (read-only):
- `read_chunk_metadata(project_id)` -- Load all pre-computed chunk data.
- `query_edit_signals(project_id, signal_type)` -- Filter across all chunks for specific edit signals.
- `get_vlm_detail(chunk_id, question)` -- Ask Qwen3.5 a follow-up about a specific chunk.
- `locate_subject(frame_uri, query)` -- Spatial grounding. Ask VLM "where is the person's face?" -> normalized BoundingBox.
- `find_audio_peaks(audio_uri, top_n)` -- Returns the top_n loudest timestamps.
- `search_assets(query, category)` -- Search available memes, SFX, music in the sandbox.

Remotion composition tools (write):
- `remotion_add_sequence(chunk_uri, start_ms, end_ms, speed, crop, position_in_timeline_ms)` -- Add a video segment.
- `remotion_add_overlay(asset_uri, at_ms, duration_ms, x, y, scale, rotation, opacity, z_index, animation, keyframes, paired_sfx)` -- Add a meme image overlay.
- `remotion_add_subtitle(text, start_ms, end_ms, style_preset, position, keyframes)` -- Add kinetic subtitle.
- `remotion_add_transition(type, at_ms, duration_ms)` -- Add a transition between sequences.
- `remotion_add_audio(audio_uri, start_ms, volume, duck_points, pitch_shift, fade_in_ms, fade_out_ms)` -- Add background music or SFX.
- `remotion_set_output(width, height, fps, codec)` -- Configure output format.
- `remotion_preview()` -- Trigger a quick low-res preview render inside the sandbox.
- `remotion_modify_sequence(sequence_id, speed?, crop?, start_ms?, end_ms?)` -- Modify an existing sequence.
- `remotion_remove_layer(layer_id)` -- Remove a layer.

**Subtitle Agent** (runs async, parallel with Music + Meme agents)
- Tools: `generate_subtitle_track`, `shorten_for_platform`, `remotion_add_subtitle`
- Formats word-level timestamps into styled subtitle blocks with kinetic typography presets.

**Music Agent** (runs async, parallel with Subtitle + Meme agents)
- Tools: `select_background_track`, `trim_and_loop_track`, `duck_under_speech`, `remotion_add_audio`
- Sources: Epidemic Sound API, Mubert API, local library.

**Meme/SFX Agent** (runs async, parallel with Subtitle + Music agents)
- Tools: `detect_meme_moments`, `search_assets`, `remotion_add_overlay`, `remotion_add_audio`
- Decision logic uses the dense VLM analysis (edit signals, bounding boxes).

**Assembly Agent (validation + sandbox render execution)**
1. Validates the `RemotionComposition`: checks all referenced assets exist in the sandbox.
2. Resolves asset URIs to absolute sandbox paths.
3. Serializes composition to TimelineJSON and writes it to the sandbox.
4. Triggers rendering: `sandbox_render_remotion` (Remotion visual layers) + `sandbox_run_ffmpeg` (audio mix).
5. Exports: `sandbox_export_to_store` -> MinIO URI.

**Publishing Agent**
- Tools: `upload_youtube`, `upload_tiktok`, `upload_instagram_reel`
- Handles OAuth token refresh, rate limits, retry logic.

### 4.3 Parallel Post-Processing (Async Fan-Out)

After the ReAct loop commits its initial `RemotionComposition`, three agents run in parallel: Subtitle Agent (z=2-4), Music Agent (audio layers), Meme/SFX Agent (z=5-10 + audio). The Assembly Agent waits for all three, validates, then triggers the sandbox render.

---

## 5. Model Pluggability Contracts

Every model-dependent step is behind a typed Python protocol. Adapters implement the protocol for specific backends.

### 5.1 ASR Contract

```python
from dataclasses import dataclass

@dataclass
class WordSegment:
    text: str
    start_ms: int
    end_ms: int
    confidence: float
    speaker: str | None = None

class ASRProvider(Protocol):
    def transcribe(self, audio_uri: str, language: str = "auto") -> list[WordSegment]: ...
    def supported_languages(self) -> list[str]: ...
```

Bundled adapters: `WhisperLocalAdapter` (whisper-large-v3-turbo), `RivaNIMAdapter` (NVIDIA Riva), `WhisperAPIAdapter` (OpenAI).

### 5.2 VLM Contract

Primary model: **Qwen3.5-397B-A17B** -- MoE architecture (17B active params), native video token processing via early-fusion. Scores 87.5% VideoMME, 84.7% Video-MMMU.

```python
class BoundingBox(BaseModel):
    x: float       # normalized 0.0-1.0 (left edge)
    y: float       # normalized 0.0-1.0 (top edge)
    width: float
    height: float

class SubjectPosition(BaseModel):
    label: str
    bbox: BoundingBox
    face_emotion: str | None = None
    is_speaking: bool = False

class SceneComposition(BaseModel):
    framing: str
    lighting: str
    background: str
    visual_complexity: float

class SecondAnalysis(BaseModel):
    second: int
    timestamp_ms: int
    visual_description: str
    spoken_text: str | None = None
    emotion: str
    energy: float  # 0.0-1.0
    edit_signal: str | None = None  # "punchline", "cut_point", "skip", "reaction", "energy_shift", "dramatic_beat", "awkward_pause"
    edit_signal_confidence: float = 0.0
    edit_signal_reason: str | None = None
    subjects: list[SubjectPosition] = []
    scene_composition: SceneComposition | None = None
    camera_movement: str | None = None
    on_screen_text: str | None = None

class ChunkVLMAnalysis(BaseModel):
    chunk_id: str
    seconds: list[SecondAnalysis]
    summary: str
    highlight_seconds: list[int]
    skip_ranges: list[tuple[int, int]]
    dominant_mood: str
    narrative_role: str
    suggested_speed: float = 1.0

class VLMProvider(Protocol):
    def describe_frame(self, image_uri: str, prompt: str) -> FrameAnalysis: ...
    def describe_frames_batch(self, image_uris: list[str], prompt: str) -> list[FrameAnalysis]: ...
    def analyze_video_chunk(self, video_uri: str, prompt: str, fps: int = 1) -> ChunkVLMAnalysis: ...
    def locate_subject(self, image_uri: str, query: str) -> BoundingBox: ...
```

Bundled adapters: `Qwen35VLAdapter` (primary), `QwenVLAdapter` (fallback), `LLaVAAdapter`, `VILANIMAdapter`, `GeminiProAdapter` (optional cloud deep reasoning), `OpenAIVisionAdapter`.

### 5.3 LLM Contract

```python
class LLMProvider(Protocol):
    def generate(self, messages: list[dict], json_schema: dict | None = None, temperature: float = 0.7) -> str: ...
    def generate_structured(self, messages: list[dict], response_model: type[BaseModel]) -> BaseModel: ...
```

Bundled adapters: `LocalLlamaAdapter`, `NIMAdapter`, `OpenAIAdapter`.

### 5.4 Configuration (YAML)

See `config/models.yaml`. Swapping models = changing YAML only, no code changes.

### 5.5 Security / Local-First

- All model services run as Docker containers on the user's machine or private cluster.
- No data leaves the network by default.
- Qwen3.5-397B-A17B runs via vLLM or NVIDIA NIM on local GPUs (~40GB VRAM with MoE offloading).
- Optional `vlm_cloud` tier (Gemini 3 Pro) disabled by default.
- Credentials stored in `.env`, never logged.

### 5.6 VLM System Prompt for Edit-Grade Understanding

The edit-grade VLM system prompt is stored at `config/prompts/vlm_edit_grade.txt`. It instructs the VLM to produce dense, second-by-second editorial manifests including:
- Per-second `SecondAnalysis` with edit signals, bounding boxes, energy scores
- Chunk-level summary, dominant mood, narrative role, highlight seconds, skip ranges
- Spatial grounding for meme placement (normalized bounding boxes for all subjects)

Edit signals: `punchline`, `cut_point`, `skip`, `reaction`, `energy_shift`, `dramatic_beat`, `awkward_pause`.

---

## 6. Core Data Schemas

### 6.1 Project Request

```python
class ProjectRequest(BaseModel):
    project_id: str = Field(default_factory=lambda: str(uuid4()))
    video_uris: list[str]
    creator_id: str | None = None
    style_prompt: str
    preferences: EditPreferences
    target_platforms: list[Platform]

class EditPreferences(BaseModel):
    clip_count: int = 5
    clip_length_range: tuple[int, int] = (15, 60)
    subtitle_languages: list[str] = ["en"]
    subtitle_style: SubtitleStyle = SubtitleStyle.TIKTOK_POP
    aspect_ratio: str = "9:16"
    include_hooks: bool = True
    include_memes: bool = True
    include_background_music: bool = True
    include_sfx: bool = True
    include_compilation: bool = False
    music_mood: str | None = None

class Platform(str, Enum):
    TIKTOK = "tiktok"
    INSTAGRAM = "instagram"
    YOUTUBE_SHORTS = "youtube_shorts"
    YOUTUBE_LONG = "youtube_long"
```

### 6.2 Chunk Metadata (Phase 1 Output)

```python
class ChunkMetadata(BaseModel):
    chunk_id: str
    video_id: str
    project_id: str
    chunk_index: int
    start_ms: int
    end_ms: int
    duration_ms: int
    video_uri: str
    audio_uri: str
    transcript: list[WordSegment] | None = None
    vlm_analysis: ChunkVLMAnalysis | None = None
    audio_features: AudioFeatures | None = None

class AudioFeatures(BaseModel):
    avg_loudness_lufs: float
    peak_loudness_lufs: float
    silence_segments: list[tuple[int, int]]
    speech_rate_wpm: float | None = None
    has_music: bool = False
    has_laughter: bool = False
    energy_profile: list[float]
    peak_timestamps_ms: list[int] = []
```

### 6.3 ClipSpec (Edit Plan Output)

```python
class ClipSpec(BaseModel):
    clip_id: str = Field(default_factory=lambda: str(uuid4()))
    source_chunks: list[str]
    segments: list[EditSegment]
    aspect_ratio: str = "9:16"
    subtitle_config: SubtitleConfig
    transitions: list[TransitionSpec] = []
    meme_points: list[MemePoint] = []
    music_mood_tags: list[str] = []
    overlays: list[OverlaySpec] = []
    platform: Platform
    title: str
    description: str
    tags: list[str] = []
```

### 6.4 Music Track

```python
class MusicTrack(BaseModel):
    track_id: str
    source: str
    track_uri: str
    mood_tags: list[str]
    duration_ms: int
    volume: float = 0.15
    duck_points: list[DuckPoint] = []
    fade_in_ms: int = 2000
    fade_out_ms: int = 3000
```

### 6.5 Meme Layer

```python
class MemeLayer(BaseModel):
    clip_id: str
    inserts: list[MemeInsert | SFXInsert]

class MemeInsert(BaseModel):
    type: str = "image_overlay"
    at_ms: int
    duration_ms: int = 2000
    image_uri: str
    position: tuple[float, float] = (0.5, 0.3)
    scale: float = 0.3
    animation: str = "pop_in"
    keyframes: list[Keyframe] = []
    paired_sfx: str | None = None

class SFXInsert(BaseModel):
    type: str = "sound_effect"
    at_ms: int
    sfx_uri: str
    volume: float = 0.8
    name: str
    pitch_shift: float = 0.0
```

### 6.6 Keyframe Schema

```python
class Keyframe(BaseModel):
    time_ms: int
    x: float | None = None
    y: float | None = None
    scale: float | None = None
    rotation: float | None = None
    opacity: float | None = None
    easing: str = "linear"  # "linear", "ease_in", "ease_out", "spring", "bounce"
```

### 6.7 Timeline JSON (Remotion Composition)

The Assembly Agent serializes all layers into a unified TimelineJSON that maps directly to Remotion `<Composition>` props. Each layer has: `type`, `z_index`, `source`, timing fields, and animation/keyframe data. The JSON is written to `/workspace/intermediate/timeline/clip_N.json` in the sandbox before rendering.

---

## 7. API Surface

### 7.1 REST Endpoints (FastAPI)

- `POST /api/v1/projects` -- Create project. Returns `project_id`. Starts async ingestion.
- `POST /api/v1/projects/{id}/upload` -- Upload raw video. Returns `video_id`.
- `GET /api/v1/projects/{id}` -- Get project status, video list, ingestion progress, clip list.
- `PUT /api/v1/projects/{id}/order` -- Reorder videos.
- `POST /api/v1/projects/{id}/edit` -- Submit style prompt + preferences. Returns `job_id`.
- `GET /api/v1/jobs/{id}` -- Get job status.
- `GET /api/v1/jobs/{id}/stream` -- WebSocket for real-time agent step updates.
- `GET /api/v1/clips/{id}` -- Get clip metadata and download URL.
- `POST /api/v1/clips/{id}/publish` -- Publish clip to platform(s).
- `POST /api/v1/social-accounts` -- Register OAuth tokens.
- `GET /api/v1/social-accounts` -- List connected social accounts.

### 7.2 WebSocket Events

```
project:ingestion_progress  {project_id, video_id, chunks_done, chunks_total}
job:status                  {job_id, phase, step, progress, message}
job:react_iteration         {job_id, iteration, thought, action, result}
job:agent_log               {job_id, agent, tool, input, output, latency_ms}
job:clip_ready              {job_id, clip_id, preview_url}
job:complete                {job_id, clips: [...], compilation_url?}
job:error                   {job_id, error, step}
```

---

## 8. Social Platform Integration

### 8.1 YouTube (Data API v3)
- **Auth:** OAuth 2.0 with `youtube.upload` scope.
- **Upload:** Resumable upload protocol.
- **Quota:** ~1,600 units per upload; default daily quota is 10,000.

### 8.2 TikTok (Content Posting API)
- **Auth:** OAuth 2.0 via TikTok Login Kit.
- **Constraints:** Max 500MB, MP4/H.264 only, 6 requests/min/user.

### 8.3 Instagram (Graph API)
- **Auth:** Facebook Login for Business with `instagram_content_publish` permission.
- **Upload flow:** POST media container -> poll status -> POST media_publish.
- **Constraints:** Video must be hosted on a public URL during upload.

---

## 9. UI Architecture

The UI has three distinct views: the **main editing canvas** (interactive node graph), the **sidebar** (draggable video list), and the **NAT trace dashboard** (observability).

### 9.1 Layout

```
+--------------------------------------------------------------------------------+
|  Auto-Vid            [Style Prompt: "funny vlog w/ memes"]  [GO]  [Traces tab] |
+-------------------------------+------------------------------------------------+
|  SIDEBAR (~25%)               |  MAIN CANVAS (~75%)                            |
|  Draggable Video List         |  Interactive Node Graph (React Flow)            |
|  [Upload Zone]                |      Video nodes -> Agent pipeline nodes        |
|  1. [intro.mp4] [drag]        |                                                |
|  2. [demo.mp4]  [drag]        |      [ReAct Loop] -> [ASR] -> [VLM]            |
|  3. [night.mp4] [drag]        |      [Subtitle] -+                             |
|  [Style Prompt textarea]      |      [Music]    -+-> [Assembly] -> [Publish]   |
|  [GO]                         |      [Meme/SFX] -+                             |
|  [Clip 1 preview]             |                                                |
|  [Clip 2 preview]             |                                                |
+-------------------------------+------------------------------------------------+
```

### 9.2 Main Canvas: Interactive Node Graph (React Flow)

**Zone 1: Video Sequence (top of canvas)**
- Each uploaded video is a draggable node (thumbnail, filename, duration, ingestion status).
- Videos connected by edges in sequence order.
- Dragging nodes on canvas updates the sequence (synced with sidebar).

**Zone 2: Agent Pipeline (bottom of canvas)**
- Agent nodes (rounded boxes): ReAct Loop, Subtitle Agent, Music Agent, Meme/SFX Agent, Assembly Agent, Publishing Agent.
- Tool nodes (smaller, dashed border): each tool call.
- Node states: dark gray (idle), blue pulse (running), green (done), red (error), amber (ReAct iteration).
- Click any node to open a detail drawer.

### 9.3 Sidebar: Draggable Video List

- Upload zone at top, numbered video cards with drag handles.
- Style prompt textarea + GO button.
- After render: clip preview cards with inline video players + publish actions.

### 9.4 NAT Trace Dashboard

Option A (hackathon): Embed Phoenix UI iframe at `http://localhost:6006`.
Option B (production): Custom waterfall span viewer.

### 9.5 Technology

- `@xyflow/react` (React Flow v12) for node-graph canvas.
- `@dnd-kit/core` + `@dnd-kit/sortable` for sidebar reordering.
- Tailwind CSS v4, dark theme.
- Native WebSocket for real-time updates.

---

## 10. Media Processing Pipeline

### 10.1 Normalization Profile

Short-form: 1080x1920, 30fps, H.264, AAC, 44100Hz.
Long-form: 1920x1080, 30fps, H.264, AAC, 44100Hz.

### 10.2 Rendering Engine: Remotion (Primary) + FFmpeg (Audio)

All rendering runs inside the Docker sandbox. Remotion renders visual layers (video, subtitles, meme overlays with spring physics). FFmpeg handles audio mixing (background music ducking + SFX layering).

**Rendering pipeline (inside sandbox):**
```
TimelineJSON -> Remotion render -> clip_N_video.mp4
                                        |
                               FFmpeg audio mix -> clip_N.mp4
                                        |
                               export_to_store -> minio://clips/clip_N.mp4
```

### 10.3 Z-Axis Layer Stacking

1. z=0: Video layers (base footage, speed-adjusted, transitions)
2. z=2-4: Subtitle layers (kinetic typography, per-word animations)
3. z=5-10: Meme/overlay layers (positioned at VLM-derived coordinates)
4. z=-1: Audio layers (FFmpeg-mixed: speech + background music + SFX)

### 10.4 Subtitle Rendering

Subtitle style presets:
- **TIKTOK_POP:** White bold text, yellow highlight on active word, pop-in animation.
- **MINIMAL:** White regular text, lower third.
- **KARAOKE:** Word-by-word color fill, centered.
- **OUTLINE:** White text with black outline, no animation.

---

## 11. Music and Meme Asset Strategy

### 11.1 Background Music Sources

- **Epidemic Sound API** -- 40K+ tracks, mood/genre search, MCP server available.
- **Mubert API** -- AI-generated royalty-free music from text prompts.
- **Local library** -- Curated pack of 20-30 royalty-free tracks (Creative Commons).

### 11.2 Meme/SFX Sources

- **Voicy API** -- 500K+ audio meme clips.
- **Soundly library** -- 163 professionally re-recorded meme sounds (royalty-free).
- **Local SFX pack** -- ~50 curated files: transitions (whoosh, swipe, pop), reactions (vine boom, bruh, airhorn), dramatic (record scratch, dun dun dun).

---

## 12. Database Schema (PostgreSQL)

Key tables:
- `projects` -- id, creator_id, status, style_prompt, preferences (JSONB), video_sequence (JSONB)
- `videos` -- id, project_id, uri, original_filename, duration_ms, width, height, fps, sequence_index, ingestion_status
- `chunks` -- id, video_id, project_id, chunk_index, start_ms, end_ms, video_uri, audio_uri, transcript (JSONB), vlm_captions (JSONB), audio_features (JSONB), status
- `jobs` -- id, project_id, status, current_phase, current_step, react_iteration, progress, started_at, completed_at, error
- `clips` -- id, project_id, job_id, clip_spec (JSONB), rendered_uri, thumbnail_uri, status, platform
- `subtitles` -- id, clip_id, language, format, uri
- `music_tracks` -- id, clip_id, source, track_uri, mood_tags (JSONB), volume_config (JSONB)
- `meme_layers` -- id, clip_id, inserts (JSONB)
- `social_accounts` -- id, creator_id, platform, access_token (encrypted), refresh_token (encrypted), expires_at
- `publish_records` -- id, clip_id, social_account_id, platform, status, share_url, published_at

---

## 13. Hackathon MVP Scope

### Must-have (MVP)
- Web UI with React Flow canvas + draggable sidebar + Phoenix traces tab
- Video upload with async chunking + ingestion (Phase 1 starts on upload)
- User-driven video sequencing via drag-and-drop (sidebar + graph, synced)
- Style prompt input
- ASR with Whisper (local) -> word-level transcript per chunk
- Dense per-second VLM analysis with Qwen3.5-397B-A17B -> ChunkVLMAnalysis with edit signals and bounding boxes
- Audio peak detection + adaptive FPS (high-energy chunks: 4 FPS VLM analysis)
- ReAct reasoning loop (2-3 iterations) emitting Remotion operations directly
- Auto-subtitle generation (English, TikTok pop style) with kinetic keyframe animation
- Background music from local library, auto-ducked
- Meme image overlays with position/rotation/scale/animation
- Meme SFX from local pack paired with overlays
- Remotion-based rendering with Z-axis stacking, keyframe animations, spring physics
- FFmpeg audio post-mix
- YouTube upload (unlisted)
- Agent graph visible in UI with clickable node detail drawers
- NAT traces visible in Phoenix (embedded iframe)

### Nice-to-have (stretch)
- Custom trace waterfall UI
- Epidemic Sound / Mubert / Voicy API integration
- GIF meme overlays
- Multi-language subtitle translation
- TikTok + Instagram upload
- NAT hyperparameter sweep

### Out of scope for hackathon
- User auth / multi-tenancy
- Production deployment (K8s)
- Fine-tuned highlight scoring model
- Advanced transitions (motion graphics)

---

## 14. Repository Structure

```
auto-vid/
  SPEC.md
  pyproject.toml
  docker-compose.yaml
  .env.example
  config/
    models.yaml
    agents.yaml
    media_profiles.yaml
    subtitle_styles.yaml
    prompts/
      vlm_edit_grade.txt
  assets/
    sfx/
    memes/
    music/
  frontend/
    package.json
    next.config.js
    remotion.config.ts
    tailwind.config.ts
    src/
      app/
        page.tsx
        traces/page.tsx
        layout.tsx
      remotion/
        Root.tsx
        VideoLayer.tsx
        MemeOverlay.tsx
        KineticSubtitle.tsx
        TransitionEffect.tsx
        TimelineComposition.tsx
      components/
        canvas/
          CanvasPanel.tsx
          VideoNode.tsx
          AgentNode.tsx
          ToolNode.tsx
          AnimatedEdge.tsx
          NodeDetailDrawer.tsx
          ReActAccordion.tsx
          graph-layout.ts
        sidebar/
          SidebarPanel.tsx
          UploadZone.tsx
          VideoCard.tsx
          StylePrompt.tsx
          ClipPreview.tsx
        traces/
          PhoenixEmbed.tsx
        common/
          ProgressBadge.tsx
          StatusDot.tsx
      hooks/
        useWebSocket.ts
        useProjectState.ts
        useTraceData.ts
      lib/
        api.ts
        sync.ts
  src/
    autovid/
      __init__.py
      api/
        app.py
        routes/
          projects.py
          jobs.py
          clips.py
          social.py
      agents/
        director.py
        react_loop.py
        remotion_tools.py
        composition_state.py
        subtitle.py
        music.py
        meme_sfx.py
        assembly.py
        publishing.py
      ingestion/
        pipeline.py
        chunker.py
        asr_worker.py
        vlm_worker.py
        audio_analyzer.py
      models/
        contracts.py
        adapters/
          whisper_local.py
          riva_nim.py
          qwen35_vl.py
          qwen_vl.py
          llava.py
          gemini_pro.py
          llama_local.py
          nim_llm.py
          openai_fallback.py
      media/
        ffmpeg_tools.py
        remotion_render.py
        frame_sampler.py
        audio_mixer.py
        spatial_tools.py
        audio_analysis.py
      schemas/
        project.py
        chunk.py
        vlm.py
        clip_spec.py
        composition.py
        timeline.py
        transcript.py
        music.py
        meme.py
      social/
        youtube.py
        tiktok.py
        instagram.py
        auth.py
      sandbox/
        manager.py
        client.py
        tools.py
        schemas.py
      storage/
        object_store.py
        db.py
        chunk_store.py
      config.py
  sandbox/
    Dockerfile
    sandbox-server.js
    package.json
    remotion-compositions/
      Root.tsx
      VideoLayer.tsx
      MemeOverlay.tsx
      KineticSubtitle.tsx
      TransitionEffect.tsx
      TimelineComposition.tsx
      remotion.config.ts
  tests/
  scripts/
    seed_demo.py
```

---

## 15. Key Dependencies

**Backend (Python):**
- `nvidia-nat>=1.4`, `deepagents`, `langgraph`
- `langchain-core`, `langchain-openai`, `langchain-community`
- `fastapi`, `uvicorn`
- `arq` or `celery[redis]`
- `sqlalchemy`, `asyncpg`, `alembic`
- `boto3` or `minio`
- `faster-whisper`, `vllm`
- `google-api-python-client`, `google-auth-oauthlib`
- `httpx`, `pydantic>=2.0`
- `opentelemetry-sdk`
- `librosa` or `pyloudnorm`
- `pysrt`
- `docker` (Python Docker SDK)

**Frontend (TypeScript/React):**
- `next`, `react`, `react-dom`
- `remotion`, `@remotion/cli`, `@remotion/renderer`, `@remotion/player`
- `@xyflow/react` (React Flow v12)
- `@dnd-kit/core`, `@dnd-kit/sortable`
- `tailwindcss`

---

## 16. Competitive Differentiation

- **CapCut / Descript / Gling:** Closed-source, GUI-only, no model pluggability, no agentic pipeline. Auto-Vid is fully open, programmable, and introspectable.
- **Maestra / HappyScribe / Captions.ai:** Transcription + captioning only. Auto-Vid does end-to-end: highlight detection, edit planning, memes, music, rendering, and publishing.
- **Short-video-maker (OSS):** Template-driven text-to-video, not vlog-to-shorts. No VLM understanding, no agentic planning.
- **NVIDIA VSS Blueprint:** Optimized for search/summarization/Q&A, not editing.

**Unique value:** The only open-source, model-agnostic, agentic video editing system that goes from raw footage to published short-form content with TikTok-level granularity. The agent thinks and acts in **Remotion primitives** -- every editing decision is a direct Remotion operation that builds a composition incrementally. Powered by Qwen3.5-397B-A17B's dense per-second video understanding with edit signals, spatial bounding boxes, emotional arc, and energy curves. Driven by a natural-language style prompt. Fully observable via NeMo Agent Toolkit.
