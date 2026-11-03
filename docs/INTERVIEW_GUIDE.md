# TraceHarbor — Recruiter & Engineering Interview Guide

This guide prepares engineers, hiring managers, and technical interviewers for in-depth technical discussions about TraceHarbor's architecture, design decisions, trade-offs, and implementation details.

---

## 1. Fast Pitches

### 30-Second Overview (Elevator Pitch)
> "TraceHarbor is an open-source, full-lifecycle observability and evaluation platform for AI agents. While traditional APMs track web requests, AI agents fail in non-deterministic ways: multi-step reasoning loops, prompt injections, and regression degradation across model versions. TraceHarbor provides lightweight Python SDK tracing, automated regression benchmarking with deterministic and LLM-as-judge evaluators, adversarial safety red-teaming across 7 threat taxonomies, and vector-clustered failure intelligence with pgvector."

### 90-Second Technical Overview (Deep-Dive Pitch)
> "Under the hood, TraceHarbor is a distributed telemetry and evaluation engine built on FastAPI, PostgreSQL 16, pgvector, and Next.js 14. 
> 
> Agent telemetry is captured asynchronously by our Python SDK using decorators and context managers, handling payload truncation at 64 KB to safeguard memory. Telemetry batches stream into FastAPI, where they are authenticated using SHA-256 hashed API keys and strictly scoped by project boundaries.
> 
> Beyond basic tracing, the platform addresses reliability and security through three distinct engines:
> 1. An **Evaluation Engine** that runs 10 deterministic evaluators (exact match, regex, JSON schema, Levenshtein, BLEU/ROUGE, token count) and LLM-as-a-judge scorers to detect regressions between model baselines and candidates.
> 2. A **Safety Red-Teaming Engine** evaluating agents across 7 adversarial threat categories including prompt injection and PII leakage.
> 3. A **Failure Intelligence Engine** that automatically sanitizes stack traces with regex redaction, indexes error embeddings via pgvector, and groups topologically similar failures into actionable issue clusters using cosine similarity.
> 
> The entire platform is covered by 123 automated tests, 5 Alembic migrations, and an end-to-end 9-step demonstration suite that can run either in-memory or on containerized infrastructure."

---

## 2. System Architecture Walkthrough

```
[Agent App / Demo] ──> [TraceHarbor SDK] ──(Batch HTTP)──> [FastAPI Ingestion]
                                                                  │
       ┌──────────────────────────┬───────────────────────────────┤
       ▼                          ▼                               ▼
[Auth & Isolation]     [Evaluation Engine]               [Failure Intelligence]
(SHA-256 / Multi-Tenant) (10 Deterministic + LLM)         (Regex Redaction + pgvector)
       │                          │                               │
       └──────────────────────────┼───────────────────────────────┘
                                  ▼
                    [PostgreSQL 16 + pgvector]
                                  │
                                  ▼
                 [Next.js 14 Management Dashboard]
```

1. **Ingestion Layer**: Asynchronous span batching via FastAPI with Pydantic validation schemas.
2. **Security & Boundaries**: API keys stored as SHA-256 hashes; all queries enforce project tenant filters.
3. **Storage & Vector Layer**: PostgreSQL 16 stores relational runs and spans; pgvector stores normalized failure embeddings.
4. **Evaluation Subsystem**: Executes test cases against golden datasets; computes comparative regression deltas.
5. **Safety Subsystem**: Adversarial test execution against 7 threat categories; generates risk scorecards.
6. **Failure Clustering**: Normalizes runtime errors, strips PII/credentials, embeds signatures, and clusters using cosine distance.
7. **Alert Engine**: Evaluates error rate and P95 latency rules over sliding windows with cooldown suppression and SSRF-safe webhooks.
8. **Frontend**: Next.js 14 with App Router, TypeScript, Tailwind CSS, providing waterfall trace views and regression diffs.

---

## 3. Top 10 Engineering Decisions & Architectural Rationale

| # | Decision | Context & Alternative | Rationale |
|:---|:---|:---|:---|
| **1** | **Async SQLAlchemy 2.0 with PostgreSQL 16** | Chose async PostgreSQL over MongoDB or Cassandra. | Relational integrity for nested spans, projects, and datasets is critical. SQLAlchemy 2.0 async engine maximizes I/O throughput during batch telemetry ingestion. |
| **2** | **pgvector for Vector Embeddings** | Integrated pgvector instead of a separate vector DB (Pinecone/Milvus). | Eliminates dual-database synchronization overhead. Failure metadata and vector embeddings reside in the same ACID-compliant transaction boundary. |
| **3** | **SHA-256 Hashed API Keys** | Stored hashed keys rather than plaintext or reversible encryption. | Zero-knowledge credential storage: even a full database compromise does not leak actionable API tokens. |
| **4** | **SDK Payload Truncation at 64 KB** | Bounded trace payloads in the Python client before transmission. | LLM prompts and agent thoughts can be massive. Truncating at 64 KB prevents client out-of-memory errors and network saturation while maintaining valid JSON structure. |
| **5** | **10 Deterministic Evaluators First, LLM Judge Optional** | Emphasized rule-based evaluators (Regex, JSON Schema, BLEU, Levenshtein). | Deterministic evaluators run in sub-millisecond time, cost zero dollars, and produce 100% reproducible regression checks. LLM judges are reserved for subjective scoring. |
| **6** | **In-Memory ASGI Engine for Local Demos** | Built `--in-memory` mode into `scripts/demo_walkthrough.py`. | Removes Docker as a hard prerequisite for recruiters or evaluators wanting to inspect the platform locally in seconds. |
| **7** | **Regex PII & Secret Redaction Pipeline** | Scrubbed stack traces and inputs before failure persistence. | Production agent logs frequently leak bearer tokens, OpenAI keys, or emails. Redacting at the ingestion boundary ensures compliance. |
| **8** | **SSRF-Safe Webhook Dispatcher** | Validated destination IP addresses against RFC 1918 / private blocks before HTTP POST. | Alert webhooks can be abused to probe internal VPC infrastructure or cloud metadata services (`169.254.169.254`). |
| **9** | **Lexical Fallback for Failure Search** | Provided keyword matching when embedding provider is disabled. | Ensures the failure investigation subsystem remains fully functional even when external embedding APIs are offline or unconfigured. |
| **10** | **Next.js 14 App Router with Static & Dynamic Routes** | Next.js with TypeScript and Tailwind CSS. | Delivers fast initial load times, unified component architecture, and responsive dark-mode visualization for complex trace trees. |

