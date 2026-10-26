# TraceHarbor — Local Development & Setup Guide

This guide describes how to configure, run, and test TraceHarbor on a local workstation.

---

## 1. Prerequisites

Ensure your system has the following tools installed:

| Tool | Minimum Version | Recommended Version | Purpose |
| :--- | :--- | :--- | :--- |
| **Python** | 3.11 | 3.11 or 3.12 | Backend API, SDK, and evaluation engine |
| **Node.js** | 20.x LTS | 20.14+ | Next.js dashboard and TypeScript compiler |
| **Docker Engine** | 24.x | Latest Docker Desktop | PostgreSQL 16 with pgvector and Redis |
| **Git** | 2.30+ | Latest | Version control |

---

## 2. Quick Start: Local In-Memory Mode (Zero Docker Needed)

TraceHarbor is designed to be fully testable and runnable locally even if Docker is not currently running.

### 1. Clone & Set Up Backend Environment
```bash
git clone https://github.com/priyanshu150106/TraceHarbor---AI-AGENT-INTELLIGENCE-PLATFORM.git
cd TraceHarbor

# Create and activate Python virtual environment
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

# Install backend API dependencies in editable mode
pip install -e "apps/api[test,dev]"

# Install Python SDK in editable mode
pip install -e "packages/sdk-python[dev]"
```

### 2. Configure Environment Variables
Copy the development environment template:
```bash
cp apps/api/.env.example apps/api/.env
```
Default configuration values:
- `DEBUG=true` (enables developer fallback for local testing)
- `EMBEDDING_PROVIDER=fake` (runs deterministic local vector embeddings without third-party API keys)
- `LOG_LEVEL=info`

### 3. Run Backend API Server
```bash
cd apps/api
uvicorn app.main:app --reload --port 8000
```
API endpoints will be live at `http://127.0.0.1:8000`:
- Interactive Swagger UI: `http://127.0.0.1:8000/docs`
- Health check: `http://127.0.0.1:8000/health`
- Liveness probe: `http://127.0.0.1:8000/healthz`
- Readiness probe: `http://127.0.0.1:8000/readyz`

### 4. Run Frontend Dashboard
In a separate terminal:
```bash
cd apps/web
npm install
npm run dev
```
Dashboard will be live at `http://localhost:3000`.

---

## 3. Production Infrastructure Mode (Docker Compose)

To run the complete production-grade architecture (PostgreSQL 16 with `pgvector` and Redis 7):

```bash
# Start all 4 containerized services
docker compose up --build -d

# Verify container health
docker compose ps

# View backend logs
docker compose logs -f api
```

The stack exposes:
- **Web UI**: `http://localhost:3000`
- **FastAPI Backend**: `http://localhost:8000`
- **PostgreSQL (pgvector)**: Bound to `127.0.0.1:5432`
- **Redis**: Bound to `127.0.0.1:6379`

---

## 4. Database Migrations (Alembic)

When running against real PostgreSQL, migrations manage schema changes idempotently.

```bash
cd apps/api

# Apply all pending migrations to head
alembic upgrade head

# Check current migration status
alembic current

# Create a new corrective migration
alembic revision -m "add_new_feature_table"
```

Migration history:
- `001_initial_schema`: Base tables (users, projects, api_keys, runs, spans, alerts) & pgvector extension
- `002_phase3_evaluations`: Golden datasets, test cases, experiments, evaluator results
- `003_phase4_analytics_alerts`: Metric aggregates, alert history, notification channels
- `004_phase5_safety`: Adversarial safety datasets, red-team campaigns, safety test results
- `005_phase6_failure_intelligence`: Normalized failure events, persistent vector clusters, triage audit log

---

## 5. Automated Verification & Testing Commands

### Backend Quality Checks
```bash
# Linting & import sorting
ruff check apps/api/app

# Fast in-memory unit & API tests (113 tests)
pytest apps/api/app/tests -v -m "not integration"

# PostgreSQL & pgvector integration tests (requires Docker/PostgreSQL)
pytest apps/api/app/tests -v -m "integration"
```

### Python SDK Quality Checks
```bash
pytest packages/sdk-python/tests -v
```

### Frontend Quality Checks
```bash
cd apps/web

# TypeScript typechecking
npm run typecheck

# Next.js ESLint linting
npm run lint

# Production bundle compilation
npm run build
```

### End-to-End Demonstration Script
```bash
# Runs the full 8-step lifecycle walkthrough in-process
python scripts/demo_walkthrough.py --in-memory

# Or against a running local or staging server
python scripts/demo_walkthrough.py --base-url http://127.0.0.1:8000
```
