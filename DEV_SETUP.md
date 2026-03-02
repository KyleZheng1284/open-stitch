# Dev Setup

## Prerequisites

- Python 3.11+, Node.js 20+, Docker, FFmpeg
- Google Cloud OAuth credentials (Drive API enabled)
- Google API key (Gemini models) and/or Azure API key (OpenAI models)

## 1. Infrastructure

```bash
cp .env.example .env
# Fill in GOOGLE_API_KEY, AZURE_API_KEY, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET
docker compose up -d postgres redis minio minio-init phoenix
```

## 2. Backend

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn server.main:app --port 8080 --reload
```

## 3. Frontend

```bash
cd client
npm install
npm run dev
```

## 4. Test ingestion (no frontend)

```bash
python tools/test_ingestion.py data/your_video.mp4
```

## Ports

| Service  | Port |
|----------|------|
| Frontend | 5173 |
| Backend  | 8080 |
| Postgres | 5432 |
| Redis    | 6379 |
| MinIO    | 9000 |
| Phoenix  | 6006 |
