# TraceHarbor — Cloud Deployment Runbook

**Document Version**: 2.0.0 (Zero-Cost Edition)  
**Target Release**: v0.1.0  
**Target Hosting Stack ($0.00 / mo Budget)**:
- **Database**: Neon (PostgreSQL 16 + pgvector, Free Tier — $0.00/mo)
- **Backend API**: Vercel Project 2 (FastAPI Serverless via `@vercel/python`, Hobby Tier — $0.00/mo)
- **Frontend Dashboard**: Vercel Project 1 (Next.js 14 App Router, Hobby Tier — $0.00/mo)
- **CI / Source Repository**: GitHub Free Tier ($0.00/mo)
**Total Monthly Cost**: **$0.00 / month** (₹0.00 / month)  
**Status**: Zero-Cost Deployment Runbook  

---

## 1. Zero-Cost Target Architecture ($0.00/mo)

TraceHarbor is architected for high security, strict tenant isolation, and zero operating costs on standard cloud free tiers:

```mermaid
flowchart TD
    subgraph PublicUsers["Public Reviewers & Recruiters"]
        Browser["Web Browser (Portfolio Visitor)"]
        Tester["Operator / CI Walkthrough"]
    end

    subgraph VercelFrontend["Vercel Project 1: Frontend (Hobby Tier — $0)"]
        NextJS["Next.js 14 Dashboard (apps/web)<br/>React 18, Tailwind CSS, Lucide Icons<br/>Static + SSR Routes"]
    end

    subgraph VercelBackend["Vercel Project 2: Backend (Hobby Tier — $0)"]
        VercelPython["FastAPI Serverless Function (apps/api)<br/>Entrypoint: api/index.py<br/>Native Python 3.12 Runtime"]
        RateLimiter["Bounded LRU Sliding Window Rate Limiter<br/>(Anti-spoofing reverse proxy support)"]
        BodyGuard["Pure ASGI Body Size Guard (4.5 MB serverless limit)"]
        AuthShield["Auth Shield & Demo Scoper (DEMO_MODE=true)"]
    end

    subgraph NeonCloud["Neon Cloud: Database (Free Tier — $0)"]
        PgPooler["Neon Connection Pooler (PgBouncer)"]
        PostgresDB[("PostgreSQL 16 Database<br/>(Strict project_id scoping)")]
        PgVectorExt["pgvector Extension<br/>(Dense Failure Embeddings)"]
    end

    Browser -->|HTTPS| NextJS
    NextJS -->|REST API Requests| VercelPython
    Tester -->|Read-Only Verification| VercelPython
    VercelPython --> RateLimiter --> BodyGuard --> AuthShield
    AuthShield -->|postgresql+asyncpg| PgPooler
    PgPooler --> PostgresDB
    PostgresDB --- PgVectorExt
```

---

## 2. Strict Zero-Cost Provider Constraints

| Provider | Service | Tier | Monthly Cost | Free Quotas & Platform Boundaries |
|:---|:---|:---|:---:|:---|
| **Vercel** | Next.js Frontend (`apps/web`) | Hobby | **$0.00** | 100 GB bandwidth, free SSL, global Edge CDN. |
| **Vercel** | FastAPI Backend (`apps/api`) | Hobby | **$0.00** | Python 3.12 Serverless Function, 4.5 MB request/response ceiling, 10s default execution limit. |
| **Neon** | PostgreSQL 16 + pgvector | Free | **$0.00** | 1 project, **1 GB storage**, **100 CU-hours/mo**, auto-suspend when idle. |
| **GitHub** | Repository & Actions CI | Free | **$0.00** | 2,000 free Actions CI minutes/month. |
| **TOTAL** | **All Services** | **Free** | **$0.00 / mo** | **Strictly ₹0.00 / month ($0.00 USD).** |

---

## 3. Exact Service Configuration

| Service Tier | Provider | Service Name | Service Type | Runtime / Engine |
|:---|:---|:---|:---|:---|
| **Database** | Neon | `traceharbor-prod` | Serverless PostgreSQL | PostgreSQL 16 with pgvector |
| **Backend API** | Vercel | `traceharbor-api` | Serverless Function | Python 3.12 (FastAPI via `api/index.py`) |
| **Frontend** | Vercel | `traceharbor-web` | Web Application | Next.js 14 (Node.js 20) |

---

## 4. Platform Constraints & Operational Boundaries

