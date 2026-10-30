# TraceHarbor — Technical Portfolio Demonstration Script

**Format:** 5–7 Minute Live Technical Demonstration  
**Target Audience:** Engineering Recruiters, Staff/Principal Engineers, Software Architects  
**Goal:** Demonstrate production-grade full-stack architecture, asynchronous telemetry ingestion, AI evaluation pipelines, adversarial safety auditing, and failure intelligence.

---

### Timing Overview
- **0:00–0:40** (40s): Problem Space & Platform Overview
- **0:40–1:40** (60s): Architecture & SDK Telemetry Instrumentation
- **1:40–2:40** (60s): Trace Inspection & Waterfall Visualization
- **2:40–3:40** (60s): Automated Regression Testing & Experiment Comparison
- **3:40–4:30** (50s): Adversarial Safety Red-Teaming & Secret Protection
- **4:30–5:20** (50s): Failure Intelligence, Redaction & Semantic Clustering
- **5:20–6:00** (40s): Real-Time Alerting, Reliability & Architectural Trade-offs
- **6:00–7:00** (60s): Buffer & Technical Questions

---

### Segment 1: Problem Space & Platform Overview (0:00 – 0:40)

- **Visual:** Open browser to TraceHarbor dashboard (`http://localhost:3000`).
- **Spoken Narrative:**
  > "Traditional APMs like Datadog or Prometheus excel at monitoring HTTP requests and microservice latency, but they fall short when observing compound AI agents. A single agent invocation can span multi-step reasoning loops, non-deterministic tool calls, retries, and LLM completions. When an agent hallucinates, leaks sensitive data, or loops indefinitely, traditional monitors simply see a slow 200 OK.
  > 
  > TraceHarbor is a purpose-built AI Agent Observability, Evaluation, Safety, and Failure Intelligence platform. It provides end-to-end tracing, regression benchmarking, adversarial red-teaming, and vector-driven error clustering so engineering teams can deploy agents with confidence."
- **Key Talking Points:**
  - Compound agent reasoning vs single HTTP request monitoring.
  - Multi-pillar approach: Observability + Evaluation + Safety + Failure Intelligence.

---

### Segment 2: Architecture & SDK Telemetry Instrumentation (0:40 – 1:40)

- **Visual:** Show `demo-agents/support_agent.py` in editor or run it from terminal.
  ```bash
  python demo-agents/support_agent.py --query "What is the return policy?"
  ```
- **Spoken Narrative:**
  > "Let's look at how agents integrate with TraceHarbor. In `support_agent.py`, we import `traceharbor`. The SDK provides a non-blocking, asynchronous telemetry pipeline.
  > 
  > The top-level agent function is decorated with `@traceharbor.trace`, creating an execution Run. Within the function, discrete reasoning steps—like retrieving knowledge base articles or invoking language models—are wrapped in `with traceharbor.span(...)`. 
  > 
  > Notice three key architectural design decisions here:
  > 1. **Client-side PII scrubbing**: Sensitive keys such as passwords, access tokens, and API credentials are automatically redacted in-process before telemetry ever touches the network.
  > 2. **Bounded backpressure**: The SDK maintains an internal queue capped at 5,000 spans with exponential backoff. If the backend is unavailable, the host agent application is never blocked or crashed.
  > 3. **DAG structural validation**: Ingestion builds a Directed Acyclic Graph, rejecting circular self-parenting spans."
- **Key Talking Points:**
  - Decorator and context-manager interface (`@traceharbor.trace`, `traceharbor.span`).
  - Zero-overhead resilience: background flush worker with thread-safe queue.

---

### Segment 3: Trace Inspection & Waterfall Visualization (1:40 – 2:40)

- **Visual:** In dashboard UI, navigate to **Runs Explorer** (`/runs`) and click on the newly ingested `support_agent` run.
- **Spoken Narrative:**
  > "In the web dashboard, the run immediately appears. Clicking into the detail view exposes our Trace Waterfall Visualizer.
  > 
  > Here, we see the complete execution hierarchy: the root `support_agent` chain span and its nested children—`knowledge_base_search` (a tool span) and `llm_response_synthesis` (an LLM span).
  > 
  > Selecting any span reveals precise input/output payloads, latency breakdown, prompt and completion token counts, and computed cost metrics.
  > 
  > If we simulate a tool failure with `--simulate-error`, the failure surfaces cleanly in red with the complete stack trace and error classification, allowing engineers to pinpoint whether the agent failed at tool execution or during response synthesis."
- **Key Talking Points:**
  - Parent-child span hierarchy visualization.
  - Granular token and cost metrics per step.
  - Clean error propagation and failure isolation.

---

### Segment 4: Automated Regression Testing & Experiment Comparison (2:40 – 3:40)

