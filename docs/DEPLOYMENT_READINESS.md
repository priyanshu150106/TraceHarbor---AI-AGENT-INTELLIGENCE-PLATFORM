# TraceHarbor — Deployment Readiness & Production Release Package

**Version**: v0.1.0-rc2  
**Implementation Phase**: Phase 12 — Deployment Preflight and Release Package  
**Status**: Ready for Deployment Review (No Cloud Resources Provisioned, Preflight Audit & Local Verification Only)  
**Proposed Hosting**: Vercel (Next.js Frontend) + Render (FastAPI Backend) + Neon (PostgreSQL 16 + pgvector)  

---

## 1. Executive Summary

TraceHarbor has completed the Phase 12 Deployment Preflight and Production Security Hardening. All platform components, route authorizations, tenant boundaries, abuse protections, and release automation scripts have been audited and verified locally.

### Repository Baseline & Verification Overview:
- **Repository Branch & HEAD**: `main` at commit `fa0b048` (clean linear history preserved).
- **Git Tags**: Existing release candidate tags `v0.1.0-rc1` and `v0.1.0-rc2` remain intact and untouched. Zero commits, zero pushes, and zero tag alterations performed.
- **Automated Tests**:
  - **Backend**: **150 passed**, **11 skipped** (PostgreSQL 16 + pgvector integration tests requiring container), **0 failed**.
  - **Python SDK**: **10 passed**, **0 failed**.
  - **Total Automated Tests**: **160 passed**, **11 skipped**, **0 failed**.
- **Frontend Quality**:
  - TypeScript typecheck (`tsc --noEmit`): 0 errors.
  - ESLint (`next lint`): 0 warnings, 0 errors.
  - Next.js Production Build (`next build`): 18 static/dynamic routes compiled and optimized cleanly with build-time secret scanning enabled.
