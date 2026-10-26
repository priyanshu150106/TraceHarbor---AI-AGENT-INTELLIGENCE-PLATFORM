# TraceHarbor — Security Architecture & Threat Model

**Observe. Evaluate. Secure.**

TraceHarbor is designed to ingest, process, and evaluate telemetry from AI agent applications. Because agent interactions often contain sensitive business logic, user inputs, internal tools, and tokens, security is an architectural requirement at every layer.

---

## 1. Threat Model Summary

| Asset | Threat | Existing Mitigation | Remaining Risk | Recommended Next Action |
| :--- | :--- | :--- | :--- | :--- |
| **Project & Tenant Telemetry** | Unauthorized cross-tenant data access or telemetry spoofing | Cryptographically hashed API keys (SHA-256), project-scoped database queries, strict tenant boundaries enforced in ORM queries | Malicious API key theft on client side | Implement short-lived scoped tokens and automated key rotation |
| **API Keys & Credentials** | Key disclosure via logs, error messages, or storage compromise | Keys hashed with SHA-256 before storage; prefix-only storage (`th_live_...`); client redaction filters | API keys in transit over insecure plaintext HTTP | Enforce TLS/HTTPS termination in reverse proxy / load balancer |
| **Alert Webhook Endpoints** | Server-Side Request Forgery (SSRF) targeting internal VPC resources or cloud metadata services | Strict RFC 1918 private IP blocking, loopback blocking, cloud metadata (`169.254.169.254`) blocking, HTTP/HTTPS scheme whitelisting | DNS rebinding between time-of-check and time-of-request | Enforce resolution-pinned socket connections for webhook dispatchers |
| **Failure Event Payloads** | Sensitive customer data (PII, tokens, passwords) stored in plaintext vector embeddings | Multi-pass regex redaction masking API keys, JWT tokens, AWS secrets, emails, and credit cards before clustering and embedding | Novel proprietary token formats not covered by standard regexes | Allow per-project custom redaction regex rules |
| **Agent Execution Sandboxes** | Malicious agent loops, infinite recursion, or resource exhaustion during evaluation/red-teaming | Safe execution boundary timeouts (`asyncio.wait_for`), bounded input length checks (max 10,000 chars), memory limits | Subprocess/container escape if agents execute arbitrary OS shell code | Run untrusted agent adapters in isolated gVisor/Firecracker microVMs |
| **Application Error Responses** | Database connection strings, credentials, or internal stack traces leaked to callers | Global correlation middleware and centralized exception handler intercepting unhandled errors; sanitized `500 Internal server error` in production | Verbose error messages in local development mode (`DEBUG=true`) | Validate that `DEBUG=false` is enforced on staging/production deployments |
| **Evaluation LLM Judges** | Prompt injection attacks manipulating automated evaluation verdicts | System prompt separation, structured JSON schema response validation, temperature clamping, deterministic fallback | Advanced jailbreaks inducing false passes in LLM judges | Implement dual-evaluator consensus scoring with adversarial canary checks |

---

## 2. Authentication & Multi-Tenancy

### Tenant Isolation Architecture
TraceHarbor enforces logical multi-tenancy at the data layer:
1. **API Key Authentication**: Incoming requests provide credentials via `X-API-Key` or `Authorization: Bearer <key>`.
2. **Key Storage**: Raw API keys are never stored in the database. Only the SHA-256 hash and a 8-character prefix (e.g. `th_live_`) are persisted.
3. **Project Scoping**: Every telemetry record (Run, Span, FailureEvent, FailureCluster, Dataset, Experiment, SafetyCampaign) is linked directly to a `project_id`.
4. **Production Enforcement**: In production (`DEBUG=false`), `resolve_project_id` rejects unauthenticated requests with `HTTP 401 Unauthorized` or `HTTP 403 Forbidden`. Dev-mode fallback is disabled.

---

## 3. Server-Side Request Forgery (SSRF) Protections

TraceHarbor features a multi-channel alert system capable of dispatching webhooks. To prevent SSRF attacks against internal infrastructure:
- **IP Range Filtering**: Resolves destination hostnames and rejects private IP ranges (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`).
- **Loopback Blocking**: Completely prohibits `127.0.0.1`, `localhost`, and `::1`.
- **Cloud Metadata Defense**: Blocks link-local addresses, specifically AWS/GCP/Azure instance metadata endpoints (`169.254.169.254`).
- **Scheme Restriction**: Only `http://` and `https://` schemes are permitted; `file://`, `gopher://`, `ftp://` are rejected.

---

## 4. Sensitive Data Redaction & Sanitization

Before failure events are synchronized into the Failure Intelligence subsystem or converted into vector embeddings, raw error messages and stack traces undergo automated redaction:
- **API Keys & Bearer Tokens**: Replaced with `[REDACTED_API_KEY]` / `[REDACTED_TOKEN]`.
- **JWT Tokens**: Replaced with `[REDACTED_JWT]`.
- **Cloud Secrets**: AWS Access Keys, secret keys, and database connection URIs are scrubbed.
- **Canary Redaction**: In red-team safety testing, specific secret canary strings injected to measure leakage are tracked and scrubbed from user-facing reports.

---

## 5. Error Sanitization & Request Traceability

TraceHarbor intercepts all unhandled runtime exceptions:
- **Correlation IDs**: `CorrelationIdMiddleware` assigns or propagates a unique UUID4 (`X-Request-ID`) to each request.
- **Log Correlation**: Request IDs are automatically bound to structured log events via `structlog.contextvars`.
- **Sanitized Responses**: When `DEBUG=false`, internal exceptions return:
  ```json
  {
    "detail": "Internal server error",
    "request_id": "c16731ae-2755-40cc-8ad0-e303fc3fa023"
  }
  ```
  Internal database connection details, passwords, and Python stack traces are never exposed to callers.
