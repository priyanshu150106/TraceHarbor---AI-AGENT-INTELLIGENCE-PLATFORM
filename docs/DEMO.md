# TraceHarbor — Technical Demonstration & Validation Guide

This guide provides end-to-end instructions for running, evaluating, and demonstrating the TraceHarbor platform.

TraceHarbor is an open, production-grade AI Agent Observability, Evaluation, Safety, Alerting, and Failure-Intelligence platform designed for multi-step agent reasoning pipelines.

---

## 1. Quick Verification (Automated 9-Step Walkthrough)

To verify all subsystems end-to-end in isolated memory without external cloud accounts or third-party API keys:

```bash
# Clone the repository
git clone https://github.com/priyanshu150106/TraceHarbor---AI-AGENT-INTELLIGENCE-PLATFORM.git
cd TraceHarbor

# Run the complete 9-step automated verification suite
python scripts/demo_walkthrough.py --in-memory
```

### What This Validates
1. **Health & Readiness Probes**: Liveness (`/healthz`), Readiness (`/readyz`), and Service Health (`/health`).
2. **Telemetry Ingestion & Span Hierarchy**: DAG span validation, parent-child nesting (`chain` &rarr; `tool`, `chain` &rarr; `llm`), error telemetry capture, and client-side PII redaction.
3. **Agent Regression Testing & Evaluation**: Golden dataset creation with test cases, baseline (`v1.0`) vs candidate (`v2.0-improved`) experiment execution, per-case result scoring, and automated regression alignment.
4. **Adversarial Safety Red-Teaming**: Multi-category adversarial evaluation (prompt injection refusal, canary secret leakage prevention) with comparative pass-rate analysis.
5. **Failure Event Synchronization & Redaction**: Automatic extraction of failure events from error traces, normalized error summaries, and multi-pattern credential scrubbing.
6. **Semantic Failure Clustering & Triage**: Cluster grouping with cosine/lexical similarity, triage status progression (`new` &rarr; `investigating` &rarr; `resolved`) with persistent audit notes, and similarity search.
7. **Alert Rules, Evaluation & Security**: Multi-metric alert rules (`error_rate`, `safety_critical_failures`), evaluation engine, cooldown suppression, and SSRF prevention.
8. **Asynchronous Background Tasks**: In-process task submission, status polling, and graceful lifecycle handling.
9. **Multi-Tenant Security Boundaries**: Cross-tenant isolation verification and unauthorized request rejection (HTTP 401/403).

---

## 2. Prerequisites & Environment Setup

### Prerequisites
- **Python**: 3.11 or higher
- **Node.js**: 18.x or 20.x
- **Docker & Docker Compose** (Optional for containerized PostgreSQL/pgvector & Redis; when Docker is unavailable, the in-memory/SQLite mode is supported for local validation)

### Environment Configuration
Copy the safe template configuration:
```bash
cp .env.example .env
```

Key environment variables:
| Variable | Description | Safe Demo Default |
| :--- | :--- | :--- |
| `DATABASE_URL` | PostgreSQL async connection string | `postgresql+asyncpg://th:change_me_in_production@localhost:5432/traceharbor` |
| `REDIS_URL` | Redis connection URL | `redis://localhost:6379/0` |
| `JWT_SECRET` | Secret key for signing tokens | `change_me_generate_a_random_secret` |
| `DEBUG` | Enable debug logging & detailed errors | `true` (dev) / `false` (prod) |
| `LOG_LEVEL` | Log verbosity | `INFO` |
| `EMBEDDING_PROVIDER` | Embedding model provider | `fake` (deterministic mock vectors) or empty |
| `NEXT_PUBLIC_API_BASE_URL` | Frontend API target | `http://localhost:8000` |

---

## 3. Interactive Hands-On Demonstration

### Step 1: Start Services

#### Option A: Docker Compose (Full Stack with PostgreSQL 16 + pgvector)
```bash
docker compose up --build -d
docker compose ps
```

#### Option B: Standalone Local Processes
Terminal 1 (Backend API):
```bash
cd apps/api
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Terminal 2 (Frontend Dashboard):
```bash
cd apps/web
npm run dev
```

Open your browser to `http://localhost:3000`.

### Step 2: Health Probes Verification
Verify service health:
```bash
# Liveness probe (fast, no external dependencies)
curl http://localhost:8000/healthz

# Readiness probe (verifies database connectivity)
curl http://localhost:8000/readyz

# Service health
curl http://localhost:8000/health
```

### Step 3: Run the Sample Support Agent
TraceHarbor includes a deterministic customer support agent (`demo-agents/support_agent.py`) instrumented with the TraceHarbor Python SDK (`@traceharbor.trace`, `traceharbor.span`).

```bash
# 1. Normal execution (generates clean trace waterfall)
python demo-agents/support_agent.py --query "What is the return policy?"

# 2. Simulated tool error (generates error span for failure clustering)
python demo-agents/support_agent.py --simulate-error
```

### Step 4: Inspect Traces in the Web Dashboard
1. Open `http://localhost:3000/runs`.
2. Inspect the latest `support_agent` execution:
   - Click to open the **Trace Waterfall Visualizer**.
   - Review root `chain` span and child `tool` (`knowledge_base_search`) and `llm` (`llm_response_synthesis`) spans.
   - Inspect duration, token counts, simulated cost, and inputs/outputs.
