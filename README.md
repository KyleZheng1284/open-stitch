# Open-Stitch (Auto-Vid)

AI-powered video editing from Google Drive. Select videos, describe your vision, get an edited video back.

Built with FastAPI, Vite + React, Remotion, Gemini 3 Pro, and Whisper.

---

## How It Works

```
Screen 0: Login with Google
Screen 1: Select mp4s from Drive → download → Flash Lite summary (2 FPS)
Screen 2: Reorder clips + answer clarifying questions → structured prompt
Screen 3: Watch pipeline progress (ASR + VLM + edit plan + Remotion render)
Screen 4: Review and download final video
```

Graph-managed agents:
- **Planning** → intent brief
- **Research** → evidence-backed findings
- **Clarification** → user question set
- **User Verification** → approved structured prompt
- **Synthesis** → edit spec
- **Remotion Synthesis** → timeline draft
- **Editing Synthesis** → composition payload
- **Internal Verification** → deterministic checks + retry target
- **Final QA** → render gate (`qa_passed`)

Legacy clarify/edit flows are still available as immediate fallback.

---

## Prerequisites

- Python 3.11+
- Node.js 20+
- Docker (for Postgres, Redis, MinIO, sandbox)
- FFmpeg installed locally
- Google Cloud project with OAuth credentials and Drive API enabled
- Google API key (for Gemini models) and/or Azure API key (for OpenAI models)

---

## Setup

### 1. Clone and configure

```bash
cp .env.example .env
```

Fill in `.env`:
```
GOOGLE_API_KEY=your-google-api-key
GOOGLE_BASE_URL=https://...
AZURE_API_KEY=your-azure-api-key
AZURE_BASE_URL=https://...
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
```

### 2. Start infrastructure

```bash
docker compose up -d postgres redis minio minio-init phoenix
```

### 3. Backend

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Run the server:
```bash
uvicorn server.main:app --port 8080 --reload
```

Verify: `curl http://localhost:8080/health` should return `{"status":"ok"}`

### 4. Frontend

```bash
cd client
npm install
npm run dev
```

Open http://localhost:5173

### 5. Sandbox (for Remotion rendering)

```bash
docker compose build sandbox-build
```

### 6. Team Inference Relay (optional)

Use this when teammates should call one shared OpenAI-compatible endpoint that forwards to your configured inference base URL.

```bash
cp .env.relay.example .env.relay
source .venv/bin/activate
uvicorn relay.main:app --host 127.0.0.1 --port 8090
```

Endpoints:
- `GET /health`
- `GET /v1/models` (Bearer token required)
- `POST /v1/chat/completions` (Bearer token required, stream + non-stream)

Cloudflare relay/backend setup: `TUNNEL_GUIDE.md`
Teammate env template: `TEAM_CLIENT.env.example`

---

## Graph Orchestration and Rollback

Environment flags:

- `GRAPH_ENABLED=false`
  - `false`: always use legacy clarify/edit route handlers.
  - `true`: use LangGraph orchestration for clarify/edit.
- `GRAPH_FAIL_OPEN=true`
  - `true`: if graph execution fails, fallback to legacy.
  - `false`: fail closed (no fallback).
- `GRAPH_MAX_STEPS=32`
  - Max recursion budget for graph execution.
- `GRAPH_EMIT_NODE_EVENTS=true`
  - Emit graph gate/state events into trace stream.

Immediate rollback:

```bash
export GRAPH_ENABLED=false
```

No code changes are required for rollback.

Migration path:

1. Ship with `GRAPH_ENABLED=false` to keep legacy clarify/edit behavior.
2. Enable graph in one environment: `GRAPH_ENABLED=true`, `GRAPH_FAIL_OPEN=true`.
3. Validate traces and outputs, then disable fail-open for strict mode: `GRAPH_FAIL_OPEN=false`.
4. If issues appear, revert immediately with `GRAPH_ENABLED=false`.

---

## Test the Ingestion Pipeline (no frontend needed)

The test script runs the full ASR + VLM + summary pipeline on a local video:

```bash
source .venv/bin/activate
python tools/test_ingestion.py data/your_video.mp4 --fps 4 --window 5
```