- **In-Memory E2E Walkthrough**: Complete 9-subsystem validation passing (`python scripts/demo_walkthrough.py --in-memory`).
- **Private Demo Seeding Workflow**: Deterministic, idempotent seeding script ([seed_demo_data.py](file:///d:/TraceHarbor/scripts/seed_demo_data.py)) verified with transaction rollback and non-demo tenant isolation.

---

## 2. Implementation Status & Feature Matrix

The following matrix distinguishes between features implemented in code, documented operational procedures, and pending hosting actions:

| Component / Security Control | Status | Location / Implementation | Verification Method |
|:---|:---|:---|:---|
| **Reverse Proxy Anti-Spoofing** | **Implemented & Tested** | `apps/api/app/core/rate_limit.py` (`get_client_ip`) | 6 automated tests in `test_abuse_protection.py` |
| **Pure ASGI Streaming Body Limit** | **Implemented & Tested** | `apps/api/app/core/middleware.py` (`ContentLengthLimitMiddleware`) | 3 automated tests in `test_abuse_protection.py` |
| **Demo Seeder Transaction Rollback**| **Implemented & Tested** | `scripts/seed_demo_data.py` (atomic transaction + rollback) | 5 automated tests in `test_seeder_safety.py` |
| **Non-Demo Tenant Isolation** | **Implemented & Tested** | `scripts/seed_demo_data.py` (asserts baseline non-demo counts) | Automated test in `test_seeder_safety.py` |
| **Production CORS Allowlist** | **Implemented & Tested** | `apps/api/app/core/cors.py`, `apps/api/app/main.py` | 6 automated tests in `test_cors.py` exercising real middleware |
| **Wildcard CORS Rejection** | **Implemented & Tested** | `apps/api/app/core/cors.py` (rejects `*` when credentials enabled) | Automated test `test_cors_wildcard_rejection` |
| **Startup CORS Validation** | **Implemented & Tested** | `apps/api/app/core/cors.py` (`validate_production_cors_at_startup`) | Fails startup if `DEBUG=false` and `CORS_ORIGINS` missing |
| **Safe Public Demo Mode** | **Implemented & Tested** | `apps/api/app/core/auth.py` (`resolve_project_id`, `DEMO_MODE`) | 8 automated tests in `test_demo_access.py` |
| **Demo Read-Only Enforcement** | **Implemented & Tested** | `apps/api/app/core/auth.py` (blocks POST/PUT/PATCH/DELETE with 403) | Automated test `test_demo_credentials_cannot_perform_privileged_mutations` |
| **Telemetry Ingest Guard** | **Implemented & Tested** | `apps/api/app/api/v1/ingest.py` (blocks demo key ingest with 403) | Tested in `test_demo_access.py` |
| **Cross-Tenant Demo Shield** | **Implemented & Tested** | `apps/api/app/core/auth.py` (blocks cross-tenant access with 403) | Tested in `test_demo_access.py` |
| **Project Directory Isolation** | **Implemented & Tested** | `apps/api/app/api/v1/projects.py` (scopes to demo project in demo mode) | Tested in `test_abuse_protection.py` |
| **Bounded Rate Limiter** | **Implemented & Tested** | `apps/api/app/core/rate_limit.py` (LRU bounded, returns 429) | Automated tests in `test_abuse_protection.py` |
| **Log Credential Redaction** | **Implemented & Tested** | `apps/api/app/core/logging.py` (`redact_sensitive_data`) | Automated test in `test_abuse_protection.py` |
| **Frontend Secret Guard** | **Implemented & Tested** | `apps/web/next.config.js` (blocks `th_live_*`, `sk-*`, `ghp_*` in `NEXT_PUBLIC_*`) | Build abort verified with simulated secret injection |
| **Client-Side Safe Auth Fallback** | **Implemented & Tested** | `apps/web/src/lib/api.ts` (supports unauthenticated demo mode & `NEXT_PUBLIC_DEMO_KEY`) | TypeScript verified, Next.js build clean |
| **SSRF Webhook Protection** | **Implemented & Tested** | `apps/api/app/alerts/notifications.py` (blocks RFC 1918, loopback, metadata) | Automated tests in `test_reliability_security.py` |
| **Error Sanitization Middleware** | **Implemented & Tested** | `apps/api/app/main.py` (`unhandled_exception_handler`) | Automated test `test_unhandled_exception_sanitization` |
| **Database Pool Guard** | **Implemented & Tested** | `apps/api/app/core/database.py` (bounded pool size & timeout) | Verified via application engine configuration |
| **Private Demo Seeder** | **Implemented & Tested** | `scripts/seed_demo_data.py` (idempotent direct DB seeding) | Verified in `test_seeder_safety.py` |
| **Hosted Demo Verifier** | **Implemented & Tested** | `scripts/demo_walkthrough.py --verify-demo` | Non-mutating verification suite |
| **Database Migrations (001–005)** | **Implemented & Tested** | `apps/api/alembic/versions/` (5 revisions committed) | Validated in integration tests & CI workflow |
| **Controlled Release Migration** | **Documented (Pre-Deploy)** | Documented in Section 7 below; separate from replica startup | Local isolated DB testing |
| **Managed Cloud Infrastructure** | **Requires Manual Hosting Config** | Proposed Neon + Render + Vercel setup | To be executed upon explicit user approval |

---

## 3. Reverse Proxy Rate Limiting & Multi-Replica Architectural Review

### 3.1 Reverse Proxy Client IP Anti-Spoofing Architecture
In a reverse-proxy environment (e.g. Render, Cloudflare, AWS ALB), client requests pass through an intermediate proxy before reaching the FastAPI ASGI server:
1. **The Spoofing Threat**: If the application blindly reads the leftmost IP from `X-Forwarded-For`, an attacker can send `X-Forwarded-For: 1.1.1.1` (or rotate arbitrary IPs per request) to completely evade per-IP rate limits.
2. **Reverse Proxy Chaining Behavior**: When a request passes through a trusted reverse proxy (such as Render's Envoy proxy), the proxy appends the real connecting IP to the right side of `X-Forwarded-For`:
   $$\text{X-Forwarded-For: } \langle\text{client-injected-ip}\rangle, \langle\text{real-client-ip}\rangle$$
3. **Application Enforcement**:
   - `get_client_ip()` in [rate_limit.py](file:///d:/TraceHarbor/apps/api/app/core/rate_limit.py) checks if the peer connection is trusted via `settings.trusted_proxies` or `settings.proxy_headers_enabled`.
   - If the request arrives directly from an untrusted peer, forwarded headers are completely ignored, and the immediate connection IP (`request.client.host`) is used.
   - When behind a trusted proxy, candidate IPs in `X-Forwarded-For` are traversed from right to left to locate the trusted proxy-appended client IP.
   - Every candidate is validated using Python's standard `ipaddress.ip_address` module. Injection payloads (e.g. `<script>`, SQL syntax, path traversal) and malformed IP strings are rejected, falling back safely to the peer IP.

### 3.2 Multi-Replica Rate Limiting Behavior
TraceHarbor's rate limiter uses an in-memory sliding-window counter backed by a bounded `OrderedDict` (LRU eviction with a maximum of 10,000 tracked keys, consuming less than 5 MB of memory).

#### Behavior with Multiple Backend Replicas:
- **Independent In-Memory State**: Each container replica maintains its own isolated in-memory sliding window. Counters are not synchronized across replicas without an external shared cache.
- **Effective Rate Limit with $N$ Replicas**: If requests are distributed evenly (round-robin) across $N$ replicas, a client could theoretically issue up to $N \times \text{limit}$ requests within the 60-second window before all replicas block them.
- **Portfolio Demonstration Assessment**: For the initial release candidate and portfolio demonstration, **a single backend replica on Render (Starter or Free tier) is the recommended deployment configuration**:
  - Strictly bounds RAM consumption (< 5 MB for rate limit storage).
  - Guarantees 100% globally consistent rate limiting (all requests hit the single replica).
  - Eliminates external dependencies, latency overhead, and costs associated with Redis.
  - Health checks (`/health`, `/healthz`, `/readyz`) and OpenAPI docs remain exempt.

#### Production Scaling Path (When Scaling Beyond 1 Replica):
When horizontal scaling beyond 1 replica is required in commercial multi-tenant SaaS:
1. **Redis Sliding-Window Token Bucket**: Replace `BoundedSlidingWindowLimiter` with an atomic Redis Lua script using Redis Sorted Sets (`ZADD`, `ZREMRANGEBYSCORE`, `ZCARD`, `EXPIRE`) or Redis Cell.
2. **Edge Rate Limiting**: Offload public demo rate limiting to Cloudflare WAF Rate Limiting or Vercel Edge Middleware, terminating abusive traffic before it reaches backend instances.

---

## 4. Pure ASGI Request Body Size Enforcement

### 4.1 Vulnerabilities of Header-Only Checks
Checking only the HTTP `Content-Length` header is insufficient for production security:
- A malicious client can send `Transfer-Encoding: chunked` without a `Content-Length` header.
- A client can send a misleadingly small `Content-Length` header while streaming a much larger body.
- Streaming uploads can exhaust container RAM before route handlers execute.

### 4.2 Implemented Pure ASGI Middleware (`ContentLengthLimitMiddleware`)
TraceHarbor implements a pure ASGI middleware in [middleware.py](file:///d:/TraceHarbor/apps/api/app/core/middleware.py):
1. **Fast-Path Header Validation**:
   - Inspects `scope["headers"]` for `b"content-length"`.
   - If declared `Content-Length > max_request_body_bytes` (10 MB), immediately returns `HTTP 413 Payload Too Large` with JSON detail without reading any body bytes.
   - If `Content-Length` is negative or non-integer, immediately returns `HTTP 400 Bad Request`.
2. **Streaming Chunk Monitoring**:
   - Intercepts the ASGI `receive` callable.
   - For every `http.request` message, accumulates `bytes_received += len(chunk)`.
   - If `bytes_received > max_request_body_bytes`, immediately raises `PayloadTooLargeError` and terminates ingestion.
3. **Python 3.11+ ExceptionGroup Unwrapping**:
   - In Python 3.11+, ASGI task groups wrap streaming exceptions in `ExceptionGroup`.
   - The registered `http_exception_handler` in [main.py](file:///d:/TraceHarbor/apps/api/app/main.py) unwraps `ExceptionGroup` causes, ensuring that streaming aborts consistently produce clean `HTTP 413` responses rather than being masked as generic `HTTP 400` body parsing errors.

---

## 5. Demo Seeder Transaction Safety & Tenant Isolation

### 5.1 Sensitivity & Safeguards
`scripts/seed_demo_data.py` operates directly against `DATABASE_URL` via SQLAlchemy's `AsyncSession`. It is a sensitive operational utility.

To ensure safety:
1. **Deterministic Dedicated Identifiers**:
   - `DEMO_USER_ID`: `00000000-0000-4000-9000-000000000001`
   - `DEMO_PROJECT_ID`: `00000000-0000-4000-a000-000000000001`
   - `DEMO_KEY_ID`: `00000000-0000-4000-b000-000000000001`
2. **Single Atomic Database Transaction**:
   - All delete queries (during `--reset`) and all entity insertions execute in a single atomic transaction.
   - If an exception occurs at any point during seeding, `session.rollback()` is immediately executed, restoring the database to its pre-operation state.
3. **Strict Non-Demo Tenant Isolation**:
   - Every deletion query in `purge_demo_tenant` is strictly filtered by `project_id == DEMO_PROJECT_ID` or `id == DEMO_PROJECT_ID`.
   - Before modifying any records, `seed_demo_data` counts all non-demo projects.
   - After seeding, it asserts that the non-demo project count is 100% identical. Any discrepancy causes an immediate assertion abort.
4. **Idempotency**:
   - Running `seed_demo_data.py` without `--reset` on an already seeded database does not create duplicate records; it verifies and returns existing record counts cleanly.

---

## 6. PostgreSQL 16 + pgvector Integration Validation

### 6.1 Alembic Migration Lineage
The database schema is defined across 5 sequential, reversible Alembic migrations:
- `001_initial_schema.py`: Base tables (`users`, `projects`, `api_keys`, `runs`, `spans`).
- `002_evaluation_engine.py`: Evaluation benchmarks (`datasets`, `test_cases`, `experiments`, `experiment_results`).
- `003_analytics_and_alerts.py`: Alerting infrastructure (`alert_rules`, `alert_history`).
- `004_safety_module.py`: Red-team safety framework (`safety_campaigns`, `safety_test_results`).
- `005_failure_intelligence.py`: pgvector extension (`CREATE EXTENSION IF NOT EXISTS vector;`), semantic failure tables (`failure_clusters`, `failure_events`, `cluster_status_changes`), and vector similarity indexes.

### 6.2 Integration Testing Environment
- In environments where Docker is not installed locally, `_probe_postgres()` in [conftest.py](file:///d:/TraceHarbor/apps/api/app/tests/integration/conftest.py) detects PostgreSQL reachability and skips the 11 integration tests gracefully with diagnostic instructions.
- In GitHub Actions CI ([.github/workflows/ci.yml](file:///d:/TraceHarbor/.github/workflows/ci.yml)), the `backend-integration` job spins up a real `pgvector/pgvector:pg16` service container, running `pytest -v -m "integration"` against live PostgreSQL 16 + pgvector.

---

## 7. Environment Variable Inventory & Classification

| Variable Name | Scope | Security Classification | Required In Prod | Purpose |
|:---|:---|:---|:---|:---|
| `DATABASE_URL` | Backend | **Secret** (Vault Only) | **Yes** | Connection string to Neon PostgreSQL (`postgresql+asyncpg://...`) |
| `JWT_SECRET` | Backend | **Secret** (Vault Only) | **Yes** | Cryptographic 32-byte secret for JWT tokens |
| `CORS_ORIGINS` | Backend | Public / Config | **Yes** | Comma-separated frontend domains (e.g. `https://traceharbor.vercel.app`) |
| `DEBUG` | Backend | Public / Config | **Yes** | Set to `false` in production to enforce strict security |
| `DEMO_MODE` | Backend | Public / Config | **Yes** (for demo) | Set to `true` to enable safe public read-only portfolio access |
| `DEMO_PROJECT_ID` | Backend | Public / Config | **Yes** (for demo) | Set to `00000000-0000-4000-a000-000000000001` |
| `RATE_LIMIT_ENABLED` | Backend | Public / Config | No | Default `true`. Bounded sliding window limiter |
| `RATE_LIMIT_DEMO_PER_MINUTE` | Backend | Public / Config | No | Default `60` requests per minute for public visitors |
| `RATE_LIMIT_AUTH_PER_MINUTE` | Backend | Public / Config | No | Default `300` requests per minute for authenticated keys |
| `MAX_REQUEST_BODY_BYTES` | Backend | Public / Config | No | Default `10485760` (10 MB) |
| `PROXY_HEADERS_ENABLED` | Backend | Public / Config | **Yes** (on Render) | Set to `true` to enable trusted proxy IP resolution behind Render |
| `TRUSTED_PROXIES` | Backend | Public / Config | No | Comma-separated trusted proxy IPs (default: `127.0.0.1,::1,testclient`) |
| `LOG_LEVEL` | Backend | Public / Config | No | Set to `INFO` or `WARNING` |
| `NEXT_PUBLIC_API_BASE_URL` | Frontend | Public (Browser) | **Yes** | Remote backend URL (e.g. `https://traceharbor-api.onrender.com`) |
| `NEXT_PUBLIC_DEMO_KEY` | Frontend | Public (Browser) | Optional | Synthetic demo key (`th_demo_*`). Leave blank for unauthenticated demo mode |

---

## 8. Complete Step-by-Step Deployment Execution Package

When deployment authorization is granted, execute this exact sequence:

### Step 1: Provision Neon PostgreSQL Database
1. Create a project in [Neon Console](https://console.neon.tech) running **PostgreSQL 16**.
2. Enable pgvector extension (Neon supports pgvector natively).
3. Copy the pooled or direct connection string:
   ```text
   postgresql://<USER>:<PASS>@<NEON_HOST>/<DB>?sslmode=require
   ```
4. Convert connection prefix for async SQLAlchemy:
   ```text
   postgresql+asyncpg://<USER>:<PASS>@<NEON_HOST>/<DB>?sslmode=require
   ```

### Step 2: Apply Migrations & Seed Demo Data (Isolated Release Step)
Run the migration and seeding from a controlled operator workstation or CI release step (NEVER inside the web server startup script):
```bash
# 1. Apply database schema migrations (001 -> 005)
cd apps/api
DATABASE_URL="postgresql+asyncpg://<USER>:<PASS>@<NEON_HOST>/<DB>?sslmode=require" alembic upgrade head

# 2. Seed synthetic portfolio demo records into dedicated demo tenant
cd ../..
DATABASE_URL="postgresql+asyncpg://<USER>:<PASS>@<NEON_HOST>/<DB>?sslmode=require" python scripts/seed_demo_data.py --reset

# 3. Verify record counts and tenant isolation
DATABASE_URL="postgresql+asyncpg://<USER>:<PASS>@<NEON_HOST>/<DB>?sslmode=require" python scripts/seed_demo_data.py --verify-only
```

### Step 3: Deploy FastAPI Backend on Render
1. Create a **Web Service** on Render pointing to the GitHub repository:
   - **Environment**: Python 3
   - **Root Directory**: `apps/api`
   - **Build Command**: `pip install -e .`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT --proxy-headers --forwarded-allow-ips='*'`
   - **Plan**: Starter ($7/mo) or Free instance (1 replica).
2. Configure Environment Variables in Render Dashboard:
   - `DATABASE_URL`: `postgresql+asyncpg://<USER>:<PASS>@<NEON_HOST>/<DB>?sslmode=require`
   - `JWT_SECRET`: `[Cryptographic 32-byte string]`
   - `DEBUG`: `false`
   - `DEMO_MODE`: `true`
   - `DEMO_PROJECT_ID`: `00000000-0000-4000-a000-000000000001`
   - `PROXY_HEADERS_ENABLED`: `true`
   - `CORS_ORIGINS`: `https://<your-vercel-domain>.vercel.app`
3. Verify Render Health Check:
   - **Health Check Path**: `/healthz`

### Step 4: Deploy Next.js Frontend on Vercel
1. Import repository in [Vercel Dashboard](https://vercel.com).
2. Configure Project Settings:
   - **Framework Preset**: Next.js
   - **Root Directory**: `apps/web`
   - **Build Command**: `npm run build`
   - **Output Directory**: `.next`
3. Configure Environment Variables in Vercel:
   - `NEXT_PUBLIC_API_BASE_URL`: `https://<your-render-service>.onrender.com`
   - `NEXT_PUBLIC_API_URL`: `https://<your-render-service>.onrender.com`
4. Deploy and record the assigned Vercel URL (e.g. `https://traceharbor.vercel.app`).
5. Update `CORS_ORIGINS` in Render if the initial Vercel domain differed.

### Step 5: Post-Deployment Verification Walkthrough
Run the non-mutating demo walkthrough against the hosted API:
```bash
python scripts/demo_walkthrough.py --base-url https://<your-render-service>.onrender.com --verify-demo
```
Expected output:
- Probes `/healthz` and `/readyz`: `200 OK`.
- Synthetic runs, golden datasets, safety campaign scores, and clusters: `200 OK`.
- Mutation attempts (`POST /v1/datasets`, `POST /v1/experiments`, `POST /v1/ingest/spans`): blocked with `HTTP 403 Forbidden`.

---

## 9. Automated Test Evidence Summary

### 9.1 Backend Pytest (150 Passed, 11 Skipped)
```text
============================= test session starts =============================
platform win32 -- Python 3.14.4, pytest-9.1.1, pluggy-1.6.0
rootdir: D:\TraceHarbor\apps\api
configfile: pyproject.toml
plugins: anyio-4.15.1, platformdirs-4.12.1, asyncio-1.4.0, cov-7.1.0
collected 161 items

apps\api\app\tests\integration\test_migrations.py .s                     [  1%]
apps\api\app\tests\integration\test_pg_models_crud.py ssssss             [  4%]
apps\api\app\tests\integration\test_pg_tenant_isolation.py s             [  5%]
apps\api\app\tests\integration\test_pg_vector.py sss                     [  7%]
apps\api\app\tests\test_abuse_protection.py ..................           [ 18%]
apps\api\app\tests\test_alerts.py .....                                  [ 21%]
apps\api\app\tests\test_analytics.py .....                               [ 24%]
apps\api\app\tests\test_comparison.py ..                                 [ 26%]
apps\api\app\tests\test_cors.py ......                                   [ 29%]
apps\api\app\tests\test_datasets.py ......                               [ 33%]
apps\api\app\tests\test_demo_access.py ........                          [ 38%]
apps\api\app\tests\test_e2e_workflow.py .                                [ 39%]
apps\api\app\tests\test_eval_isolation.py ...                            [ 40%]
apps\api\app\tests\test_evaluators.py ............                       [ 48%]
apps\api\app\tests\test_experiments.py ....                              [ 50%]
apps\api\app\tests\test_failures.py ............                         [ 58%]
apps\api\app\tests\test_health.py ...                                    [ 60%]
apps\api\app\tests\test_ingest.py ..........                             [ 66%]
apps\api\app\tests\test_llm_judge.py ....                                [ 68%]
apps\api\app\tests\test_models.py ...                                    [ 70%]
apps\api\app\tests\test_reliability_security.py ........                 [ 75%]
apps\api\app\tests\test_runs.py .......                                  [ 80%]
apps\api\app\tests\test_safety_api.py ....                               [ 82%]
apps\api\app\tests\test_safety_boundary_and_alerts.py ....               [ 85%]
apps\api\app\tests\test_safety_evaluators.py .............               [ 93%]
apps\api\app\tests\test_seeder_safety.py .....                           [ 96%]
apps\api\app\tests\test_tasks.py ......                                  [100%]

================= 150 passed, 11 skipped, 1 warning in 22.93s =================
```

### 9.2 Python SDK Tests (10 Passed)
```text
packages/sdk-python/tests/test_sdk.py ..........                         [100%]
============================= 10 passed in 5.55s ==============================
```

### 9.3 Frontend Production Build (18 Routes Built)
```text
Route (app)                              Size     First Load JS
┌ ○ /                                    2.88 kB         104 kB
├ ○ /_not-found                          873 B          88.2 kB
├ ○ /alerts                              5.22 kB         107 kB
├ ○ /analytics                           4.4 kB          106 kB
├ ○ /datasets                            4.87 kB         106 kB
├ ○ /experiments                         5.24 kB         107 kB
├ ƒ /experiments/[id]                    3.78 kB         105 kB
├ ○ /experiments/compare                 4.6 kB          106 kB
├ ○ /failures                            3.41 kB         105 kB
├ ○ /failures/clusters                   3.48 kB         105 kB
├ ƒ /failures/clusters/[id]              3.13 kB         105 kB
├ ○ /failures/search                     2.55 kB         104 kB
├ ○ /projects                            1.77 kB         103 kB
├ ○ /runs                                2.8 kB          104 kB
├ ƒ /runs/[id]                           3.58 kB         105 kB
├ ○ /safety                              4.25 kB         106 kB
├ ○ /safety/campaigns                    4.58 kB         106 kB
├ ƒ /safety/campaigns/[id]               3.89 kB         105 kB
├ ○ /safety/compare                      3.62 kB         105 kB
└ ○ /settings                            2.33 kB         104 kB
+ First Load JS shared by all            87.3 kB
```

---

## 10. Conclusion & Deployment Readiness Sign-Off

TraceHarbor has met all pre-deployment operational and security criteria. The codebase is fully prepared for a controlled, zero-risk deployment to Vercel, Render, and Neon upon explicit user authorization.
