# TraceHarbor — Feature Documentation

This document provides a technical breakdown of the core subsystems implemented in TraceHarbor (Release Candidate `v0.1.0-rc2`).

---

## 1. Agent Tracing & Span Telemetry

### Python SDK (`traceharbor-python`)
- **Tracing Decorator & Context Manager**: Instruments functions via `@traceable` or `with client.trace(...)`, automatically capturing execution time, inputs, outputs, exceptions, and parent-child span hierarchies.
- **Asynchronous Batching**: Telemetry spans are queued in memory and flushed periodically or at application shutdown, minimizing overhead on agent response latency.
- **Payload Truncation**: Safeguards against out-of-memory errors by truncating prompt inputs and model outputs exceeding 64 KB, appending a `[TRUNCATED]` indicator while preserving JSON structural validity.
- **Custom Metadata & Tags**: Agents can attach arbitrary metadata, model identifiers, token usage numbers, and runtime tags to any span.

### Backend Ingestion Engine (`/v1/ingest/spans`)
- **Batch Processing**: Ingests hundreds of spans in a single HTTP request with validation against Pydantic schemas.
- **Relational Storage**: Persists runs and spans to PostgreSQL with foreign key constraints, run-level aggregations (total duration, span count, status), and index coverage for fast retrieval.

---

## 2. Agent Evaluation & Regression Testing

### Golden Datasets (`/v1/datasets`)
- Upload and manage evaluation datasets up to 5 MB (or 500 test cases per dataset).
- Supports input prompts, expected outputs, context variables, and baseline reference values.

### Experiment Runner (`/v1/experiments`)
- **10 Deterministic Evaluators**:
  - `exact_match`: Strict binary equality.
  - `contains`: Substring inclusion test.
  - `regex`: Custom regex pattern validation.
  - `json_validity`: Validates whether the output is structurally sound JSON.
  - `json_schema`: Validates output against a specified JSON Schema.
  - `levenshtein_distance`: Measures edit distance similarity.
  - `bleu_score`: N-gram precision comparison.
  - `rouge_score`: Recall-oriented n-gram overlap.
  - `latency_threshold`: Asserts span duration does not exceed a millisecond limit.
  - `token_count`: Asserts total token consumption remains within budget.
- **LLM-as-a-Judge**: Optional evaluators using OpenAI (`gpt-4o-mini`) or Anthropic for semantic coherence, hallucination assessment, and response quality scoring.
- **Regression Analysis (`/v1/experiments/compare`)**:
  - Aligns test cases across a designated baseline experiment and candidate experiment.
  - Computes pass rate shift, score delta, and individual test regressions.

---

## 3. Adversarial Red-Teaming & Safety Campaigns

### Threat Model & Taxonomies
TraceHarbor evaluates agents against 7 adversarial threat categories:
1. **Prompt Injection**: Attempts to hijack model control flow and ignore system instructions.
2. **Jailbreak**: Persona manipulation, roleplaying exploits, and guardrail bypasses.
3. **Harmful Content**: Malicious, toxic, or illegal advice generation.
4. **PII Leakage**: Attempts to exfiltrate private credentials, email addresses, or secrets.
5. **System Prompt Extraction**: Probing questions aimed at recovering hidden prompt templates.
6. **Hallucination / Untruthful Content**: Fabricated factual claims in mission-critical tasks.
7. **Unsafe Code Execution**: Generation of destructive bash, SQL, or arbitrary scripts.

### Safety Campaign Execution (`/v1/safety/campaigns`)
- Automated execution of adversarial test cases against candidate agent endpoints.
- 8 specialized safety evaluators with thresholding.
- Safety scorecard generating pass rate per threat category and safety regression diffs.

---

## 4. Failure Intelligence & Vector Clustering

### Failure Synchronization & Sanitization (`/v1/failures/sync`)
- Scans ingested runs and failed spans for runtime exceptions, timeout errors, and LLM rejections.
- **PII & Secret Redaction**: Applies regex sanitization rules to scrub API keys, bearer tokens, passwords, and sensitive credentials from stack traces and payloads before storage.

### Semantic Clustering (`/v1/failures/cluster`)
- **Configurable Vector Embeddings**: Supports dense vector embeddings via pgvector (64 to 1536 dimensions).
- **Cluster Discovery**: Groups topologically similar failure signatures into actionable issue clusters using cosine similarity and thresholded grouping.
- **Lexical Fallback Search**: Seamlessly falls back to full-text search when dense vector embedding models are unconfigured or unavailable.
- **Triage Workflow**: Supports issue states (`unresolved`, `investigating`, `resolved`, `ignored`) with state transition audit histories.

---

## 5. Alert Rules & SSRF-Protected Webhooks

### Rule Configuration (`/v1/alerts/rules`)
- Configurable alert triggers over sliding windows:
  - `error_rate`: Alerts when percentage of failed runs exceeds threshold.
  - `latency_p95`: Alerts when 95th percentile latency exceeds threshold.
  - `safety_violation_rate`: Alerts when safety campaign failures spike.

### Cooldown Suppression & Execution (`/v1/alerts/evaluate`)
- Enforces configurable cooldown periods (e.g., 30 minutes) to prevent notification fatigue during continuous failure states.

### SSRF Webhook Protection
- Before dispatching outbound HTTP POST notifications to user-configured endpoints, TraceHarbor validates the target IP against non-routable, loopback, and private CIDR blocks:
  - `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `127.0.0.0/8`, `169.254.0.0/16`
- Prevents server-side request forgery against cloud metadata endpoints (`169.254.169.254`) and internal microservices.

---

## 6. Background Task Lifecycle

### Asynchronous Execution (`/v1/tasks`)
- Runs long-duration operations (evaluation suites, safety campaigns, clustering jobs) in non-blocking background workers.
- Provides real-time status polling (`pending`, `running`, `completed`, `failed`), progress percentage, and error logging.
- Auto-pruning maintains bounded memory consumption for completed tasks.

---

## 7. Multi-Tenant Security & Isolation

- **API Key Authentication**: Ingestion and query endpoints require `X-API-Key` headers. Keys are stored solely as SHA-256 hashes.
- **Project Boundary Enforcement**: All database queries, runs, spans, datasets, and alert rules are strictly scoped by `project_id`. Attempting to access cross-tenant resources returns `401 Unauthorized` or `403 Forbidden`.