This runs:
1. Frame extraction (dense @ 4 FPS + summary @ 2 FPS) + audio extraction — parallel
2. Whisper ASR + Gemini VLM + Flash Lite summary — parallel
3. Merged ASR+VLM timeline
4. Edit plan generation via Gemini 3 Pro

---

## Test and QA

One command to validate graph + legacy paths:

```bash
./tools/test_all.sh
```

Equivalent make target:

```bash
make test-ci
```

Individual commands:

```bash
python3 -m ruff check server/graph server/agents/tools.py tests
python3 -m mypy --config-file mypy.graph.ini
python3 -m pytest -q tests
```

---

## Test the Backend API

Start the server, then:

```bash
# Health check
curl http://localhost:8080/health

# Auth (requires Google OAuth flow — use the frontend for this)

# Or test directly with a Bearer token:
curl -H "Authorization: Bearer YOUR_GOOGLE_TOKEN" \
  http://localhost:8080/api/drive/files
```

---

## Project Structure

```
auto-vid/
├── client/              Vite + React SPA
│   └── src/
│       ├── pages/       Login, Select, Setup, Progress, Review
│       ├── components/  VideoCard, ClarifyChat, ProgressTimeline
│       ├── hooks/       useDrive, useProject, useSocket
│       └── lib/api.ts   REST + WebSocket client
│
├── server/              FastAPI Python backend
│   ├── main.py          App entry point
│   ├── config.py        Settings + YAML loaders
│   ├── graph/           LangGraph orchestration, nodes, validators
│   ├── routes/          auth, drive, projects, jobs
│   ├── agents/          clarifying.py, editing.py
│   ├── ingestion/       pipeline.py, asr.py, vlm.py, summary.py
│   ├── drive/           Google OAuth + Drive API client
│   ├── sandbox/         Docker container management + HTTP client
│   ├── schemas/         project.py, video.py, composition.py
│   └── storage/         db.py (Postgres), objects.py (MinIO)
│
├── sandbox/             Remotion Docker image (sandbox-server.js)
├── config/              YAML configs (models, agents, prompts)
├── docs/                Graph event taxonomy + developer guide
├── tools/               Dev scripts (test_ingestion.py)
└── docker-compose.yaml  Postgres, Redis, MinIO, Phoenix
```

---

## Ports

| Service  | Port |
|----------|------|
| Frontend | 5173 |
| Backend  | 8080 |
| Postgres | 5432 |
| Redis    | 6379 |
| MinIO    | 9000 |
| Phoenix  | 6006 |

---

## Configuration

All model and pipeline settings are in `.env` and `config/`:

| Setting | File | Purpose |
|---------|------|---------|
| `GOOGLE_API_KEY` | `.env` | Google API key (Gemini models) |
| `AZURE_API_KEY` | `.env` | Azure API key (OpenAI models) |
| `VLM_MODEL` | `.env` | Dense VLM model (default: Gemini 3 Pro) |
| `SUMMARY_MODEL` | `.env` | Fast summary model (default: Gemini 2.5 Flash Lite) |
| `SUMMARY_FPS` | `.env` | Summary frame rate (default: 2) |
| `ASR_MODEL` | `.env` | Whisper model size |
| `GOOGLE_CLIENT_ID` | `.env` | Google OAuth client ID |
| `config/models.yaml` | config | Model endpoints and parameters |
| `config/agents.yaml` | config | Agent and ingestion settings |
| `config/prompts/vlm_edit_grade.txt` | config | VLM system prompt |

Graph docs:

- `docs/GRAPH_EVENT_TAXONOMY.md`
- `docs/GRAPH_DEVELOPER.md`

---

## Debugging Workflow

1. Open `/progress/:projectId` to inspect trace graph.
2. Confirm node lifecycle events (`agent.start`, `agent.end`).
3. Inspect gate transitions (`graph.gate`) and state snapshots (`graph.state`).
4. If graph execution fails:
   - with `GRAPH_FAIL_OPEN=true`, verify legacy fallback in logs.
   - with `GRAPH_FAIL_OPEN=false`, inspect verification report and raised error.
5. For loop issues, inspect `next_node` chosen by internal verification.
