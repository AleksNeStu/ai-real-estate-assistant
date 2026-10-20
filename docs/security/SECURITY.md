# Security Policy — AI Real Estate Assistant V4

**Last Updated:** 26.01.2026
**Version:** 4.0

This document outlines the security measures implemented in the AI Real Estate Assistant platform and provides guidelines for secure deployment and operation.

---

## Table of Contents

- [Security Architecture](#security-architecture)
- [Authentication & Authorization](#authentication--authorization)
- [Input Validation & Sanitization](#input-validation--sanitization)
- [Rate Limiting & DDoS Protection](#rate-limiting--ddos-protection)
- [API Security](#api-security)
- [Frontend Security](#frontend-security)
- [Resilience & Availability](#resilience--availability)
- [Secrets Management](#secrets-management)
- [Dependency Security](#dependency-security)
- [Production Deployment Checklist](#production-deployment-checklist)
- [Incident Response](#incident-response)
- [Reporting Security Issues](#reporting-security-issues)

---

## Security Architecture

The platform follows defense-in-depth principles with multiple layers of security:

### Backend Security Layers
1. **API Key Authentication** - Required for all API endpoints
2. **Input Sanitization** - All user inputs are validated and sanitized
3. **Rate Limiting** - Distributed (Redis) or in-memory rate limiting
4. **Request Size Limits** - Prevents DoS via large payloads
5. **Security Headers** - CSP, HSTS, X-Frame-Options, etc.
6. **Circuit Breakers** - Resilient LLM provider calls with fallback
7. **Observability** - Request ID correlation for all requests

### Frontend Security Layers
1. **Content Security Policy** - Strict CSP headers in production
2. **No Client Secrets** - API keys injected server-side via proxy
3. **HTTPS Enforcement** - HSTS with preload in production
4. **XSS Protection** - Input sanitization and output encoding

---

## Authentication & Authorization

### API Key Authentication

All API endpoints require authentication via the `X-API-Key` header:

```bash
curl -H "X-API-Key: $API_KEY" https://api.example.com/api/v1/search
```

**Implementation:** [api/auth.py](../api/auth.py)

**Key Features:**
- Supports multiple valid keys via `API_ACCESS_KEYS` (comma-separated)
- Keys are normalized (trimmed, deduplicated)
- `dev-secret-key` is **blocked in production**
- Failed authentication returns 401/403 with request ID

### API Key Rotation

Zero-downtime key rotation is supported:

1. Add new key alongside existing: `API_ACCESS_KEYS="NEW_KEY,OLD_KEY"`
2. Verify new key works: `GET /api/v1/verify-auth`
3. Update clients to use `NEW_KEY`
4. Remove old key: `API_ACCESS_KEYS="NEW_KEY"`

---

## Input Validation & Sanitization

### Sanitization Layer

All user inputs are sanitized using the [utils/sanitization.py](../utils/sanitization.py) module:

**Features:**
- Control character filtering (prevents log injection)
- HTML tag stripping (prevents XSS)
- Maximum length enforcement
- Path traversal protection

**Protected Endpoints:**
- `/api/v1/search` - Search queries sanitized (max 1,000 chars)
- `/api/v1/chat` - Chat messages sanitized (max 50,000 chars)

**Example:**
```python
from utils.sanitization import sanitize_search_query

try:
    clean_query = sanitize_search_query(user_input)
except ValueError as e:
    raise HTTPException(status_code=400, detail=str(e))
```

### ChromaDB Metadata Hardening (GHSA-36p7-vc44-83pf / CVE-2026-45833)

Dependabot keeps `GHSA-36p7-vc44-83pf` open because **no upstream patch exists** in any
released chromadb 0.5.x or 1.x line (the GHSA page reports "Patched versions: None").
The vector-store code path is mitigated in-tree rather than at the dependency
layer — every metadata value that reaches chromadb is funnelled through a
strict-whitelist pre-serialiser, so the chromadb metadata type-confusion attack
that the CVE describes cannot be reached from this app.

The two-layer pre-serialiser, defined in
[`apps/api/vector_store/chroma_store.py`](../apps/api/vector_store/chroma_store.py):

1. **`_sanitize_val` (line 304) — inner pre-serialiser, called from
   `property_to_document`** (which is the only path that builds a
   `Document` for chromadb ingestion). Allows **only**
   `None | str | int | bool | float | datetime-as-ISO-string`. Drops
   everything else. `float`s that are `NaN` or non-finite are dropped.
2. **`_sanitize_metadata` (line 472) — outer pre-serialiser, called from
   `add_properties` directly before `vector_store._collection.add(...)`**.
   Allows the same primitive set; **stringifies** any non-primitive via
   `str(value)` so no dict / list / object ever reaches chromadb's
   typed-metadata path.

The chromadb CVE-2026-45833 attack vector requires non-primitive metadata
values (typically dict-shaped) to reach the chromadb typed-input layer.
Both sanitizers reject those types upstream. The `add_texts` /
`add_documents` paths in this codebase therefore only ever see primitive
metadata, which chromadb's own validation handles safely.

Reachability assessment:
- `add_properties` (line 369) — the only ingestion path; sanitization
  mandatory before chromadb's `add` / `add_texts`.
- `similarity_search_with_score` (line 680), `get` (line 350), and the
  `delete` filters (lines 1214, 1232) all build their `filter` arguments
  via `_build_chroma_filter` (line 574) which constructs structured
  where-clauses server-side from typed Python values, not from
  user-controlled string interpolation.
- **No user-controlled string is ever passed through chromadb's
  metadata-typing layer.** The CVE is therefore non-reachable in this
  codebase as written.

**Action:** the Dependabot alert will stay open until upstream ships a
patch. Tracking the mitigation in-tree is by design; the tag gate
(`v5.1.5.4` / `v5.1.6`) per `Rule 2` requires 0 open critical alerts, so
the tag remains blocked at the dependency layer until either (a)
upstream releases a patched chromadb, or (b) this app is rewritten to
not use chromadb at all. Operator accepts the residual risk in the
meantime.

### Pydantic Validation

All request models use Pydantic for type validation and constraints:

```python
class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    limit: int = Field(10, ge=1, le=100)
```

---

## Rate Limiting & DDoS Protection

### Rate Limiting Configuration

**Implementation:** [api/observability.py](../api/observability.py)

**Environment Variables:**
```bash
# Enable rate limiting
API_RATE_LIMIT_ENABLED=true
API_RATE_LIMIT_RPM=600  # Requests per minute per client
```

**Rate Limiting Behavior:**
- Per-client limits based on API key hash
- Returns 429 with headers:
  - `X-RateLimit-Limit`: Maximum requests
  - `X-RateLimit-Remaining`: Remaining requests
  - `X-RateLimit-Reset`: Seconds until reset
  - `Retry-After`: Seconds to wait (on 429)

**Excluded Paths:**
- `/health` - Health checks
- `/docs`, `/redoc`, `/openapi.json` - API documentation

### Redis-Backed Rate Limiting

For distributed deployments, Redis-backed rate limiting is available:

```bash
REDIS_URL=redis://localhost:6379
```

**Fallback:** Automatically falls back to in-memory rate limiting if Redis is unavailable.

---

## API Security

### Request Size Limits

Prevents DoS via large payloads:

**Environment Variables:**
```bash
REQUEST_MAX_BODY_SIZE_MB=10      # Standard requests
REQUEST_MAX_UPLOAD_SIZE_MB=25     # File uploads
```

**Implementation:** [api/middleware/request_size.py](../api/middleware/request_size.py)

**Response:** Returns 413 (Payload Too Large) on exceed

### Security Headers

**Implementation:** [api/middleware/security.py](../api/middleware/security.py)

**Headers Applied:**
- `Content-Security-Policy` - Restricts resource loading
- `X-Content-Type-Options: nosniff` - Prevents MIME sniffing
- `X-Frame-Options: DENY` - Prevents clickjacking
- `X-XSS-Protection: 1; mode=block` - XSS mitigation
- `Referrer-Policy: strict-origin-when-cross-origin` - Controls referrer info
- `Permissions-Policy` - Restricts browser features
- `Strict-Transport-Security` - HTTPS enforcement (production only)

### Request ID Correlation

All requests include a unique `X-Request-ID` header for tracing:

```bash
curl -H "X-API-Key: $API_KEY" https://api.example.com/api/v1/search
# Returns: X-Request-ID: 550e8400-e29b-41d4-a716-446655440000
```

**Usage:** Include this ID in support requests for log correlation.

---

## Frontend Security

### Content Security Policy

**Implementation:** [frontend/next.config.ts](../frontend/next.config.ts)

**Production CSP:**
```javascript
{
  "default-src": ["'self'"],
  "script-src": ["'self'"],
  "style-src": ["'self'", "'unsafe-inline'"],
  "img-src": ["'self'", "data:", "https:", "blob:"],
  "connect-src": ["'self'", "<API_URL>"],
  "frame-src": ["'none'"],
  "object-src": ["'none'"]
}
```

**Development CSP:** More permissive for hot module replacement.

### No Client Secrets

API keys are **never** exposed to the frontend:

1. Frontend calls Next.js server-side proxy
2. Proxy injects `X-API-Key` from server environment
3. Actual backend API is never called directly from browser

### Error Handling

All API errors include the request ID for support:

```typescript
try {
  await searchProperties(request);
} catch (error) {
  // Error message includes request_id for support
  console.error(error);
}
```

---

## Resilience & Availability

### Circuit Breaker Pattern

**Implementation:** [utils/circuit.py](../utils/circuit.py)

**Purpose:** Prevents cascading failures when LLM providers are down.

**Behavior:**
- **Closed** (normal): Requests pass through
- **Open** (failing): Requests fail fast with error
- **Half-Open** (testing): Test requests allowed

**Configuration:**
```python
CIRCUIT_FAILURE_THRESHOLD=5   # Failures before opening
CIRCUIT_RECOVERY_TIMEOUT=60   # Seconds before half-open
CIRCUIT_HALF_OPEN_MAX_CALLS=3 # Test calls in half-open
```

### Graceful Shutdown

**Implementation:** [api/main.py](../api/main.py)

**Process:**
1. Stop accepting new requests (uvicorn)
2. Wait for drain period (default: 30s)
3. Stop background services (scheduler, monitors)
4. Close connections (vector store, Redis)
5. Log completion

**Configuration:**
```bash
SHUTDOWN_DRAIN_SECONDS=30
SHUTDOWN_MAX_WAIT_SECONDS=60
```

### Health Checks

**Endpoint:** `GET /health?include_dependencies=true`

**Response:**
```json
{
  "status": "healthy",
  "version": "4.0.0",
  "timestamp": "2026-01-26T10:00:00Z",
  "uptime_seconds": 3600,
  "dependencies": {
    "vector_store": {
      "status": "healthy",
      "message": "Connected",
      "latency_ms": 5.2
    },
    "redis": {
      "status": "healthy",
      "message": "Connected",
      "latency_ms": 1.1
    },
    "llm_provider": {
      "status": "degraded",
      "message": "OpenAI: OK, Anthropic: Timeout",
      "latency_ms": 250
    }
  }
}
```

**HTTP Status Codes:**
- 200: Healthy or Degraded
- 503: Unhealthy (critical dependencies down)

---

## Secrets Management

### Required Secrets

**Production:**
```bash
# At least one LLM provider API key (required)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=...

# API authentication (required)
API_ACCESS_KEYS=generated-api-key-here

# CORS (required)
CORS_ALLOW_ORIGINS=https://yourdomain.com

# Environment (required)
ENVIRONMENT=production
```

**Development:**
```bash
ENVIRONMENT=local
CORS_ALLOW_ORIGINS=http://localhost:3000
API_ACCESS_KEYS=dev-key-for-local-testing
```

### Secret Generation

Generate a secure API key:
```bash
openssl rand -hex 32
```

### Best Practices
1. **Never commit `.env` files** - Use `.env.example` as template
2. **Rotate keys quarterly** - Use staged rotation process
3. **Use platform secrets** - AWS Secrets Manager, Azure Key Vault, etc.
4. **Audit access** - Track who has access to production secrets
5. **Revoke immediately** - On suspected exposure

---

## Dependency Security

### Python Dependencies

**Security Tools:**
- `bandit` - Static analysis for security issues
- `pip-audit` - Known vulnerability scanning
- `safety` - Dependency vulnerability checking

**Run Security Scans:**
```bash
python -m bandit -r api agents ai analytics -x tests
python -m pip_audit -r requirements.txt
```

### Frontend Dependencies

**Security Tools:**
```bash
cd frontend
npm audit fix
npm audit --audit-level=high
```

**Pinned Transitive Dependencies:**
- `cross-spawn@7.0.5` - Fixes CVE-2024-21502
- `glob@10.4.5` - Fixes path traversal
- `tar@6.2.1` - Fixes arbitrary file write

---

## Production Deployment Checklist

### Pre-Deployment

- [ ] All environment variables set (no defaults for secrets)
- [ ] API keys generated and stored securely
- [ ] CORS restricted to production domain
- [ ] `ENVIRONMENT=production` set
- [ ] HTTPS enabled with valid certificate
- [ ] HSTS preloaded (if using domain)
- [ ] Rate limiting enabled
- [ ] Redis configured (if using distributed rate limiting)
- [ ] Database/vector store backed up
- [ ] Log aggregation configured
- [ ] Monitoring/alerting configured
- [ ] CSP headers tested
- [ ] Security audit run (`bandit`, `pip-audit`)

### Post-Deployment

- [ ] Verify health check returns 200
- [ ] Test API authentication with `GET /api/v1/verify-auth`
- [ ] Verify rate limiting works (send 601 requests)
- [ ] Check security headers in browser dev tools
- [ ] Verify CSP is enforced (check console for violations)
- [ ] Test request ID correlation in logs
- [ ] Verify graceful shutdown (SIGTERM, wait for drain)
- [ ] Monitor error rates and latency

---

## Incident Response

### Security Incident Process

1. **Detection** - Automated alerts or user report
2. **Assessment** - Determine severity and scope
3. **Containment** - Isolate affected systems if needed
4. **Eradication** - Remove threat or vulnerability
5. **Recovery** - Restore services from clean state
6. **Lessons Learned** - Update procedures

### Severity Levels

- **P0 (Critical)** - Production data exposure, active exploitation
- **P1 (High)** - Unauthorized access, denial of service
- **P2 (Medium)** - Potential exposure, misconfiguration
- **P3 (Low)** - Best practice deviation, low risk

### Response Contacts

- Security Lead: [To be configured]
- Infrastructure: [To be configured]
- Compliance: [To be configured]

---

## Reporting Security Issues

### Responsible Disclosure

If you discover a security vulnerability, please **disclose it privately**:

1. **Do not** create public issues
2. **Do not** disclose details publicly
3. **Do** send details to: security@example.com
4. **Include**:
   - Description of vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (optional)

### Response Timeline

- **Acknowledgment**: Within 48 hours
- **Initial Assessment**: Within 7 days
- **Fix Deployment**: Based on severity
  - P0: Within 24 hours
  - P1: Within 72 hours
  - P2: Within 2 weeks
  - P3: Next release

### Recognition

Security researchers who follow responsible disclosure will be:
- Credited in security advisories (if desired)
- Eligible for bounty program (if available)
- Invited to private security discussions

---

## Changelog

### 2026-01-26 - V4 Security Enhancements
- Added security headers middleware (CSP, HSTS, X-Frame-Options)
- Added request size limits to prevent DoS
- Added Redis-backed distributed rate limiting
- Added input sanitization for search and chat endpoints
- Added circuit breaker pattern for LLM provider resilience
- Added enhanced health checks with dependency verification
- Added graceful shutdown with drain period
- Added request ID correlation for all requests
- Added CSP headers to frontend Next.js config
- Removed `dev-secret-key` fallback in production
- Updated SECURITY.md documentation

### 2025-01-18 - Initial V4 Security Review
- Implemented API key authentication
- Added rate limiting with per-client RPM
- Added request ID correlation
- Fixed CORS configuration for production
- Added `pip-audit` and `bandit` to CI

---

**Document Version:** 4.0
**Last Review:** 2026-01-26
**Next Review:** 2026-04-26 (Quarterly)
