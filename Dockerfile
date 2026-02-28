FROM python:3.11-slim AS base

WORKDIR /app

# System dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ffmpeg \
        libpq-dev \
        gcc \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY pyproject.toml ./
RUN pip install --no-cache-dir -e ".[dev]" 2>/dev/null || pip install --no-cache-dir .

# Application code
COPY src/ ./src/
COPY config/ ./config/

EXPOSE 8080

CMD ["uvicorn", "autovid.api.app:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "4"]
