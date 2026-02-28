# Open-Stitch Tunnel Guide

Single source of truth for sharing your relay and backend with teammates.

## Context Table

| Context | Who | Purpose | What They Run | What They Need |
|---|---|---|---|---|
| Host Operator | You | Run relay/backend and expose via Cloudflare tunnel | `uvicorn server.main:app`, `uvicorn relay.main:app`, `cloudflared tunnel ...` | `.env`, `.env.relay`, provider API key, relay token |
| Teammate Consumer | Teammates | Call hosted endpoints from their own frontend/client | `curl` or app requests to your tunneled URLs | Relay base URL, backend base URL, shared relay token |

## Quick Access

| Need | Link |
|---|---|
| Host setup + run services | [Section A: Host Operator](#section-a-host-operator-you) |
| Quick Tunnel (fast test) | [Option A: Quick Tunnel](#4-option-a-quick-tunnel-fast-testing) |
| Named Tunnel (stable domain) | [Option B: Named Tunnel](#5-option-b-named-tunnel-stable-domain) |
| Teammate env + usage | [Section B: Teammates](#section-b-teammates-consumers) |
| Teammate test commands | [Teammate test commands](#7-teammate-test-commands) |

## Section A: Host Operator (You)

Everything in this section is only for the person hosting relay/backend on the machine.

## 1) What this provides

- `llm-relay` endpoint for OpenAI-compatible model calls.
- `open-stitch-api` endpoint for full backend processing (upload -> ingest -> edit -> render).
- Sandbox/Remotion stays private on your machine and is never exposed directly.

No extra refactor is required for this flow.

## 2) Prerequisites on host machine

- Conda env `openstitch` with dependencies installed.
- Relay config file set up:

```bash
cd /Users/cuhackit/Documents/GitHub/open-stitch
cp .env.relay.example .env.relay
```

Set in `.env.relay`:
- `RELAY_SHARED_TOKEN=<long-random-secret>`
- `UPSTREAM_API_KEY=<provider-key>` (or keep `NVIDIA_API_KEY` in `.env`)
- optional: `UPSTREAM_BASE_URL` (or keep `NVIDIA_BASE_URL` in `.env`)

## 3) Start host services

Terminal A (backend):

```bash
cd /Users/cuhackit/Documents/GitHub/open-stitch
source "$HOME/miniforge3/bin/activate"
conda activate openstitch
uvicorn server.main:app --host 127.0.0.1 --port 8080
```

Terminal B (relay):

```bash
cd /Users/cuhackit/Documents/GitHub/open-stitch
source "$HOME/miniforge3/bin/activate"
conda activate openstitch
uvicorn relay.main:app --host 127.0.0.1 --port 8090
```

## 4) Option A: Quick Tunnel (fast testing)

Terminal C:

```bash
cloudflared tunnel --url http://127.0.0.1:8090
```

Use the printed URL:
- Relay base URL: `https://<random>.trycloudflare.com/v1`

Notes:
- URL changes each restart.
- Keep terminal C running.

## 5) Option B: Named Tunnel (stable domain)

Use this once your Cloudflare zone is active (nameservers switched).

```bash
cloudflared tunnel login
cloudflared tunnel create llm-relay
mkdir -p ~/.cloudflared
cp relay/cloudflared/config.fullstack.example.yml ~/.cloudflared/config.yml
```

Edit `~/.cloudflared/config.yml`:
- set `tunnel` ID and `credentials-file` from create output
- set hostnames:
  - `llm-relay.<your-domain>` -> `http://127.0.0.1:8090`
  - `open-stitch-api.<your-domain>` -> `http://127.0.0.1:8080`

Route DNS:

```bash
cloudflared tunnel route dns llm-relay llm-relay.<your-domain>
cloudflared tunnel route dns llm-relay open-stitch-api.<your-domain>
cloudflared tunnel run llm-relay
```

---

## Section B: Teammates (Consumers)

Everything in this section is for teammates who call your hosted endpoints.

## 6) Teammate setup

Teammates copy:

```bash
cp TEAM_CLIENT.env.example .env.team
```

Set:
- `LLM_RELAY_BASE_URL=https://llm-relay.<your-domain>/v1` (or quick tunnel URL + `/v1`)
- `LLM_RELAY_API_KEY=<RELAY_SHARED_TOKEN>`
- `OPEN_STITCH_API_BASE_URL=https://open-stitch-api.<your-domain>`
- `OPEN_STITCH_WS_BASE_URL=wss://open-stitch-api.<your-domain>`

## 7) Teammate test commands

Relay models:

```bash
curl "$LLM_RELAY_BASE_URL/models" \
  -H "Authorization: Bearer $LLM_RELAY_API_KEY"
```

Relay chat:

```bash
curl "$LLM_RELAY_BASE_URL/chat/completions" \
  -H "Authorization: Bearer $LLM_RELAY_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"gcp/google/gemini-3-pro","messages":[{"role":"user","content":"ping"}],"stream":false}'
```

Backend health:

```bash
curl "$OPEN_STITCH_API_BASE_URL/health"
```

## 8) Security boundary

- Public via tunnel:
  - Relay `:8090`
  - Backend `:8080`
- Private only:
  - Sandbox API `:9876`
  - Upstream provider keys
  - Host `.env`/`.env.relay`
