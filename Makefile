# ─── Auto-Vid Makefile ────────────────────────────────────────────────
# Cross-platform reproducible setup (Linux / macOS / Windows WSL)
#
# Usage:
#   make setup       — Full first-time setup (venv + deps + infra + frontend)
#   make dev         — Start backend + frontend for development
#   make infra       — Start infrastructure only (Postgres, Redis, MinIO, Phoenix)
#   make test        — Run Python tests
#   make lint        — Run linter + type checker
#   make clean       — Remove venv + build artifacts
#
# Requirements:
#   - Python 3.11+ (pyenv, system, or deadsnakes)
#   - Docker + Docker Compose
#   - Node.js 20+ / npm

SHELL := /bin/bash
.DEFAULT_GOAL := help

# ─── Config ───────────────────────────────────────────────────────────
PYTHON     := python3
VENV       := .venv
BIN        := $(VENV)/bin
PIP        := $(BIN)/pip
PYTHON_BIN := $(BIN)/python
UV         := $(shell command -v uv 2>/dev/null)

# Detect OS for activation path
ifeq ($(OS),Windows_NT)
    BIN := $(VENV)/Scripts
    PIP := $(BIN)/pip.exe
    PYTHON_BIN := $(BIN)/python.exe
endif

# ─── Help ─────────────────────────────────────────────────────────────
.PHONY: help
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

# ─── Full Setup ───────────────────────────────────────────────────────
.PHONY: setup
setup: venv install env infra frontend-install sandbox-build ## Full first-time setup
	@echo ""
	@echo "✅ Setup complete. Run 'make dev' to start developing."

# ─── Python Virtual Environment ──────────────────────────────────────
.PHONY: venv
venv: ## Create Python virtual environment
	@if [ ! -d "$(VENV)" ]; then \
		echo "Creating virtual environment..."; \
		$(PYTHON) -m venv $(VENV); \
		echo "Virtual environment created at $(VENV)/"; \
	else \
		echo "Virtual environment already exists."; \
	fi

# ─── Install Python Dependencies ─────────────────────────────────────
.PHONY: install
install: venv ## Install Python dependencies into venv
	@echo "Installing Python dependencies..."
ifdef UV
	@echo "Using uv (fast)..."
	$(UV) pip install -e ".[dev]" --python $(PYTHON_BIN)
else
	$(PIP) install --upgrade pip setuptools wheel
	$(PIP) install -e ".[dev]"
endif
	@echo "Python dependencies installed."

# ─── Environment File ────────────────────────────────────────────────
.PHONY: env
env: ## Copy .env.example to .env if missing
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "Created .env from .env.example"; \
	else \
		echo ".env already exists, skipping."; \
	fi

# ─── Infrastructure (Docker) ─────────────────────────────────────────
.PHONY: infra
infra: ## Start Postgres, Redis, MinIO, Phoenix via Docker Compose
	docker compose up -d postgres redis minio minio-init phoenix
	@echo "Waiting for services to be healthy..."
	@docker compose exec postgres pg_isready -U autovid -q && echo "Postgres: ready" || true
	@echo "Infrastructure running."
	@echo "  Postgres:  localhost:5432"
	@echo "  Redis:     localhost:6379"
	@echo "  MinIO:     localhost:9000  (console: localhost:9001)"
	@echo "  Phoenix:   localhost:6006"

.PHONY: infra-down
infra-down: ## Stop infrastructure
	docker compose down

.PHONY: infra-reset
infra-reset: ## Stop infrastructure and delete volumes
	docker compose down -v

# ─── Sandbox Image ────────────────────────────────────────────────────
.PHONY: sandbox-build
sandbox-build: ## Build the autovid-sandbox Docker image
	docker compose build sandbox-build

# ─── Frontend ─────────────────────────────────────────────────────────
.PHONY: frontend-install
frontend-install: ## Install frontend npm dependencies
	cd frontend && npm install

# ─── Development ──────────────────────────────────────────────────────
.PHONY: dev
dev: ## Start backend (uvicorn) + frontend (next dev) in parallel
	@echo "Starting backend on :8080 and frontend on :3000..."
	@trap 'kill 0' EXIT; \
		$(PYTHON_BIN) -m uvicorn autovid.api.app:app --port 8080 --reload & \
		cd frontend && npm run dev & \
		wait

.PHONY: backend
backend: ## Start backend only
	$(PYTHON_BIN) -m uvicorn autovid.api.app:app --port 8080 --reload

.PHONY: frontend
frontend: ## Start frontend only
	cd frontend && npm run dev

# ─── Quality ──────────────────────────────────────────────────────────
.PHONY: test
test: ## Run Python tests
	$(PYTHON_BIN) -m pytest tests/ -v

.PHONY: lint
lint: ## Run ruff linter + mypy type checker
	$(BIN)/ruff check src/
	$(BIN)/ruff format --check src/

.PHONY: format
format: ## Auto-format code
	$(BIN)/ruff check --fix src/
	$(BIN)/ruff format src/

.PHONY: typecheck
typecheck: ## Run mypy
	$(BIN)/mypy src/autovid/

# ─── Docker Full Stack ────────────────────────────────────────────────
.PHONY: docker-up
docker-up: ## Start everything in Docker (infra + backend)
	docker compose up -d --build

.PHONY: docker-down
docker-down: ## Stop everything
	docker compose down

# ─── Cleanup ──────────────────────────────────────────────────────────
.PHONY: clean
clean: ## Remove venv, build artifacts, caches
	rm -rf $(VENV) build/ dist/ *.egg-info src/*.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	@echo "Cleaned."
