# TraceHarbor Dashboard Screenshot Catalog

This directory contains verified, production-grade screenshots of the TraceHarbor web dashboard captured from the active running application.

---

## 1. Environment & Capture Specification

- **Capture Method**: Automated headless browser capture (`Google Chrome 1440×900` at 100% zoom).
- **Runtime Environment**: Live FastAPI backend running on local development engine (`sqlite+aiosqlite`) paired with the production-built Next.js 14 frontend (`next start` at `http://localhost:3000`).
- **Telemetry Seeding**: Populated using the official 9-step demonstration verification suite (`scripts/demo_walkthrough.py --base-url http://127.0.0.1:8000`).
- **Theme**: Dark Mode (Tailwind `slate-950` palette).
- **Data Integrity**: All telemetry, trace names, and evaluations use synthetic benchmark data. No personal credentials or private keys are exposed.

---

## 2. Screenshot Catalog

| File | Target Route | Captured Subsystem & Highlights |
|:---|:---|:---|
| [`01-dashboard-overview.png`](01-dashboard-overview.png) | `/` | **System Overview**: KPI metric cards (Total Runs: 10, Error Rate: 10%, Avg/P95 Latency: 54ms/67ms, Tokens: 1,420), execution list with live status indicators. |
| [`02-runs-waterfall.png`](02-runs-waterfall.png) | `/runs` | **Runs Explorer**: Historical agent execution feed with filtering by status (`completed`, `error`), agent names, tokens, duration, and trace links. |
| [`02-trace-detail.png`](02-trace-detail.png) | `/runs/[id]` | **Trace Inspection**: Parent-child execution waterfall (`CHAIN: support_agent` -> `TOOL: knowledge_base_search` -> `LLM: llm_response_synthesis`) with span timing bars and JSON payload inspector. |
| [`03-experiment-regression.png`](03-experiment-regression.png) | `/experiments` | **Evaluation Experiments**: Deterministic regression test suites (`Support v1.0 Baseline` vs. `Support v2.0 Candidate`), 100% pass rates, and scorecards. |
| [`03-experiment-compare.png`](03-experiment-compare.png) | `/experiments/compare` | **Regression Comparison**: Side-by-side experiment diff view for detecting metric regressions across prompt/model versions. |
| [`04-safety-campaign.png`](04-safety-campaign.png) | `/safety/campaigns` | **Adversarial Safety Red-Teaming**: Red-team audit campaigns with threat category breakdown, critical breach indicators, and pass rates. |
| [`05-failure-clusters.png`](05-failure-clusters.png) | `/failures` | **Failure Intelligence**: Normalized failure event feed, PII-sanitized error summaries, severity triage (`CRITICAL`, `HIGH`), and lexical fallback search. |
| [`06-alert-rules.png`](06-alert-rules.png) | `/alerts` | **Alert Rules & Incident History**: Metric threshold monitor (`Error Rate > 1.0%`), notification channels (`In-App & Webhook` with SSRF protection), and delivered incident logs. |
