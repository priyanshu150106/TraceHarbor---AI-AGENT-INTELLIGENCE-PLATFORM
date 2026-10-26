# TraceHarbor — Technical Demonstration & Evaluation Guide

This guide is intended for engineering recruiters, software architects, and hiring managers evaluating TraceHarbor as a technical portfolio project.

TraceHarbor is an AI Agent Observability, Evaluation, Safety, and Failure-Intelligence platform designed to provide production observability for multi-step agent reasoning pipelines.

---

## 1. Fast Demonstration (60-Second Automated Walkthrough)

To verify the entire platform lifecycle end-to-end without needing external cloud accounts or third-party API keys:

```bash
# Clone the repository
git clone https://github.com/priyanshu150106/TraceHarbor---AI-AGENT-INTELLIGENCE-PLATFORM.git
cd TraceHarbor

# Run the complete 8-step verification walkthrough in isolated memory
python scripts/demo_walkthrough.py --in-memory
```

### What This Demonstrates
The walkthrough executes and asserts the following subsystems:
1. **Health Probes**: Liveness (`/healthz`) and Readiness (`/readyz`) probes verify operational status.
2. **Telemetry Ingestion**: SDK telemetry payloads with nested tool and LLM spans are ingested, validating DAG parent-child relationships and cycle rejection.
3. **Run Inspection**: Retrieves trace details, verifying latency, token usage, and cost calculations.
4. **Automated Regression Evaluation**: Golden FAQ datasets are evaluated against agent outputs.
5. **Adversarial Safety Red-Teaming**: Executes prompt injection and canary secret-leakage evaluations with automated refusal scoring.
6. **Failure Intelligence Synchronization**: Scans failed spans and test results, executing PII/token redaction.
7. **Semantic Vector Clustering**: Persists error clusters with cosine/lexical similarity metrics and updates investigation triage status.
8. **Multi-Tenant Security**: Confirms that cross-tenant access with unauthorized keys is strictly blocked (401/403).

---

## 2. Interactive Hands-On Demonstration

### Step 1: Start the Backend & Frontend

In Terminal 1 (Backend API):
```bash
cd apps/api
uvicorn app.main:app --port 8000 --reload
```

In Terminal 2 (Dashboard Web UI):
```bash
cd apps/web
npm run dev
```
Open your browser to `http://localhost:3000`.

---

### Step 2: Run the Reference Customer Support Agent

TraceHarbor includes a deterministic reference agent (`demo-agents/support_agent.py`) instrumented with the TraceHarbor Python SDK (`@traceharbor.trace`, `traceharbor.span`).

```bash
# Run successful agent execution (generates clean trace)
python demo-agents/support_agent.py --query "What is the return policy?"

# Run simulated tool failure (generates error span for failure intelligence)
python demo-agents/support_agent.py --simulate-error
```

**What happens behind the scenes:**
- The agent executes multi-step reasoning: tool retrieval (`knowledge_base_search`) followed by response synthesis (`llm_response_synthesis`).
- The Python SDK enqueues telemetry in a bounded background buffer and flushes it asynchronously over HTTP to `http://127.0.0.1:8000/v1/ingest/spans`.
- Latency, token metrics (prompt/completion), and simulated costs are recorded.

---

### Step 3: Inspect Traces in the Web Dashboard

1. Navigate to **Runs Explorer** (`http://localhost:3000/runs`).
2. Click on the most recent `support_agent` run.
3. Review the **Trace Waterfall Visualizer**:
   - Inspect the root `chain` span and child `tool` and `llm` spans.
   - Click on `knowledge_base_search` to inspect inputs, outputs, duration, and token usage.
   - Inspect the failed run to view error stack traces and error types.

---

### Step 4: Explore AI Safety & Red-Teaming

1. Navigate to **Safety** (`http://localhost:3000/safety`).
2. Review the Safety Overview metrics:
   - Pass rates across attack categories: Prompt Injection, Jailbreak Refusal, Sensitive Data Leakage, Unsafe Tool Policies.
3. Navigate to **Campaigns** (`http://localhost:3000/safety/campaigns`) to inspect individual adversarial attack runs and canary leakage detections.

---

### Step 5: Failure Intelligence & Semantic Clustering

1. Navigate to **Failure Intelligence** (`http://localhost:3000/failures`).
2. Click **Sync Failures** to scan error traces and extract normalized, redacted failure events.
3. Navigate to **Failure Clusters** (`http://localhost:3000/failures/clusters`).
4. Click on a persistent failure cluster to:
   - View grouped failure events.
   - Review representative evidence and dominant error messages.
   - Transition the triage investigation status (`new` &rarr; `investigating` &rarr; `resolved`) and save resolution notes.
5. Use **Similar Failure Search** (`http://localhost:3000/failures/search`) to search for errors using semantic embeddings or lexical similarity.

---

## 3. Architecture Highlights for Technical Reviewers

- **Asynchronous Telemetry Ingestion**: The Python SDK uses non-blocking in-memory queues with bounded backpressure (`5,000` max queue size) and exponential backoff retry. It never halts the host application if telemetry servers are unreachable.
- **Topological Integrity**: The ingestion engine builds a Directed Acyclic Graph (DAG) of spans, rejecting circular self-parenting dependencies.
- **Provider-Neutral LLM Judge**: Evaluation supports mock/local modes alongside OpenAI, Anthropic, and custom LLM providers.
- **Dual Vector Architecture**: Semantic vector clustering supports native `pgvector` HNSW indexes with fallback to lexical Jaccard similarity when running lightweight local databases.
- **Defense-in-Depth Security**: Loopback and link-local IP blocks prevent webhook SSRF; API keys are salted and hashed with SHA-256; multi-pass regex scrubs PII and credentials prior to embedding.