---

## 4. Technical Interview Q&A — Backend & Systems

### Q1: How do you handle high-throughput span ingestion without degrading agent latency?
> **Answer**: Telemetry ingestion uses a decoupled multi-stage strategy. First, the Python SDK records spans locally in memory and batches them asynchronously, keeping agent execution latency unblocked. Second, the backend exposes `/v1/ingest/spans` which accepts batch payloads containing multiple spans across runs in a single HTTP request. Third, batch database inserts are performed inside a single transaction with indexed foreign keys (`run_id`, `project_id`), avoiding individual row insert round-trips.

### Q2: How is multi-tenancy enforced across the platform?
> **Answer**: Multi-tenancy is enforced at the database query boundary. Clients authenticate using the `X-API-Key` HTTP header. The backend computes the SHA-256 hash of the incoming key and retrieves the associated `project_id`. Every service layer operation and SQLAlchemy query explicitly filters by `project_id`. Cross-tenant queries return `401 Unauthorized` or `403 Forbidden`.

### Q3: What happens to background tasks if the server restarts?
> **Answer**: In the current release candidate (`v0.1.0-rc2`), background tasks are tracked via an in-process asynchronous task manager. If the server process terminates abruptly, in-flight background tasks are marked as interrupted or lost. For production deployment, the architecture is designed to swap the in-process worker with a persistent Redis-backed Celery/ARQ queue.

### Q4: How do you prevent Server-Side Request Forgery (SSRF) when firing alert webhooks?
> **Answer**: When an alert fires and triggers an outbound HTTP POST, the webhook handler parses the target URL, resolves its hostname to an IP address, and verifies that the IP does not belong to loopback (`127.0.0.0/8`), private networks (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`), or link-local cloud metadata endpoints (`169.254.0.0/16`). If a private IP is detected, the request is aborted and logged as a security block.

---

## 5. Technical Interview Q&A — AI/ML & Evaluation

### Q1: Why not just use an LLM-as-a-judge for all evaluations?
> **Answer**: LLM-as-a-judge has three significant drawbacks: non-deterministic output variance, latency (seconds per test case), and financial cost. For CI/CD regression testing, 80% of checks can and should be deterministic: did the agent return valid JSON? Did it adhere to the required schema? Did it output the expected tool call? Is the latency within 500 ms? TraceHarbor pairs 10 deterministic evaluators with optional LLM judges to achieve fast, cheap, and reproducible CI gates.

### Q2: How does the failure clustering algorithm work?
> **Answer**: When failures are synchronized, the platform normalizes the error type, exception message, and stack trace, scrubbing sensitive credentials. If embeddings are enabled, dense vector representations are generated and stored in a pgvector column. The clustering algorithm computes cosine distance between failure vectors and groups events falling within a distance threshold into persistent `FailureCluster` records. If embeddings are disabled, TraceHarbor provides lexical fallback clustering based on normalized error signatures.

### Q3: How do safety red-team campaigns differ from regular evaluation experiments?
> **Answer**: Regular experiments test functional accuracy against golden benchmarks (inputs and expected outputs). Safety campaigns specifically challenge the agent's defense perimeter using adversarial inputs classified across 7 threat taxonomies (prompt injection, jailbreak, harmful advice, PII exfiltration, system prompt theft, hallucination, and unsafe code execution). The resulting metrics focus on defense pass rate, violation severity, and attack resistance.

---

## 6. Honest Status & Deployment Reality

| Question | Candid Engineering Answer |
|:---|:---|
| **Is TraceHarbor currently deployed to production?** | No. TraceHarbor is currently at release candidate status (`v0.1.0-rc2`). It has been validated through automated CI pipelines and local containerized staging environments. |
| **How many active users or production traffic does it handle?** | Zero external customers. The metrics and traces in the demo walkthrough are synthetically generated to test and prove platform capabilities under controlled conditions. |
| **What is the current test coverage?** | 123 automated tests pass on every commit (113 backend unit/API tests + 10 SDK tests), with 11 PostgreSQL integration tests verified in GitHub Actions CI. |
| **What are the immediate next architectural improvements?** | 1) Migrating the in-process background worker to Redis/Celery; 2) Adding OpenTelemetry (OTel) span exporter compatibility to the Python SDK; 3) Implementing live WebSocket streaming for real-time span waterfall rendering. |
