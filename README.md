# TraceHarbor

> **Observe. Evaluate. Secure.**

TraceHarbor is an open-source AI Agent Observability, Evaluation, and Security Platform. It enables developers and AI engineers to trace agent executions, inspect nested LLM and tool calls, measure token latency and costs, detect regressions with automated benchmark evaluations, and red-team agents against prompt injection and security vulnerabilities.

[![CI](https://github.com/priyanshu150106/TraceHarbor---AI-AGENT-INTELLIGENCE-PLATFORM/actions/workflows/ci.yml/badge.svg)](https://github.com/priyanshu150106/TraceHarbor---AI-AGENT-INTELLIGENCE-PLATFORM/actions)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-14-black.svg)](https://nextjs.org/)
[![CI](https://github.com/priyanshu150106/TraceHarbor---AI-AGENT-INTELLIGENCE-PLATFORM/actions/workflows/ci.yml/badge.svg)](https://github.com/priyanshu150106/TraceHarbor---AI-AGENT-INTELLIGENCE-PLATFORM/actions)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-14-black.svg)](https://nextjs.org/)
[![Tests](https://img.shields.io/badge/tests-73%20passed-brightgreen.svg)](#7-testing--quality-assurance)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

---

## 1. Dashboard Views

| View | Route | Description |
| :--- | :--- | :--- |
| **Overview Dashboard** | `/` | Operational KPIs: execution volume, success/error rates, avg/p95 latency, tokens, and cost. |
| **Runs Explorer** | `/runs` | Searchable, paginated agent run history with status filters and copyable IDs. |
| **Trace Waterfall** | `/runs/[id]` | Chronological waterfall timeline, hierarchical span trees, and inspector drawer. |
| **Advanced Analytics** | `/analytics` | Time-series charts, p50/p95 percentiles, model economics, agent comparisons, and cost attribution. |
| **Alerts & Monitoring** | `/alerts` | Configurable threshold rules, manual & automated evaluation, cooldown deduplication, and fired alert audit logs. |
| **Dataset Hub** | `/datasets` | Create, preview, and upload JSON/CSV golden datasets with structural validation. |
| **Experiment Hub** | `/experiments` | Execute benchmark evaluation runs against approved agent versions. |
| **Experiment Details** | `/experiments/[id]` | Per-case evaluation scorecard, pass/fail explanations, and linked trace waterfalls. |
| **Regression Diff Engine** | `/experiments/compare` | Side-by-side version comparison isolating regressions, improvements, and score deltas. |

---

## 2. Implementation Status

| Feature / Area | Status | Notes |
| :--- | :--- | :--- |
| **Phase 0: Monorepo Foundation** | Implemented & Verified | Branch, author identity, remote, and folder layout configured |
| **Phase 0: Backend Scaffolding** | Implemented & Tested | FastAPI app with `/health`, structured logging, and CORS |
| **Phase 0: Database Models** | Implemented & Tested | SQLAlchemy 2.0 models for users, projects, api_keys, runs, spans, alert rules, history |
| **Phase 0: Infrastructure Specs** | Implemented | Docker Compose for PostgreSQL 16 (pgvector) and Redis 7 |
| **Phase 1A: Trace Ingestion API** | Implemented & Tested | `POST /v1/ingest/spans` with API key auth, cycle detection, tenant isolation, and atomic batches |
| **Phase 1A: Python Tracing SDK** | Implemented & Tested | Client library with sync/async decorators, nested spans, redaction, queueing, retries, and kill-switch |
| **Phase 1A: Customer Support Demo Agent** | Implemented & Verified | Deterministic multi-step agent with tool calling and error telemetry |
| **Phase 2: Observability Dashboard** | Implemented & Tested | Next.js 14 App Router UI with Overview, Runs Explorer, Projects, Settings |
| **Phase 2: Trace Waterfall & Tree UI** | Implemented & Tested | Collapsible span hierarchy, relative timing bar charts, and span inspector panel |
| **Phase 2: Read APIs** | Implemented & Tested | `GET /v1/runs`, `GET /v1/runs/{id}`, `GET /v1/analytics/overview`, `GET /v1/projects` |
| **Phase 3: Dataset Management** | Implemented & Tested | JSON & CSV uploads, UTF-8 validation, size & case limits (5MB / 500 cases), and pagination |
| **Phase 3: Rule Evaluation Engine** | Implemented & Tested | 10 deterministic evaluators (regex with ReDoS protection, JSON schema, latency, tool calls) |
| **Phase 3: Safe Agent Adapter Registry** | Implemented & Tested | Explicit registry (V1 baseline, V2 improved, V0.9 buggy); zero arbitrary code execution |
| **Phase 3: Experiment Runner & Persistence** | Implemented & Tested | Async execution pipeline, Run & Span trace recording, per-case scoring, and aggregated metrics |
| **Phase 3: Regression Detection Engine** | Implemented & Tested | Side-by-side diffing aligned by `test_case_id`, delta metrics, regressions vs improvements |
| **Phase 3: Optional LLM-as-Judge** | Implemented & Tested | Provider-neutral evaluator (correctness, helpfulness, groundedness, tone) with mock fallback mode |
| **Phase 3: Web UI for Evaluation** | Implemented & Tested | Next.js pages `/datasets`, `/experiments`, `/experiments/[id]`, `/experiments/compare` |
| **Phase 4: Advanced Analytics Engine** | **Implemented & Tested** | Time-series bucketing with zero-padded intervals, p50/p95 latency percentiles, model breakdown, agent comparison |
| **Phase 4: Alerting & Monitoring Engine** | **Implemented & Tested** | Configurable rules (`error_rate`, `p95_latency_ms`, `total_cost`, `eval_pass_rate`), cooldown suppression |
| **Phase 4: SSRF-Safe Outbound Webhooks** | **Implemented & Tested** | Blocks localhost, private subnets, and cloud metadata (169.254.169.254); HMAC-SHA256 signature signing |
| **Phase 4: Web UI for Analytics & Alerts**| **Implemented & Tested** | Next.js interactive dashboards `/analytics` and `/alerts` |
| **Phase 5: Red-Team Campaigns** | *Planned (Upcoming)* | Adversarial prompt executor and vulnerability discovery metrics |
| **Phase 6: Failure Clustering** | *Planned* | Vector-based failure clustering via PostgreSQL pgvector |

---

## 3. Evaluation & Regression Testing Engine (Phase 3)

### 3.1 Golden Dataset Management
TraceHarbor allows engineering teams to manage golden test suites for evaluating AI agents:
- **Formats Supported:** JSON arrays and CSV tables.
- **Enforced Safeguards:**
  - Strict UTF-8 character encoding verification.
  - Maximum upload file size: **5 MB**.
  - Maximum test cases per dataset: **500 cases**.
  - Project tenant isolation: all datasets and cases are scoped strictly to the requesting project.
  - Uploaded files are parsed in-memory and committed via database transactions; no arbitrary code or SQL is ever executed.

#### Example JSON Dataset Format:
```json
[
  {
    "input": "What is your return policy?",
    "expected_output": "Returns are accepted within 30 days of purchase with receipt.",
    "criteria": {
      "required_keywords": ["30 days", "return"],
      "regex_pattern": "(?i)30\\s*days",
      "max_latency_ms": 2500
    },
    "tags": ["returns", "policy"]
  },
  {
    "input": "Can I cancel order #98765?",
    "expected_output": "Orders can be cancelled within 1 hour.",
    "criteria": {
      "required_keywords": ["cancel", "1 hour"],
      "required_tools": ["cancel_order"]
    },
    "tags": ["cancellation"]
  }
]
```

#### Equivalent CSV Dataset Format:
```csv
input,expected_output,required_keywords,regex_pattern,max_latency_ms,tags
"What is your return policy?","Returns are accepted within 30 days.","30 days;return","(?i)30\s*days",2500,"returns;policy"
"Can I cancel order #98765?","Orders can be cancelled within 1 hour.","cancel;1 hour",,2500,"cancellation"
```

A bundled golden dataset is provided in `datasets/support_agent_golden.json` and `datasets/support_agent_golden.csv`.

---

### 3.2 Rule-Based Evaluator Suite
Deterministic evaluators run 100% locally with zero external API calls or latency overhead:

1. **Exact Match (`exact_match`):** Binary check for exact character-for-character equality.
2. **Case-Insensitive Exact Match (`case_insensitive_exact_match`):** Case-folded string comparison.
3. **Required Keywords (`required_keywords`):** Checks whether all designated phrases appear in the output.
4. **Regex Match (`regex_match`):** Regular expression matching with length limits and input boundaries to guard against ReDoS (Regular Expression Denial of Service).
5. **JSON Valid (`json_valid`):** Validates that agent output contains well-formed JSON syntax.
6. **JSON Schema (`json_schema`):** Validates JSON structure and types against an arbitrary JSON Schema specification.
7. **Required Tool Call (`required_tool_call`):** Verifies that the agent invoked designated tools (e.g., `search_faq`, `cancel_order`) by inspecting recorded child spans.
8. **Latency Threshold (`latency_threshold`):** Checks that agent execution completed within a defined maximum millisecond threshold.
9. **Token / Cost Threshold (`token_cost_threshold`):** Validates that total tokens or estimated LLM cost stayed within budget.
10. **Output Presence (`output_presence`):** Confirms the agent generated non-empty, non-null responses.

---

### 3.3 Safe Agent Adapter Registry
To ensure production safety and guard against Remote Code Execution (RCE), TraceHarbor enforces an explicit **Agent Adapter Registry**. Arbitrary uploaded code or arbitrary Python imports are strictly prohibited:

| Registered Agent | Version | Description |
| :--- | :--- | :--- |
| `SupportAgent` | `1.0` | Baseline customer support agent with standard FAQ tool lookup. |
| `SupportAgent` | `2.0` | Improved support agent with comprehensive return, warranty, and escalation policies. |
| `SupportAgent` | `0.9-buggy` | Intentionally degraded agent for testing regression detection pipelines. |

---

### 3.4 Version Comparison & Regression Detection
TraceHarbor includes a dedicated comparison engine (`GET /v1/experiments/compare?a={baseline_id}&b={candidate_id}` or web route `/experiments/compare`):
- **Alignment:** Aligns individual test cases by immutable `test_case_id`.
- **Classification Categories:**
  - 🚨 **Regression:** A case that **PASSED** in the baseline experiment but **FAILED** in the candidate experiment.
  - ✨ **Improvement:** A case that **FAILED** in the baseline experiment but **PASSED** in the candidate experiment.
  - 🤝 **Unchanged:** Identical pass/fail outcome in both experiments.
  - ⚠️ **Evaluator Error:** Cases where execution or evaluation threw an unhandled exception.
  - 📋 **Missing:** Cases present in only one of the experiments.
- **Delta Scoring:** Computes pass rate delta ($\Delta \text{PassRate} = \text{PassRate}_B - \text{PassRate}_A$) and mean score differences.

---

### 3.5 Optional LLM-as-Judge Evaluator
TraceHarbor includes a provider-neutral LLM Judge evaluator (`llm_judge`) for qualitative assessments:
- **Supported Rubrics:** `correctness`, `helpfulness`, `groundedness`, and `tone`.
- **Provider Security:** Provider API keys (`OPENAI_API_KEY`) reside exclusively in server environment variables and are **never** exposed to the client browser.
- **Deterministic Mock Fallback:** When no provider key is configured (or during automated test execution), the evaluator defaults to a deterministic mock mode, guaranteeing that **no paid API calls are ever made during automated testing or setup**.
- **Important Note on LLM Judges:** LLM-as-a-judge evaluations can be subject to position bias, verbosity bias, and non-deterministic scoring variance. TraceHarbor recommends using deterministic rule-based evaluators as the primary regression gate, reserving LLM judges for advisory qualitative tracking.

---

### 3.6 Complete REST API Endpoint Reference

| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `GET` | `/health` | Service liveness & readiness check | No |
| `POST` | `/v1/ingest/spans` | Batch ingestion of agent execution spans | Yes (`X-API-Key`) |
| `GET` | `/v1/runs` | Paginated agent execution runs list | Optional / Tenant |
| `GET` | `/v1/runs/{id}` | Detailed trace waterfall with nested spans | Optional / Tenant |
| `GET` | `/v1/analytics/overview` | Aggregated operational metrics (latency, cost, runs) | Optional / Tenant |
| `GET` | `/v1/projects` | Project directory with recorded execution counts | Optional / Tenant |
| `POST` | `/v1/datasets` | Create a named dataset with test cases | Optional / Tenant |
| `GET` | `/v1/datasets` | List datasets for the authorized project | Optional / Tenant |
| `GET` | `/v1/datasets/{id}` | Retrieve dataset details and test cases | Optional / Tenant |
| `POST` | `/v1/datasets/{id}/cases` | Append test cases to an existing dataset | Optional / Tenant |
| `POST` | `/v1/datasets/upload` | Create dataset & import cases from CSV/JSON file | Optional / Tenant |
| `DELETE`| `/v1/datasets/{id}` | Delete a dataset and its test cases | Optional / Tenant |
| `GET` | `/v1/experiments/agents` | Directory of approved agent adapters and versions | Optional / Tenant |
| `POST` | `/v1/experiments` | Create and launch an evaluation experiment | Optional / Tenant |
| `GET` | `/v1/experiments` | List experiments with pass-rates and filters | Optional / Tenant |
| `GET` | `/v1/experiments/{id}` | Retrieve per-case experiment evaluation scorecards | Optional / Tenant |
| `GET` | `/v1/experiments/compare` | Compare baseline (A) vs candidate (B) experiments | Optional / Tenant |

---

## 4. Local Development & Startup Guide

### 4.1 Prerequisites
- **Python:** 3.11 or newer
- **Node.js:** 18 or newer (v20+ recommended) with `npm`
- **Git**
- **Docker Desktop** (Optional for containerized PostgreSQL/Redis; SQLite in-memory is used for all unit tests)

### 4.2 Step-by-Step Local Startup

#### 1. Start Backend API
```powershell
cd D:\TraceHarbor\apps\api
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
- API Base URL: `http://localhost:8000`
- Interactive Swagger Docs: `http://localhost:8000/docs`
- Health Check: `http://localhost:8000/health`

#### 2. Start Frontend Web Dashboard
```powershell
cd D:\TraceHarbor\apps\web
npm run dev
```
- Web Dashboard: `http://localhost:3000`
- Runs Explorer: `http://localhost:3000/runs`
- Dataset Hub: `http://localhost:3000/datasets`
- Experiment Hub: `http://localhost:3000/experiments`
- Version Comparison: `http://localhost:3000/experiments/compare`

#### 3. Run Your First Experiment Walkthrough

**Step A — Upload the Golden Dataset:**
1. Open `http://localhost:3000/datasets`.
2. Click **"Upload CSV/JSON"**.
3. Choose `D:\TraceHarbor\datasets\support_agent_golden.json` and enter a name (e.g. `Support Golden Suite`).
4. Click **"Upload and Import"**. 8 test cases will be validated and imported.

**Step B — Run the Baseline Experiment:**
1. Open `http://localhost:3000/experiments`.
2. Click **"Start Experiment"**.
3. Select `SupportAgent (v1.0)` and your uploaded dataset. Click **"Launch Experiment"**.
4. The test cases execute through the agent runner and are evaluated against all defined criteria.

**Step C — Run the Candidate Experiment:**
1. Click **"Start Experiment"** again.
2. Select `SupportAgent (v2.0)` and the same dataset. Click **"Launch Experiment"**.

**Step D — Compare Versions & Detect Regressions:**
1. Open `http://localhost:3000/experiments/compare`.
2. Select the `v1.0` run as Baseline (A) and the `v2.0` run as Candidate (B).
3. Click **"Run Comparison"**. The dashboard highlights pass-rate deltas, isolated improvements, and flags any regressions with side-by-side inputs, outputs, and evaluator explanations.

---

## 5. Advanced Analytics, Monitoring & Alerting (Phase 4)

### 5.1 Analytics Semantics & Aggregated Metrics
TraceHarbor computes operational and performance metrics across recorded runs, spans, and experiment test cases:

- **Total Runs:** Total execution count within the chosen time window (`24h`, `7d`, `30d`, `all`).
- **Success & Error Rates:** $\text{Error Rate} = \frac{\text{Failed Runs}}{\text{Successful Runs} + \text{Failed Runs}}$. Runs marked `running` or `queued` are treated as incomplete and excluded from error rate calculations.
- **Duration Percentiles ($p_{50}$ & $p_{95}$):** Continuous linear interpolation over completed run durations ($k = (N-1) \times p$), ensuring identical and predictable results across both SQLite and PostgreSQL.
- **Token Volume:** Sum of input (prompt) and output (completion) tokens across spans.
- **Cost Attribution:** Exact USD model execution cost summed from LLM spans. Differentiates metered runs from unmetered runs (`unmetered_runs`) to prevent misleading zero-cost assumptions.
- **Continuous Time-Series:** Dynamically computes contiguous time intervals and zero-pads sparse periods so frontend trendlines never break or jump across missing days.

### 5.2 Analytics API Endpoints
- `GET /v1/analytics/overview?time_range=7d&agent_name=SupportAgent`: High-level KPI metrics, percentiles, and recent runs.
- `GET /v1/analytics/timeseries?time_range=7d&interval=hour`: Continuous telemetry points (volume, errors, $p_{50}$, $p_{95}$, tokens, cost).
- `GET /v1/analytics/models?time_range=7d`: Aggregated LLM calls, token burn, latency, and costs grouped by model name.
- `GET /v1/analytics/agents?time_range=7d`: Execution volume, success rates, $p_{95}$ latency, and total costs grouped by agent and version.
- `GET /v1/analytics/cost-breakdown?time_range=7d`: Daily cost breakdown by agent and model, with metered vs unmetered counts.

### 5.3 Alert Rule Management & Evaluation Engine
TraceHarbor includes an active monitoring engine that continuously evaluates agent telemetry against user-configured thresholds:

- **Metrics Monitored:** `error_rate` (0.0–1.0), `p95_latency_ms` (ms), `total_cost` ($), `eval_pass_rate` (0.0–1.0), `regression_count`.
- **Operators:** `>`, `>=`, `<`, `<=`, `==`.
- **Evaluation Windows:** `15m`, `1h`, `6h`, `24h`, `7d`.
- **Notification Channels:** `in_app` (incident audit history), `webhook` (outbound HTTP), `both`.
- **Cooldown & Deduplication:** Configurable mute period (default 30m) prevents repeated alert storms when a metric stays above threshold.
- **Alert Endpoints:**
  - `POST /v1/alerts/rules`: Create a new alert rule.
  - `GET /v1/alerts/rules`: List all alert rules for the current project.
  - `PATCH /v1/alerts/rules/{id}`: Update threshold, window, channel, webhook, or enable/disable.
  - `DELETE /v1/alerts/rules/{id}`: Delete an alert rule.
  - `GET /v1/alerts/history`: Paginated audit log of triggered alerts and delivery status.
  - `POST /v1/alerts/evaluate`: On-demand batch evaluation of all active rules.
  - `POST /v1/alerts/test/{id}`: Dry-run test of a single rule against live telemetry.

### 5.4 SSRF-Protected Outbound Webhooks
When configuring webhook notifications, TraceHarbor enforces strict server-side request forgery (SSRF) defenses:
- **IP Range Filtering:** Automatically resolves target hostnames and rejects loopback (`127.0.0.1`, `::1`), private networks (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`), link-local (`169.254.0.0/16`), and cloud metadata IPs (`169.254.169.254`).
- **Cryptographic Signatures:** Outbound HTTP payloads are signed with an HMAC SHA-256 digest (`X-TraceHarbor-Signature-256`) when a secret is configured.
- **Bounded Timeouts:** Webhook HTTP requests enforce a strict 5.0-second timeout.

---

## 6. Generating Real Telemetry & Exploring Phase 4

To generate live agent telemetry, evaluate rules, and inspect real-time metrics on the dashboard:

```powershell
# 1. Run the deterministic customer support demo agent to generate real runs & spans
python -m demo-agents.support_agent.agent
```
The demo agent will invoke tool calls, execute multi-step reasoning, and stream spans to the backend.

Then explore the new Phase 4 views:
- **Advanced Analytics (`http://localhost:3000/analytics`):** View volume and error trendlines, $p_{50}$/$p_{95}$ latency graphs, model cost economics, and agent version comparisons.
- **Alerts & Monitoring (`http://localhost:3000/alerts`):** Create an alert rule (e.g. `error_rate > 0.05`), click **"Evaluate Rules Now"**, and review triggered incidents in the audit log.

---

## 7. Python Tracing SDK Usage

### 7.1 Local Installation
```bash
pip install -e packages/sdk-python
```

### 7.2 Basic Tracing Example
```python
import traceharbor

# 1. Initialize once at application startup
traceharbor.init(
    api_key="th_live_your_project_api_key",
    endpoint="http://127.0.0.1:8000",
)

# 2. Decorate top-level agent workflows (supports sync and async functions)
@traceharbor.trace(name="support_agent", version="1.0", tags=["support", "prod"])
def answer(question: str) -> str:
    # 3. Instrument internal tool calls and reasoning steps
    with traceharbor.span("search_knowledge_base", span_type="tool") as s:
        s.set_input({"query": question})
        faq_result = "Returns are accepted within 30 days."
        s.set_output({"result": faq_result})
        s.set_tokens(prompt=20, completion=15, total=35, cost_usd=0.00007, model="gpt-4o-mini")
    
    return f"According to our policy: {faq_result}"

# 4. Invoke agent normally — tracing happens non-blockingly in the background
response = answer("What is the return policy?")

# 5. Flush and shutdown before process exit
traceharbor.flush()
traceharbor.shutdown()
```

---

## 8. Testing & Quality Assurance

### 8.1 Backend Test Suite (64 Tests)
```powershell
python -m pytest apps/api/app/tests -v
```
Covers:
- **Analytics:** overview KPI calculation, zero-padded continuous timeseries, model attribution, agent version comparisons, empty project handling, and tenant isolation.
- **Alerting & Monitoring:** rule CRUD lifecycle, operator validation, window limits, threshold evaluation, cooldown deduplication, and SSRF URL validation.
- **Datasets:** creation, pagination, test-case addition, JSON & CSV uploads, validation error handling, case count limits, and safe deletion.
- **Rule Evaluators:** exact match, case-insensitive match, required keywords, regex ReDoS safety, JSON syntax, JSON Schema validation, tool-call tracking, latency threshold checks, token/cost checks, output presence, and payload safe truncation.
- **LLM Judge:** mock fallback mode, rubric validation, timeout handling, and unconfigured key handling with zero paid calls.
- **Experiments:** agent directory listing, lifecycle execution, trace Run/Span linkage, per-case result persistence, empty dataset rejection, and unapproved agent rejection.
- **Regression Comparison:** side-by-side alignment, delta calculations, regression classification, improvement classification, and incompleted experiment rejection.
- **Tenant Isolation:** cross-project dataset access protection, experiment reading/writing isolation, and API key authentication enforcement.
- **Core Tracing & Runs:** health endpoints, ingestion cycle validation, batch limits, runs pagination, and waterfall detail retrieval.

### 8.2 Python SDK Test Suite (9 Tests)
```powershell
python -m pytest packages/sdk-python/tests -v
```
Covers: sync/async tracing, nested spans, error recording, redaction, queue limits, flush/shutdown, and transport failure isolation.

### 8.3 Combined Automated Test Execution (73 Tests Total)
```powershell
python -m pytest apps/api/app/tests packages/sdk-python/tests -v
```
Result: **73 passed, 0 failures, 0 errors** in ~7.5 seconds.

### 8.4 Python Code Style & Linting
```powershell
python -m ruff check apps/api packages/sdk-python
```
Result: **All checks passed (0 errors)**.

### 8.5 Frontend Typechecking, Linting & Production Build
```powershell
cd apps/web
npm run typecheck
npm run lint
npm run build
```
Result:
- **Typecheck:** Clean pass (`tsc --noEmit`).
- **ESLint:** Clean pass with **0 errors and 0 warnings**.
- **Production Build:** Successfully compiled all 12 App Router static and dynamic routes (`/`, `/runs`, `/runs/[id]`, `/analytics`, `/alerts`, `/datasets`, `/experiments`, `/experiments/[id]`, `/experiments/compare`, `/projects`, `/settings`, `/_not-found`).

> **Database & Infrastructure Status Note:**  
> All 73 automated tests execute against an in-memory SQLite database and mocked transport. Docker Desktop and a live PostgreSQL instance have not yet been started or tested in this local environment; execution of Alembic migrations (`001_initial_schema.py`, `002_evaluation_engine.py`, and `003_analytics_and_alerts.py`) against live PostgreSQL remains pending Docker availability.

---

## 9. Monorepo Directory Structure

```
TraceHarbor/
├── .github/workflows/ci.yml       # GitHub Actions CI workflow (linting, tests, build)
├── apps/
│   ├── api/                       # FastAPI backend application
│   │   ├── alembic/               # Database migrations (001_initial_schema, 002_evaluation_engine, 003_analytics_and_alerts)
│   │   ├── app/
│   │   │   ├── alerts/            # Alert evaluation engine, cooldown logic, SSRF-safe notifications
│   │   │   ├── analytics/         # Metric semantics, percentiles, timeseries bucketing
│   │   │   ├── api/v1/            # API routers: ingest, runs, analytics, alerts, datasets, experiments
│   │   │   ├── core/              # Config, DB connection, auth, structured logging
│   │   │   ├── evaluation/        # Rule evaluators, LLM judge, runner, agent registry, parser
│   │   │   ├── models/            # SQLAlchemy models: user, project, run, span, dataset, experiment, alert
│   │   │   ├── schemas/           # Pydantic v2 request and response contracts
│   │   │   └── tests/             # 64 automated pytest tests covering all subsystems
│   │   └── pyproject.toml         # Backend dependencies & tools configuration
│   └── web/                       # Next.js 14 App Router web dashboard
│       ├── src/
│       │   ├── app/               # Routes: /, /runs, /analytics, /alerts, /datasets, /experiments, /experiments/compare
│       │   ├── components/        # Layout & UI components (Navbar, Sidebar)
│       │   └── lib/               # Typed API client and TypeScript definitions
│       └── package.json           # Frontend dependencies
├── datasets/                      # Reference golden benchmark datasets (JSON & CSV)
├── demo-agents/                   # Standalone agent implementations (Customer Support Agent)
├── docs/
│   └── ARCHITECTURE.md            # In-depth architectural designs & Mermaid sequences
├── infra/
│   └── docker-compose.yml         # Container definitions: PostgreSQL 16 (pgvector) & Redis 7
├── packages/
│   └── sdk-python/                # TraceHarbor Python Tracing SDK library
├── .env.example                   # Environment variables template
├── .gitignore                     # Git ignore rules for Python, Node, and environments
├── README.md                      # Comprehensive project documentation
└── SPEC.md                        # Platform specification & engineering roadmap
```

---

## 10. Roadmap

TraceHarbor follows the incremental roadmap outlined in [SPEC.md](SPEC.md):
- **Phase 0:** Project Scaffolding & Database Foundation *(Completed & Tested)*
- **Phase 1A:** Trace Ingestion API & Python SDK *(Completed & Tested)*
- **Phase 2:** Trace Waterfall UI & Observability Dashboard *(Completed & Tested)*
- **Phase 3:** Evaluation & Regression Testing Engine *(Completed & Tested)*
- **Phase 4:** Advanced Analytics, Monitoring & Alerting *(Completed & Tested)*
- **Phase 5:** AI Safety & Red-Teaming Module *(Upcoming)*
- **Phase 6:** Intelligence Layer (Vector Failure Clustering via pgvector)
- **Phase 7:** Production Hardening & Portfolio Polish

---

## Author & Attribution

**Priyanshu Raman**  
- **GitHub:** [@priyanshu150106](https://github.com/priyanshu150106)  
- **Repository:** [TraceHarbor on GitHub](https://github.com/priyanshu150106/TraceHarbor---AI-AGENT-INTELLIGENCE-PLATFORM.git)  
- **Contact:** [priyanshu150106@gmail.com](mailto:priyanshu150106@gmail.com)

