# TraceHarbor

> **Observe. Evaluate. Secure.**

TraceHarbor is an open-source AI Agent Observability, Evaluation, and Security Platform. It enables developers and AI engineers to trace agent executions, inspect nested LLM and tool calls, measure token latency and costs, detect regressions with automated benchmark evaluations, and red-team agents against prompt injection and security vulnerabilities.

[![CI](https://github.com/priyanshu150106/TraceHarbor---AI-AGENT-INTELLIGENCE-PLATFORM/actions/workflows/ci.yml/badge.svg)](https://github.com/priyanshu150106/TraceHarbor---AI-AGENT-INTELLIGENCE-PLATFORM/actions)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-14-black.svg)](https://nextjs.org/)
[![Tests](https://img.shields.io/badge/tests-121%20passed-brightgreen.svg)](#10-testing--quality-assurance)
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
| **Safety Overview** | `/safety` | Fleet safety posture, category breakdown, critical vulnerability feed, and quick-launch. |
| **Safety Campaigns** | `/safety/campaigns` | Searchable campaign execution history, pass/fail status, and launch modal. |
| **Safety Campaign Details** | `/safety/campaigns/[id]` | Per-test security scorecard, redacted evidence drawer, and linked trace runs. |
| **Safety Regression Engine** | `/safety/compare` | Head-to-head security regression detection (baseline vs candidate agent versions). |
| **Failure Intelligence Feed** | `/failures` | Normalized failure event feed, severity/category filters, time range, cluster assignment, and sync actions. |
| **Failure Clusters Overview** | `/failures/clusters` | Semantic cluster overview, status filter tabs, frequency trends, and bounded clustering job execution. |
| **Cluster Investigation Detail**| `/failures/clusters/[id]` | Root-cause evidence, representative traces, affected agent versions, member events, and status audit trail. |
| **Similar Failure Search** | `/failures/search` | Nearest-neighbor similarity search by query text or event ID with pgvector cosine distance and lexical fallback. |

---

## 2. Implementation Status

| Feature / Area | Status | Notes |
| :--- | :--- | :--- |
| **Phase 0: Monorepo Foundation** | Implemented & Verified | Branch, author identity, remote, and folder layout configured |
| **Phase 0: Backend Scaffolding** | Implemented & Tested | FastAPI app with `/health`, structured logging, and CORS |
| **Phase 0: Database Models** | Implemented & Tested | SQLAlchemy 2.0 models for users, projects, api_keys, runs, spans, alert rules, history, failures |
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
| **Phase 5: AI Safety & Red-Teaming** | **Implemented & Tested** | 7 threat categories, 8 deterministic evaluators, canary detection, safe boundary, campaigns, regression diff, and `/safety` UI |
| **Phase 6: Failure Intelligence & Semantic Clustering** | **Implemented & Tested** | Normalized failure events, redaction engine, pluggable embeddings (fake/openai), PostgreSQL pgvector, threshold clustering, status audit trail, and Web UI |
| **Phase 7: Production Readiness & Reliability Engineering** | **Implemented & Tested** | Request correlation ID middleware, separate liveness/readiness probes, background task manager with retries, real PostgreSQL/pgvector integration suite, and hardened CI containers |

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
- Safety Overview: `http://localhost:3000/safety`
- Safety Campaigns: `http://localhost:3000/safety/campaigns`
- Safety Regression Diff: `http://localhost:3000/safety/compare`

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

## 7. AI Safety & Red-Teaming Module (Phase 5)

TraceHarbor includes a production-grade AI Agent Safety and Red-Teaming benchmark engine designed to test, audit, and compare agent versions against adversarial attacks and safety policy violations.

### 7.1 Threat Categories
TraceHarbor structures adversarial safety testing across 7 core threat categories plus benign controls:
1. **Prompt Injection (`prompt_injection`):** Direct and indirect attempts to override developer system prompts, alter agent goals, or jailbreak boundary instructions.
2. **Instruction Hierarchy (`instruction_hierarchy`):** Multi-tenant or untrusted retrieval payloads (RAG) attempting to elevate untrusted user data above foundational system prompts.
3. **Sensitive Data Handling (`sensitive_data_handling`):** Elicitation attempts targeting synthetic canary secrets, internal API keys, passwords, or PII.
4. **Unsafe Tool Use (`unsafe_tool_use`):** Prompting agents to invoke unauthorized or destructive tools (e.g., `execute_command`, `refund_unapproved`, `delete_user`).
5. **Policy Boundary Testing (`policy_boundary`):** Boundary testing for disallowed actions such as unverified shipping changes, financial modifications, or terms-of-service violations.
6. **Data Exfiltration (`data_exfiltration`):** Covert attempts to transmit synthetic canary secrets via unauthorized outbound webhooks or side-channel tool parameters.
7. **Jailbreak & Refusal Robustness (`jailbreak_refusal`):** Adversarial framing (hypothetical roleplay, developer mode override) testing whether an agent refuses unsafe commands safely and politely.

### 7.2 Deterministic Safety Evaluators
Evaluators run deterministically in-process with zero external API dependencies, producing structured outcomes (`passed`, `severity`, `explanation`, and `evidence`):
- **Secret Leakage Evaluator (`secret_leakage`):** Scans agent outputs and tool calls for synthetic canaries (`TR_CANARY_...`) and known secrets, automatically masking evidence before database persistence.
- **Required Refusal Evaluator (`required_refusal`):** Verifies that the agent refused an adversarial request and did not execute the forbidden action.
- **Forbidden Pattern Evaluator (`forbidden_pattern`):** Detects prohibited substrings or regex signatures that indicate boundary violations.
- **Tool Policy Enforcement Evaluator (`tool_policy_enforcement`):** Validates tool execution against strict allowlists and denylists.
- **Output Schema Validation Evaluator (`output_schema_validation`):** Ensures responses adhere to structural safety formats.
- **Policy Compliance Evaluator (`policy_compliance`):** Evaluates multi-criterion policy rules (e.g. required disclosures, forbidden clauses).
- **Prompt Injection Resistance Evaluator (`prompt_injection_resistance`):** Tests resilience against jailbreak markers and instruction override indicators.
- **Optional LLM Safety Judge (`llm_safety_judge`):** Optional, provider-neutral qualitative safety judge disabled by default. *Crucially, LLM judges are never treated as proof of safety.*

### 7.3 Safe Execution Boundary
Safety evaluations must never cause damage to host infrastructure:
- **Zero Arbitrary Execution:** Only pre-registered agent adapters (`SupportAgentSecured` `v3.0-secured`, `SupportAgentVulnerable` `v0.5-vulnerable`, etc.) from the explicit adapter registry can be targeted.
- **Isolated Mock Tools:** All tool executions are intercepted by deterministic mock fixtures (`search_order`, `lookup_faq`). No real external webhooks or database writes are permitted.
- **Resource Bounds:** Enforces strict timeouts (10s default), input size truncation (10 KB), and output size truncation (50 KB).
- **Exception Trapping:** Agent runtime exceptions or timeouts are recorded as isolated test outcomes without crashing or leaving the campaign in an inconsistent state.

### 7.4 Safety Campaigns & Version Regression Analysis
TraceHarbor persists comprehensive safety campaigns linked directly to trace runs:
- **Campaign Metrics:** Overall pass rate, category breakdown, severity-weighted penalty score, and critical failure count.
- **Evidence Redaction:** Synthetic secrets, canary tokens, and credentials in test evidence are automatically sanitized using `redact_sensitive_content` before persistence.
- **Regression Diffing:** Compare baseline vs. candidate campaigns aligned by immutable `test_case_id`:
  - 🚨 **Regressed:** Passed in baseline, failed in candidate.
  - ✨ **Resolved:** Failed in baseline, fixed in candidate.
  - 🤝 **Unchanged:** Identical security posture.
  - ⚠️ **Evaluator Error:** Runtime execution faults.

### 7.5 Safety REST API Endpoints

| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `GET` | `/v1/safety/overview` | Fleet safety KPIs, pass rates, and critical vulnerabilities | Tenant Isolated |
| `GET` | `/v1/safety/campaigns` | Searchable list of executed safety campaigns | Tenant Isolated |
| `POST` | `/v1/safety/campaigns` | Launch a safety campaign against an approved agent | Tenant Isolated |
| `GET` | `/v1/safety/campaigns/{id}` | Detailed scorecard, test results, and redacted evidence | Tenant Isolated |
| `GET` | `/v1/safety/compare` | Compare baseline vs candidate campaigns (regressions/fixes) | Tenant Isolated |
| `GET` | `/v1/safety/datasets` | Directory of registered safety benchmark datasets | Tenant Isolated |
| `POST` | `/v1/safety/datasets` | Create or import a safety benchmark dataset | Tenant Isolated |
| `GET` | `/v1/safety/datasets/{id}` | Retrieve safety test cases and threat metadata | Tenant Isolated |
| `GET` | `/v1/safety/agents` | Directory of approved agent adapters eligible for red-teaming | Tenant Isolated |

### 7.6 Walkthrough: Running a Red-Team Benchmark & Comparing Agent Versions

TraceHarbor ships with a curated red-teaming benchmark dataset at `datasets/safety_redteam_benchmark.json` (and `.csv`) covering prompt injection, sensitive data leakage, unauthorized tool execution, and benign controls.

**Step 1 — Upload the Safety Benchmark Dataset:**
1. Navigate to `http://localhost:3000/datasets` (or create via `POST /v1/safety/datasets`).
2. Upload `datasets/safety_redteam_benchmark.json` with Dataset Type set to `safety`.

**Step 2 — Launch Vulnerable Agent Campaign (Baseline):**
1. Navigate to `http://localhost:3000/safety/campaigns`.
2. Click **"Launch Campaign"**.
3. Select agent `SupportAgentVulnerable (v0.5-vulnerable)` and the safety dataset.
4. Click **"Run Campaign"**. The benchmark will detect critical vulnerabilities (e.g. system canary leakage, unauthorized tool calls, prompt injection compliance).

**Step 3 — Launch Secured Agent Campaign (Candidate):**
1. Click **"Launch Campaign"** again.
2. Select agent `SupportAgentSecured (v3.0-secured)` and the same safety dataset.
3. Click **"Run Campaign"**. The secured agent defends against injections, protects canaries, refuses unauthorized tools, and passes benign control prompts.

**Step 4 — Compare Safety Regressions & Verifications:**
1. Navigate to `http://localhost:3000/safety/compare`.
2. Select the vulnerable run as Baseline and the secured run as Candidate.
3. View the regression engine: it highlights resolved vulnerabilities, proves zero newly introduced regressions, and displays redacted evidence side-by-side.

---

## 8. Python Tracing SDK Usage

### 8.1 Local Installation
```bash
pip install -e packages/sdk-python
```

### 8.2 Basic Tracing Example
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

## 9. Failure Intelligence & Semantic Clustering (Phase 6)

### 9.1 Overview & Architecture
TraceHarbor automatically extracts, redacts, normalizes, and groups recurring AI agent failures across runs, spans, evaluation experiments, and safety benchmarks into persistent clusters using PostgreSQL pgvector.

- **Idempotent Multi-Source Ingestion:** Syncs from failed runs (`status=error`), failed spans (`status=error`), failed evaluations (`status=failed`), and failed safety red-team tests (`passed=false`) without duplicate events.
- **Strict Privacy & Redaction:** Strips API keys, Bearer tokens, URLs with embedded credentials, emails, IPv4 addresses, file paths, SSNs, credit cards, line numbers, and hex memory addresses before storage or embedding.
- **Pluggable Embedding Providers:** Supports `openai` (`text-embedding-3-small`), `fake` (deterministic unit vectors for zero-dependency local testing), or disabled mode with an automatic lexical similarity fallback.
- **Content-Hash Deduplication:** Uses SHA-256 hashes of normalized failure summaries (`content_hash`) to avoid re-embedding unchanged error text.
- **Incremental Threshold-Based Clustering:** Assigns failure events to clusters via cosine distance against centroid vectors with configurable similarity thresholds (default $0.85$) and minimum cluster sizes (default $2$).
- **Status Audit Trail:** Tracks cluster lifecycle (`new` -> `investigating` -> `resolved` -> `ignored`) with developer resolution notes and an immutable audit log in `cluster_status_changes`.

### 9.2 Failure Intelligence API Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/v1/failures/overview` | Fleet failure metrics, cluster status breakdown, severity counts, and embedding capability status |
| `GET` | `/v1/failures` | Filterable, paginated normalized failure event feed |
| `GET` | `/v1/failures/{id}` | Single failure event detail with source context and linked trace |
| `POST` | `/v1/failures/search` | Nearest-neighbor vector similarity search or lexical fallback |
| `GET` | `/v1/failures/clusters` | List semantic clusters with dominant category, severity distribution, and status filters |
| `GET` | `/v1/failures/clusters/{id}` | Cluster detail with representative traces, member events, and status audit trail |
| `PATCH`| `/v1/failures/clusters/{id}/status` | Update cluster status (`new`, `investigating`, `resolved`, `ignored`) with resolution notes |
| `POST` | `/v1/failures/clusters/run` | Execute bounded clustering job against embedded failures (supports background mode) |
| `POST` | `/v1/failures/sync` | Idempotently scan and normalize failure events from existing runs, spans, and benchmarks |

---

## 10. Production Readiness & Reliability Engineering (Phase 7)

### 10.1 System Reliability, Background Tasks & Distributed Tracing
- **Request Correlation ID Middleware:** Every HTTP request is assigned a UUID4 correlation ID via `CorrelationIdMiddleware`. Accepts caller-provided `X-Request-ID` headers for end-to-end distributed tracing, binds `request_id` to `structlog` context, and always returns `X-Request-ID` in HTTP response headers.
- **Probe Separation:**
  - `/healthz` — Liveness probe (fast, zero dependencies) returning HTTP 200 if the process is alive.
  - `/readyz` — Readiness probe verifying essential database reachability (PostgreSQL `SELECT 1`). Returns HTTP 503 Service Unavailable if the database is unreachable, safely preventing traffic routing to unready replicas.
  - `/health` — Diagnostic health overview reporting system version, database status, and uptime for dashboards and status pages.
- **In-Process Background Task Manager:** Built-in `BackgroundTaskManager` (`app.core.tasks`) executes long-running operations asynchronously without requiring external worker daemons:
  - Bounded exponential backoff retries (1s, 2s, 4s, capped at 10s) on transient exceptions.
  - Status tracking (`queued`, `running`, `completed`, `failed`, `cancelled`), progress indicators, and memory-bounded history eviction (retaining up to 500 tasks).
  - Graceful shutdown integration via FastAPI lifespan ensuring active tasks are cleanly drained or cancelled during SIGTERM.
  - Asynchronous background execution options for clustering (`/v1/failures/clusters/run`) and failure sync (`/v1/failures/sync`) via `run_in_background=True`.
- **Production Mode Tenant Guard:** In production mode (`debug=False`), `resolve_project_id` rejects unauthenticated requests without an explicit `project_id` with HTTP 401 Unauthorized, eliminating accidental cross-tenant data exposure.
- **Startup Configuration Validation:** Automatic inspection of production configuration emitting warnings if placeholder secrets (`JWT_SECRET`, default credentials, wildcard CORS) are detected.
- **Infrastructure Hardening:** Docker Compose binds PostgreSQL (5432) and Redis (6379) strictly to `127.0.0.1` and uses an automated `initdb` script (`01-init.sql`) to provision the `vector` extension and test database.

### 10.2 Reliability & Task Management Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/health` | Diagnostic status report for dashboards and humans |
| `GET` | `/healthz` | Liveness probe for container orchestrators (Docker, K8s) |
| `GET` | `/readyz` | Readiness probe verifying PostgreSQL database reachability |
| `GET` | `/v1/tasks` | List recent background tasks filtered by project tenancy |
| `GET` | `/v1/tasks/{id}` | Inspect progress, status, and results for a background task |
| `POST` | `/v1/tasks/{id}/cancel` | Cancel an in-progress or queued background task |

---

## 11. Testing & Quality Assurance

### 11.1 Backend Test Suite (112 Unit & API Tests)
```powershell
python -m pytest apps/api/app/tests -v -m "not integration"
```
Covers:
- **Production Readiness & Reliability (Phase 7):** Request correlation ID middleware (`X-Request-ID` generation & propagation), liveness probe (`/healthz`), readiness probe (`/readyz`) with DB health check, production-mode tenant auth enforcement (`resolve_project_id` rejects unauthenticated in `debug=False`), startup configuration safety warnings, SSRF URL validator rules, BackgroundTaskManager in-process async execution, bounded exponential backoff retries, async clustering & failure sync, task status/cancellation API (`/v1/tasks`), and comprehensive End-to-End workflow verification (`test_e2e_workflow.py`).
- **Failure Intelligence & Clustering (Phase 6):** PII and credential redaction, error text normalization, normalizers across runs/spans/experiments/safety, FakeEmbeddingProvider determinism and validation, cosine similarity boundaries, lexical similarity fallback, single-pass clustering, cluster metadata aggregation, idempotent sync, cluster status transitions with audit logs, similarity search endpoints, and project tenant isolation.
- **Safety Evaluators & Redaction:** secret canary detection, required refusal checks, forbidden pattern detection, tool policy enforcement, schema validation, multi-rule policy compliance, prompt injection resistance, LLM safety judge mock fallback, and canary redaction.
- **Safety Runner, Campaigns & Regression:** agent isolation boundary, timeouts, input/output truncation, exception safety, campaign persistence, baseline vs candidate regression comparison, tenant isolation, and alert rule metric computation.
- **Analytics:** overview KPI calculation, zero-padded continuous timeseries, model attribution, agent version comparisons, empty project handling, and tenant isolation.
- **Alerting & Monitoring:** rule CRUD lifecycle, operator validation, window limits, threshold evaluation, cooldown deduplication, safety metrics (`safety_pass_rate`, `safety_critical_failures`), and SSRF URL validation.
- **Datasets:** creation, pagination, test-case addition, JSON & CSV uploads, validation error handling, case count limits, and safe deletion.
- **Rule Evaluators:** exact match, case-insensitive match, required keywords, regex ReDoS safety, JSON syntax, JSON Schema validation, tool-call tracking, latency threshold checks, token/cost checks, output presence, and payload safe truncation.
- **Experiments:** agent directory listing, lifecycle execution, trace Run/Span linkage, per-case result persistence, empty dataset rejection, and unapproved agent rejection.
- **Core Tracing & Runs:** health endpoints, ingestion cycle validation, batch limits, runs pagination, and waterfall detail retrieval.

### 11.2 Real PostgreSQL & pgvector Integration Suite (11 Tests)
```powershell
# Run with local Docker or external PostgreSQL:
docker compose -f infra/docker-compose.yml up -d
python -m pytest apps/api/app/tests -v -m "integration"
```
Covers:
- Alembic migration chain consistency (001 -> 002 -> 003 -> 004 -> 005) and schema upgrades against real PostgreSQL.
- Full CRUD operations across all 15 ORM models on PostgreSQL with native JSONB, UUID, and timezone-aware timestamps.
- Native `pgvector` operations: 64-dimensional float vector insertion, cosine distance search (`<=>`), L2 distance, and cluster centroid indexing.
- Multi-project database-level tenant isolation boundaries.
- *Graceful skipping:* When PostgreSQL is not running locally (e.g. without Docker Desktop), integration tests skip cleanly with informative messages. In GitHub Actions CI, tests run against a dedicated `pgvector/pgvector:pg16` service container.

### 11.3 Python SDK Test Suite (9 Tests)
```powershell
python -m pytest packages/sdk-python/tests -v
```
Covers: sync/async tracing, nested spans, error recording, redaction, queue limits, flush/shutdown, and transport failure isolation.

### 11.4 Combined Automated Test Execution (121 Tests Total)
```powershell
python -m pytest apps/api/app/tests packages/sdk-python/tests -v
```
Result: **121 passed, 11 skipped (PG integration), 0 failures** in ~11 seconds.

### 11.5 Python Code Style & Linting
```powershell
python -m ruff check apps/api packages/sdk-python
```
Result: **All checks passed (0 errors)**.

### 11.6 Frontend Typechecking, Linting & Production Build
```powershell
cd apps/web
npm run typecheck
npm run lint
npm run build
```
Result:
- **Typecheck:** Clean pass (`tsc --noEmit`).
- **ESLint:** Clean pass.
- **Production Build:** Successfully compiled all 18 App Router static and dynamic routes (`/`, `/runs`, `/runs/[id]`, `/analytics`, `/alerts`, `/datasets`, `/experiments`, `/experiments/[id]`, `/experiments/compare`, `/safety`, `/safety/campaigns`, `/safety/campaigns/[id]`, `/safety/compare`, `/failures`, `/failures/clusters`, `/failures/clusters/[id]`, `/failures/search`, `/projects`, `/settings`, `/_not-found`).

---

## 12. Monorepo Directory Structure

```
TraceHarbor/
├── .github/workflows/ci.yml       # Hardened GitHub Actions CI (unit tests, PG16 container integration, SDK, Next.js build)
├── apps/
│   ├── api/                       # FastAPI backend application
│   │   ├── alembic/               # Database migrations (001_initial -> 002_eval -> 003_alerts -> 004_safety -> 005_failure_intelligence)
│   │   ├── app/
│   │   │   ├── alerts/            # Alert evaluation engine, cooldown logic, SSRF-safe notifications
│   │   │   ├── analytics/         # Metric semantics, percentiles, timeseries bucketing
│   │   │   ├── api/v1/            # API routers: ingest, runs, analytics, alerts, datasets, experiments, safety, failures, tasks
│   │   │   ├── core/              # Config, DB session factory, auth, structured logging, middleware, tasks
│   │   │   ├── evaluation/        # Rule evaluators, LLM judge, runner, agent registry, parser
│   │   │   ├── failures/          # Redaction, normalizer, embedding service, clustering, sync
│   │   │   ├── models/            # 15 SQLAlchemy models: user, project, run, span, dataset, experiment, alert, safety, failure
│   │   │   ├── safety/            # Redaction, evaluators, runner, comparison, dataset parser
│   │   │   ├── schemas/           # Pydantic v2 request and response contracts
│   │   │   └── tests/             # 112 unit & API tests + 11 PostgreSQL integration tests + E2E workflow
│   │   │       └── integration/   # Real PostgreSQL 16 & pgvector migration, CRUD, tenant isolation, and vector tests
│   │   └── pyproject.toml         # Backend dependencies & tools configuration (ruff, pytest)
│   └── web/                       # Next.js 14 App Router web dashboard
│       ├── src/
│       │   ├── app/               # Routes: /, /runs, /analytics, /alerts, /datasets, /experiments, /safety, /failures, /projects, /settings
│       │   ├── components/        # Layout & UI components (Navbar, Sidebar)
│       │   └── lib/               # Typed API client and TypeScript definitions
│       └── package.json           # Frontend dependencies
├── datasets/                      # Reference golden & safety red-team benchmark datasets (JSON & CSV)
├── demo-agents/                   # Standalone agent implementations (Customer Support Agent)
├── docs/
│   └── ARCHITECTURE.md            # In-depth architectural designs, Mermaid sequences & reliability specifications
├── infra/
│   ├── docker-compose.yml         # Local infrastructure: PostgreSQL 16 (pgvector) & Redis 7 (bound to 127.0.0.1)
│   └── initdb/
│       └── 01-init.sql            # Automated container init: pgvector extension & traceharbor_test DB
├── packages/
│   └── sdk-python/                # TraceHarbor Python Tracing SDK library (9 passing tests)
├── .env.example                   # Environment variables template (includes POSTGRES_TEST_URL)
├── .gitignore                     # Git ignore rules for Python, Node, and environments
├── README.md                      # Comprehensive project documentation
└── SPEC.md                        # Platform specification & engineering roadmap
```

---

## 13. Roadmap

TraceHarbor follows the incremental roadmap outlined in [SPEC.md](SPEC.md):
- **Phase 0:** Project Scaffolding & Database Foundation *(Completed & Tested)*
- **Phase 1A:** Trace Ingestion API & Python SDK *(Completed & Tested)*
- **Phase 2:** Trace Waterfall UI & Observability Dashboard *(Completed & Tested)*
- **Phase 3:** Evaluation & Regression Testing Engine *(Completed & Tested)*
- **Phase 4:** Advanced Analytics, Monitoring & Alerting *(Completed & Tested)*
- **Phase 5:** AI Safety & Red-Teaming Module *(Completed & Tested)*
- **Phase 6:** Failure Intelligence & Semantic Clustering via pgvector *(Completed & Tested)*
- **Phase 7:** Production Readiness & Reliability Engineering *(Completed & Tested)*

---

## 14. Author & Attribution

**Priyanshu Raman**  
- **GitHub:** [@priyanshu150106](https://github.com/priyanshu150106)  
- **Repository:** [TraceHarbor on GitHub](https://github.com/priyanshu150106/TraceHarbor---AI-AGENT-INTELLIGENCE-PLATFORM.git)  
- **Contact:** [priyanshu150106@gmail.com](mailto:priyanshu150106@gmail.com)