1. **Payload Size Boundaries**:
   - Vercel Serverless Functions enforce a strict **4.5 MB** maximum payload limit for request bodies and responses.
   - TraceHarbor configures `max_request_body_bytes = 4194304` (4 MB) in `apps/api/app/core/config.py`, rejecting oversized uploads before the platform threshold is crossed.
   - All dataset and telemetry batch endpoints enforce strict pagination (`limit` default 50, maximum 100), keeping typical responses under 50 KB.
2. **Execution Duration**:
   - Vercel Hobby serverless functions have a 10s default execution timeout (max 60s).
   - Long-running async background tasks do not persist indefinitely; mutating long-running operations are disabled for public demo users (HTTP 403) and immediate responses are returned.
3. **Client IP & Anti-Spoofing on Vercel**:
   - Vercel's edge network overwrites `X-Forwarded-For` with the true connecting client IP address, preventing client-side spoofing.
   - In addition, Vercel injects `X-Vercel-Forwarded-For`.
   - The rate limiter resolves `X-Vercel-Forwarded-For` and Vercel's verified `X-Forwarded-For` when `PROXY_HEADERS_ENABLED=true`. Untrusted direct client connections ignore forwarded headers.
4. **Rate Limiting Concurrency**:
   - The in-memory sliding window rate limiter operates within each ephemeral serverless instance. Under free-tier serverless auto-scaling, this protects individual worker containers from query flooding without requiring a billable Redis cluster.

---

## 5. Zero-Cost Free Tier Ledger

| Service | Plan | Monthly Cost (USD) | Monthly Cost (INR) | Free Tier Limitations & Quotas |
|:---|:---|:---:|:---:|:---|
| **Neon PostgreSQL** | Free | $0.00 | ₹0 | **1 GB storage**, **100 CU-hours/month**, auto-suspends after 5 min idle (wakes in ~1s). |
| **Vercel Backend** | Hobby | $0.00 | ₹0 | 4.5 MB payload limit, 10s execution duration, 100 GB bandwidth, serverless Python. |
| **Vercel Frontend** | Hobby | $0.00 | ₹0 | 100 GB bandwidth, global Edge caching, automatic HTTPS. |
| **TOTAL** | Free | **$0.00 / mo** | **₹0 / mo** | **100% Zero-Cost Portfolio Demonstration.** |

---

## 6. Secret-Generation Instructions

All production secrets must be generated locally using cryptographically secure random number generators. **Never share, commit, or print raw secrets in chat.**

### Generate JWT Secret:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```
*Output*: A 43-character base64 URL-safe random string.

### Generate Database Password:
```bash
python -c "import secrets; print(secrets.token_hex(16))"
```
*Output*: A 32-character hexadecimal random string.

---

## 7. Neon Database Provisioning Sequence

