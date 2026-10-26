# Multi-stage production Dockerfile for TraceHarbor API
# Stage 1: Build dependencies
FROM python:3.11-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
COPY pyproject.toml .
RUN pip install --no-cache-dir --prefix=/install .

# Stage 2: Runtime image
FROM python:3.11-slim AS runner

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Run as non-privileged service user
RUN useradd -m -u 10001 -s /bin/bash appuser

WORKDIR /app

# Copy installed python dependencies from builder
COPY --from=builder /install /usr/local

# Copy application code and database migration definitions
COPY alembic.ini .
COPY alembic/ ./alembic/
COPY app/ ./app/

RUN chown -R appuser:appuser /app

USER appuser

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/healthz || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