- **Visual:** Navigate to **Experiments** (`/experiments`) and then **Compare Experiments** (`/experiments/compare`).
- **Spoken Narrative:**
  > "Observing production runs is half the battle; preventing regressions is the other half. TraceHarbor includes an automated evaluation engine.
  > 
  > Here, we benchmark candidate versions against a golden dataset of test cases. When comparing `support_agent` version 1.0 against version 2.0-improved, TraceHarbor aligns outcomes by their immutable test-case ID.
  > 
  > The comparison visualizer displays:
  > - Exact score deltas across all test cases.
  > - Regressions where a previously passing prompt now fails.
  > - Improvements and unchanged cases.
  > 
  > Crucially, evaluator errors are separated from genuine test failures, preventing infrastructure timeouts from being misdiagnosed as prompt regressions."
- **Key Talking Points:**
  - Immutable test-case alignment.
  - Multi-evaluator criteria (exact match, required keywords, latency/cost thresholds, LLM-as-judge).
  - Clear separation of agent failure vs test execution failure.

---

### Segment 5: Adversarial Safety Red-Teaming & Secret Protection (3:40 – 4:30)

- **Visual:** Navigate to **Safety** (`/safety`) and **Safety Campaigns** (`/safety/campaigns`).
- **Spoken Narrative:**
  > "AI agents connected to enterprise data require defensive guardrails. TraceHarbor features a dedicated adversarial safety suite.
  > 
  > We evaluate agents across four key vulnerability categories:
  > 1. **Prompt Injection Resistance**: Testing whether the agent refuses adversarial system prompt overrides.
  > 2. **Canary Secret Leakage**: Injecting synthetic canary credentials into context and verifying that the agent never echoes them.
  > 3. **Unsafe Tool Invocation**: Enforcing policy boundaries on tool parameters.
  > 4. **Required Refusals**: Verifying compliant refusal when presented with harmful requests.
  > 
  > Results are tracked per campaign, computing pass rates and critical failure counts to prevent insecure agent updates from reaching production."
- **Key Talking Points:**
  - Standardized threat categories.
  - Automated canary tracking and refusal detection.
  - Comparative safety deltas between agent releases.

---

### Segment 6: Failure Intelligence, Redaction & Semantic Clustering (4:30 – 5:20)

- **Visual:** Navigate to **Failure Intelligence** (`/failures`) and **Failure Clusters** (`/failures/clusters`).
- **Spoken Narrative:**
  > "When running millions of spans, thousands of disparate error logs become overwhelming. TraceHarbor’s Failure Intelligence engine continuously scans error traces, normalizes repetitive noise, redacts database credentials and PII, and groups similar errors into semantic clusters.
  > 
  > In environments with PostgreSQL and `pgvector`, clustering uses native HNSW cosine distance indexes. On lightweight or local environments without vector extensions, it automatically falls back to lexical similarity.
  > 
  > Engineering teams can triage clusters directly from the dashboard: transitioning status from `new` to `investigating` to `resolved`, and attaching persistent resolution audit notes."
- **Key Talking Points:**
  - Automated failure extraction and normalization.
  - Multi-pass regex scrubbing prior to embedding.
  - Vector clustering with graceful lexical fallback.
  - Triage lifecycle state machine.

---

### Segment 7: Real-Time Alerting, Reliability & Trade-Offs (5:20 – 6:00)

- **Visual:** Navigate to **Alerts** (`/alerts`) and show configuration view.
- **Spoken Narrative:**
  > "Finally, TraceHarbor provides real-time alerting based on sliding time windows for metrics like `error_rate`, `latency_p95`, and `safety_critical_failures`.
  > 
  > To ensure operational reliability:
  > - **SSRF Protection**: All webhook destinations are validated against private, link-local, and cloud metadata IPs (`169.254.169.254`), preventing webhook reflection attacks.
  > - **Cooldown Deduplication**: Prevents alert storms by suppressing repeated notifications within configured cooldown windows.
  > 
  > To be transparent about architectural trade-offs: background jobs currently run via an in-process asynchronous task manager with bounded memory. For single-node or local deployments, this keeps deployment footprint zero-dependency; for multi-node enterprise scale, we recommend backing the queue with a distributed broker like Redis or Celery."
- **Key Talking Points:**
  - Security-first webhooks (SSRF defense).
  - Cooldown suppression.
  - Honest architectural trade-offs (in-process vs distributed queue).

---

### Segment 8: Conclusion & Questions (6:00 – 7:00)

- **Visual:** Return to Overview dashboard (`/`) or terminal showing clean CI test results.
- **Spoken Narrative:**
  > "To summarize: TraceHarbor was built from the ground up to solve the real operational challenges of compound AI agents—providing observability, rigorous evaluation, adversarial safety, and failure triage in a single cohesive platform.
  > 
  > The entire platform is open-source, fully tested with over 120 automated unit and integration tests, and verified end-to-end. Thank you, and I welcome any technical questions about the architecture or implementation."