1. Log into [Neon Console](https://console.neon.tech).
2. Click **Create Project**:
   - **Project Name**: `traceharbor-prod`
   - **Postgres Version**: `16`
   - **Region**: Select region closest to Render (e.g. `US East (Ohio)` / `us-east-2` if Render is in `Oregon`/`Ohio`, or `Frankfurt` if Render is in `Frankfurt`).
3. Neon automatically provisions the primary database and displays connection credentials.
4. Copy the connection string. Neon provides:
   - Pooled connection string (`-pooler` in hostname): Recommended for FastAPI asyncpg connection pool.
   - Example format: `postgresql://th_owner:<PASSWORD>@ep-xyz-pooler.us-east-2.aws.neon.tech/neondb?sslmode=require`
5. Prefix with `postgresql+asyncpg://` for SQLAlchemy:
   ```text
   postgresql+asyncpg://th_owner:<PASSWORD>@ep-xyz-pooler.us-east-2.aws.neon.tech/neondb?sslmode=require
   ```

---

## 8. pgvector Extension Initialization

Neon supports `pgvector` natively. Alembic migration `005_failure_intelligence.py` includes `CREATE EXTENSION IF NOT EXISTS vector;`.

To verify pgvector availability manually via Neon SQL Editor:
```sql
CREATE EXTENSION IF NOT EXISTS vector;
SELECT * FROM pg_extension WHERE extname = 'vector';
```

---

## 9. Controlled Database Migration Command

Execute Alembic migrations from an isolated release workstation or CI step directly against the database URL. **Do not run migrations on API container startup.**

```bash
cd apps/api

# Run all 5 sequential revisions (001 -> 005)
DATABASE_URL="postgresql+asyncpg://<USER>:<PASS>@<HOST>/<DB>?sslmode=require" alembic upgrade head

# Verify current revision
DATABASE_URL="postgresql+asyncpg://<USER>:<PASS>@<HOST>/<DB>?sslmode=require" alembic current
# Expected Output: 005_failure_intelligence (head)
```

---

## 10. Private Synthetic Demo Seeding Command

Populate the database with clean, realistic synthetic demonstration data. This utility guarantees 100% tenant isolation and atomic transaction rollback.

```bash
cd D:\TraceHarbor

# 1. Seed demo tenant (idempotent, rolls back on error)
DATABASE_URL="postgresql+asyncpg://<USER>:<PASS>@<HOST>/<DB>?sslmode=require" python scripts/seed_demo_data.py --reset

# 2. Verify record counts and non-demo isolation
DATABASE_URL="postgresql+asyncpg://<USER>:<PASS>@<HOST>/<DB>?sslmode=require" python scripts/seed_demo_data.py --verify-only
```

*Expected Verification Output*:
```text
=======================================================
 DEMO TENANT VERIFICATION REPORT
 Target Project ID : 00000000-0000-4000-a000-000000000001
=======================================================
 • Runs                  : 2 record(s)
 • Spans                 : 5 record(s)
 • Datasets              : 2 record(s)
 • Test Cases            : 4 record(s)
 • Experiments           : 1 record(s)
 • Safety Campaigns      : 1 record(s)
 • Failure Clusters      : 1 record(s)
 • Failure Events        : 1 record(s)
 • Alert Rules           : 1 record(s)
=======================================================
 [PASS] 100% of verified records belong strictly to the demo project.
 [PASS] Zero cross-tenant data leaked or modified.
```

---

## 11. Vercel Backend Deployment (Project 2 — $0.00/mo)

The backend is deployed as a serverless ASGI application via Vercel's native Python runtime (`@vercel/python`).

1. In [Vercel Dashboard](https://vercel.com), click **Add New...** -> **Project**.
2. Import the `TraceHarbor` repository.
3. Configure Project Settings:
   - **Project Name**: `traceharbor-api`
   - **Framework Preset**: `Other`
   - **Root Directory**: `apps/api`
   - **Build Command**: *(leave empty; Vercel detects requirements.txt)*
   - **Output Directory**: *(leave default)*
4. Configure Environment Variables in Vercel for the Backend:

| Key | Value / Recommendation | Note |
|:---|:---|:---|
| `DATABASE_URL` | `postgresql+asyncpg://<USER>:<PASS>@<HOST>/<DB>?sslmode=require` | Use Neon pooled connection URL (`-pooler`) |
| `DB_POOL_SIZE` | `2` | Optimized for serverless functions |
| `DB_MAX_OVERFLOW` | `3` | Prevents Neon connection exhaustion |
| `DB_POOL_RECYCLE` | `300` | Recycles idle connections cleanly |
| `JWT_SECRET` | `<Generated 32-byte cryptographic secret>` | Required for authentication |
| `DEBUG` | `false` | Enforces production mode |
| `DEMO_MODE` | `true` | Enables safe public demo mode |
| `DEMO_PROJECT_ID` | `00000000-0000-4000-a000-000000000001` | Fixed UUID for the demo tenant |
| `CORS_ORIGINS` | `https://traceharbor-web.vercel.app` | Set to your Vercel frontend URL |
| `RATE_LIMIT_ENABLED` | `true` | Enables anti-abuse rate limiter |
| `RATE_LIMIT_DEMO_PER_MINUTE` | `60` | 60 requests/minute for demo users |
| `RATE_LIMIT_AUTH_PER_MINUTE` | `300` | 300 requests/minute for authenticated users |
| `MAX_REQUEST_BODY_BYTES` | `4500000` | 4.5 MB serverless function payload limit |
| `PROXY_HEADERS_ENABLED` | `true` | Honors reverse proxy headers |
| `TRUSTED_PROXIES` | `127.0.0.1,::1,testclient` | Reverse proxy trust list |
| `LOG_LEVEL` | `INFO` | Standard structured logging |

5. Deploy. Record the assigned backend URL (e.g. `https://traceharbor-api.vercel.app`).

---

## 12. Vercel Frontend Deployment (Project 1 — $0.00/mo)

The frontend is deployed on Vercel's Edge/Next.js hosting with zero hosting cost.

1. In [Vercel Dashboard](https://vercel.com), click **Add New...** -> **Project**.
2. Import the `TraceHarbor` repository.
3. Configure Project Settings:
   - **Project Name**: `traceharbor-web`
   - **Framework Preset**: `Next.js`
   - **Root Directory**: `apps/web`
   - **Build Command**: `npm run build`
   - **Output Directory**: `.next`
   - **Node.js Version**: `20.x`
4. Configure Environment Variables in Vercel for the Frontend:

| Key | Value | Note |
|:---|:---|:---|
| `NEXT_PUBLIC_API_BASE_URL` | `https://traceharbor-api.vercel.app` | Assigned URL of Project 2 (no trailing slash) |
| `NEXT_PUBLIC_API_URL` | `https://traceharbor-api.vercel.app` | Secondary alias for API base URL |
| `NEXT_PUBLIC_DEMO_KEY` | *(leave empty)* | Triggers automatic unauthenticated demo access |

5. Deploy. Record the assigned frontend URL (e.g. `https://traceharbor-web.vercel.app`).
6. If the assigned frontend URL differs from `CORS_ORIGINS`, update `CORS_ORIGINS` in the backend project settings.

---

## 13. CORS Configuration

- FastAPI backend requires explicit origin URLs in `CORS_ORIGINS`.
- Wildcards (`*`) are prohibited and rejected at startup when `DEBUG=false`.
- Ensure exact matching without trailing slash: `https://traceharbor-web.vercel.app`.
- If custom domains or preview deployments are added later, add them comma-separated:
  ```text
  CORS_ORIGINS=https://traceharbor-web.vercel.app
  ```

---

## 14. Health and Readiness Verification

Test backend probes immediately after deployment:

```bash
# 1. Liveness probe (returns 200 alive)
curl -i https://traceharbor-api.vercel.app/healthz

# 2. Readiness probe (validates database connectivity)
curl -i https://traceharbor-api.vercel.app/readyz

# 3. Platform metadata
curl -i https://traceharbor-api.vercel.app/health
```

---

## 15. Public Demo Access Validation

Verify that public unauthenticated reads succeed while mutations and cross-tenant queries are blocked:

```bash
# 1. Unauthenticated read of synthetic runs (Must return 200 OK)
curl -i https://traceharbor-api.vercel.app/v1/runs

# 2. Unauthenticated read of synthetic failure clusters (Must return 200 OK)
curl -i https://traceharbor-api.vercel.app/v1/failures/clusters

# 3. Attempt mutation without key (Must return 403 Forbidden)
curl -i -X POST https://traceharbor-api.vercel.app/v1/datasets \
  -H "Content-Type: application/json" \
  -d '{"name": "Unauthorized Dataset"}'

# 4. Attempt telemetry ingestion without live key (Must return 401/403)
curl -i -X POST https://traceharbor-api.vercel.app/v1/ingest/spans \
  -H "Content-Type: application/json" \
  -d '{"runs": [], "spans": []}'
```

---

## 16. Live Walkthrough Verification

Execute the non-mutating demo verification suite against the live deployment:

```bash
python scripts/demo_walkthrough.py --base-url https://traceharbor-api.onrender.com --verify-demo
```

*Expected Result*: All 10 verification steps succeed with `[PASS]`, confirming end-to-end operational health.

---

## 17. Rollback Procedure

If unexpected errors occur during deployment:

1. **Frontend Rollback (Vercel)**:
   - In Vercel Dashboard -> **Deployments**, click the previous successful deployment -> **Instant Rollback**.
2. **Backend Rollback (Render)**:
   - In Render Dashboard -> **Deploys**, click the prior working build -> **Rollback to this deploy**.
3. **Database Schema Rollback (Alembic)**:
   - To roll back a migration:
     ```bash
     cd apps/api
     DATABASE_URL="..." alembic downgrade -1
     ```
4. **Data Reset**:
   - To cleanly re-seed synthetic data:
     ```bash
     DATABASE_URL="..." python scripts/seed_demo_data.py --reset
     ```

---

## 18. Post-Deployment Security Checklist

- [ ] `DEBUG=false` confirmed on Render.
- [ ] `DEMO_MODE=true` confirmed on Render.
- [ ] `DEMO_PROJECT_ID` set to `00000000-0000-4000-a000-000000000001`.
- [ ] `PROXY_HEADERS_ENABLED=true` set on Render.
- [ ] `CORS_ORIGINS` strictly set to the Vercel domain (no wildcard `*`).
- [ ] `NEXT_PUBLIC_*` contains zero secret tokens (`th_live_*`, `sk-*`, database credentials).
- [ ] Mutation endpoints (`POST`, `PUT`, `PATCH`, `DELETE`) return `HTTP 403` to unauthenticated callers.
- [ ] Rate limiting active (`X-RateLimit-Limit`, `X-RateLimit-Remaining` headers present in responses).
- [ ] Request bodies > 10 MB rejected with `HTTP 413`.
- [ ] Database credentials not logged in Render runtime logs (verified via log redaction).