3. Open the failed run to inspect captured error stack traces and error metadata.

### Step 5: Execute an Evaluation Experiment
1. Navigate to **Experiments** (`http://localhost:3000/experiments`).
2. Run a regression benchmark between `support_agent` version `1.0` and `2.0-improved`.
3. Open **Regression Comparison** (`http://localhost:3000/experiments/compare`):
   - Review aligned per-case outcomes by immutable test-case ID.
   - Inspect regressions, improvements, and score deltas.

### Step 6: Execute an Adversarial Safety Campaign
1. Navigate to **Safety** (`http://localhost:3000/safety`).
2. Run a safety campaign against the golden adversarial dataset (`datasets/safety_redteam_benchmark.json`).
3. Inspect category metrics:
   - **Prompt Injection Resistance**: Automated refusal verification.
   - **Sensitive Data Protection**: Canary value detection and secret masking.
4. Review comparative safety analysis (`http://localhost:3000/safety/compare`).

### Step 7: Inspect Failure Intelligence & Triage
1. Navigate to **Failure Intelligence** (`http://localhost:3000/failures`).
2. Trigger **Sync Failures** to scan error traces and extract sanitized failure events.
3. Open **Failure Clusters** (`http://localhost:3000/failures/clusters`):
   - Review automatically grouped clusters.
   - Open a cluster detail view, inspect representative evidence, and update investigation triage status (`new` &rarr; `investigating` &rarr; `resolved`) with resolution notes.
4. Use **Similar Failure Search** (`http://localhost:3000/failures/search`) to search for matching failure patterns.

### Step 8: Validate Alerting & Webhook Security
1. Navigate to **Alerts** (`http://localhost:3000/alerts`).
2. Configure an alert rule (e.g. `metric="error_rate"`, `operator=">"`, `threshold=0.05`).
3. Evaluate the rule to confirm firing behavior and cooldown suppression.
4. Note that SSRF protection automatically prevents webhooks targeting private IPs or cloud instance metadata (`169.254.169.254`).

---

## 4. Troubleshooting Common Startup Issues

| Symptom | Root Cause | Resolution |
| :--- | :--- | :--- |
| `curl: (7) Failed to connect to localhost:8000` | Backend API not started | Run `python -m uvicorn app.main:app --port 8000` in `apps/api`. |
| `/readyz returns HTTP 503` | Database unreachable | Check `DATABASE_URL` or run in-memory test mode via `scripts/demo_walkthrough.py --in-memory`. |
| `TypeError: 'evaluator_names'` | Outdated model schema | Ensure model definitions align with `apps/api/app/models`. |
| `Form data requires python-multipart` | Missing multipart package | Ensure `python-multipart>=0.0.9` is installed in the environment. |
| `Docker not found` | Docker daemon not installed/running | Use standalone Python and Node.js processes or the automated in-memory suite. |

---

## 5. Architectural Trade-Offs & Known Limitations

1. **In-Process Background Task Manager**:
   - The built-in `BackgroundTaskManager` provides async task execution and bounded history tracking in memory.
   - *Limitation*: Tasks are in-process; if the API server restarts, in-flight background tasks are terminated. For multi-node high-availability production, a persistent distributed broker (e.g., Celery or Temporal) should back task dispatch.
2. **Dual-Mode Vector Search**:
   - When PostgreSQL with `pgvector` is available, cosine distance queries use native HNSW vector indexes.
   - When running on SQLite without vector extensions, the platform transparently falls back to lexical Jaccard similarity and warns that semantic clustering is simulated.
3. **LLM Judge Provider Flexibility**:
   - TraceHarbor defaults to deterministic local evaluator functions and mock judge mode to enable instant, zero-cost regression testing without requiring paid OpenAI or Anthropic API keys.

---

## 6. End-to-End Demo Checklist

| Check | Expected Visible Outcome | Verified |
| :--- | :--- | :---: |
| **Health Liveness** | `GET /healthz` returns `{"status":"alive"}` (HTTP 200) | `[x]` |
| **Health Readiness** | `GET /readyz` returns `{"status":"ready","checks":{"database":"ok"}}` | `[x]` |
| **Telemetry Ingestion** | `POST /v1/ingest/spans` returns `{"ingested_runs":1,"ingested_spans":3}` | `[x]` |
| **Waterfall Visualizer** | UI displays root chain span and nested tool/llm children | `[x]` |
| **Experiment Execution** | Evaluation returns pass rate and per-case results | `[x]` |
| **Regression Comparison**| Candidate vs baseline aligns cases and shows score delta | `[x]` |
| **Safety Red-Teaming** | Prompt injection refusal and canary protection scored | `[x]` |
| **Failure Synchronization**| Failure events extracted with sensitive credentials scrubbed | `[x]` |
| **Cluster Triage** | Investigation status transitions persist with resolution notes | `[x]` |
| **Alert Cooldown** | Second evaluation within cooldown window is suppressed | `[x]` |
| **SSRF Webhook Block** | Webhook URLs targeting private/loopback IPs are rejected | `[x]` |
| **Task Management** | Background tasks track progress and appear in `/v1/tasks` | `[x]` |
| **Tenant Isolation** | Unauthorized API key receives HTTP 401 or 403 | `[x]` |
