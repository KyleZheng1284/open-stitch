# Dev Setup

## Prerequisites

- Python 3.11+, Node.js 20+, Docker

## Infrastructure

```bash
cp .env.example .env
docker compose up -d postgres redis minio minio-init phoenix
docker compose build sandbox-build
```

## Backend

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn autovid.api.app:app --port 8080 --reload
```

## Frontend

```bash
cd frontend
npm install
npm run dev
```

## Ports

| Service  | Port |
|----------|------|
| Frontend | 3000 |
| Backend  | 8080 |
| Postgres | 5432 |
| Redis    | 6379 |
| MinIO    | 9000 |
| Phoenix  | 6006 |
