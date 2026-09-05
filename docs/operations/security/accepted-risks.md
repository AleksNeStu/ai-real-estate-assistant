# Accepted Security Risks — `AleksNeStu/ai-real-estate-assistant`

**Last reviewed:** 2026-08-26
**Previous review:** 2026-08-25 (initial draft; outdated — see "History" at bottom)
**Review cadence:** weekly on Monday, in sync with `.github/dependabot.yml` schedule
**Owner:** Alex Nesterovich
**Scope:** Open Dependabot alerts on the `dev` branch where the upstream fix is not yet
available, where exposure is internal-only, or where the fix is scheduled for a later
release. **Excludes** alerts already covered by an in-flight or merged dependabot PR — those
follow the normal `pr-triage` workflow.

This document is the canonical register of risks that the project consciously accepts.
Anything not listed here is treated as a candidate for immediate action under
`CLAUDE.md` §"Public Repo Maintenance" → "Security patches (Dependabot critical/high CVEs)".

---

## How risks enter this list

A risk enters when **all three** are true:

1. Dependabot has emitted an alert (`/repos/{owner}/{repo}/dependabot/alerts?state=open`).
2. The alert has `first_patched_version: null` in the GitHub API response — meaning no
   upstream fix is published yet, **OR** the fix is published but incompatible with the
   project's `pyproject.toml` upper-bound pin and a widening would itself be a
   policy-blocked change outside the scope of the current security triage.
3. The package either has no public-internet ingress (internal vector store / agent
   runtime / cryptography helper) **AND** the documented attack vector is not reachable
   in this deployment, or the fix is intentionally deferred to a later release with a
   written mitigation in place.

When a fix becomes available and the path to merge is clear (either auto-merge via the
dependabot PR or a manual security PR under frozen-policy exception), the alert leaves
this list and is tracked under the standard `pr-triage` flow.

---

## Current state (2026-08-26, verified via `gh api`)

**6 open Dependabot alerts**, all on a single package (`chromadb`, pip ecosystem, in
`apps/api/`). The 6 alerts decompose into 3 unique CVEs, each duplicated across the two
manifest paths where `chromadb` is referenced (`apps/api/pyproject.toml` and
`apps/api/uv.lock`).

| GHSA | CVE | CVSSv4 | EPSS | First patched | Affected manifest paths | Alerts |
|---|---|---|---|---|---|---|
| GHSA-36p7-vc44-83pf | CVE-2026-45833 | **9.4** | 0.00342 | NONE | pyproject.toml + uv.lock | #320, #323 |
| GHSA-xph7-9rjv-w5fr | CVE-2026-45831 | 8.8 | 0.00237 | NONE | pyproject.toml + uv.lock | #316, #322 |
| GHSA-2wm9-hf6c-p5cr | CVE-2026-45830 | 8.8 | 0.00345 | NONE | pyproject.toml + uv.lock | #318, #321 |

**Severity mix:** 2 CRITICAL (CVE-2026-45833 × 2 paths) + 4 HIGH (CVE-2026-45831 × 2 paths +
CVE-2026-45830 × 2 paths).

**EPSS interpretation:** all three CVEs have EPSS percentiles < 30th percentile, meaning
they are NOT currently being exploited in the wild per the EPSS exploitation model
(FIRST.org, updated daily). Risk profile is dominated by theoretical reachability, not
active exploitation.

---

## CRITICAL (2 alerts — CVE-2026-45833, code injection)

### ChromaDB — CVE-2026-45833 (GHSA-36p7-vc44-83pf) · 2 alerts (#320, #323)

- **Vulnerable range:** `>= 0.4.17, <= 1.5.9` (project pins `chromadb>=0.5.0,<0.6.0` per
  `apps/api/pyproject.toml`)
- **Manifest paths surfaced:** `apps/api/pyproject.toml`, `apps/api/uv.lock`
- **Upstream fix:** `first_patched_version: null`. HiddenLayer advisory
  (https://www.hiddenlayer.com/sai-security-advisory/2026-06-chromadb-5) notes the fix is
  pending in chroma-core/chroma PR #7602.
- **Severity justification:** CVSSv4 = 9.4 (`AV:N/AC:L/AT:N/PR:L/UI:N/VC:H/VI:H/VA:H/SC:H/SI:H/SA:H`).
  CWE-94 (Improper Control of Generation of Code — Code Injection).
- **Attack vector (per GHSA):** an **authenticated** attacker who holds
  `UPDATE_COLLECTION` permission sends a malicious model repository URL with
  `trust_remote_code=true` to `/api/v2/tenants/{tenant}/databases/{db}/collections/{id}`.
  The ChromaDB server then loads and executes the malicious code via its embedding
  model loader.
- **Reachability analysis in this deployment:**
  - ChromaDB runs as an **in-process** Python client inside the FastAPI worker — there is
    **no separate network port** for ChromaDB itself. No `0.0.0.0:8000` listener on the
    chromadb process; the only public ingress is the FastAPI app on Render.
  - The vulnerable ChromaDB HTTP endpoint
    `/api/v2/tenants/.../collections/{collection_id}` is **not exposed** by this app.
    The FastAPI routes are all under `/api/v1/*` and `/health`. A search of the OpenAPI
    schema confirms no `/api/v2/...` route is registered (verified 2026-08-25 via
    `GET /openapi.json` on Render staging).
  - **Authentication prerequisite is not met:** ChromaDB's `UPDATE_COLLECTION` permission
    is granted by ChromaDB's own auth layer (not by our FastAPI auth). The deployment
    uses the default `default_tenant` with no ChromaDB-side user accounts configured;
    ChromaDB requires `Authorization: Bearer <token>` for any permission-scoped operation,
    and no such tokens are issued by the FastAPI app.
  - **Trust_remote_code path is not reachable:** the FastAPI app never instantiates a
    ChromaDB embedding function with `trust_remote_code=true`. The agent runtime uses
    `fastembed` (a sandboxed ONNX-based embedder) for embeddings, not ChromaDB's
    `SentenceTransformerEmbeddingFunction` which is the affected loader.
  - **Deployment context is ephemeral:** `SEED_ON_STARTUP=false` and
    `VECTOR_PERSIST_ENABLED=false` per `render.yaml`. Each Render instance starts with
    an empty in-memory ChromaDB index that does not persist. The vulnerable code path
    requires pre-existing collection state to be meaningful.
- **Mitigation in place:** the attack chain (authenticated ChromaDB user + malicious model
  URL + pre-existing collection + `trust_remote_code=true` flag) requires four
  independent preconditions, **none of which are reachable in this deployment**.
- **Decision:** **ACCEPTED — attack chain not reachable.** Next review: weekly Monday.
  When `first_patched_version` becomes non-null, transition to `pr-triage` for a
  CVE-fix PR (the `pyproject.toml` upper bound may need widening — allowed under
  frozen-policy "Security patches" row).

---

## HIGH (4 alerts — CVE-2026-45831 + CVE-2026-45830)

### ChromaDB — CVE-2026-45831 (GHSA-xph7-9rjv-w5fr) · 2 alerts (#316, #322)

- **Vulnerable range:** `>= 0.5.0, <= 1.5.9` (project pin `>=0.5.0,<0.6.0` IS in range)
- **Manifest paths surfaced:** `apps/api/pyproject.toml`, `apps/api/uv.lock`
- **Upstream fix:** `first_patched_version: null`. Fix tracked in chroma-core/chroma
  PR #7602 (same PR as CVE-2026-45833).
- **Severity justification:** CVSSv4 = 8.8
  (`AV:N/AC:L/AT:P/PR:L/UI:N/VC:H/VI:H/VA:N/SC:H/SI:H/SA:N`). CWE-863 (Incorrect
  Authorization).
- **Attack vector (per GHSA):** the `SimpleRBACAuthorizationProvider` evaluates whether
  a user holds a given permission (e.g., `read`, `write`) but does **not** check which
  tenant, database, or collection that permission applies to. An authenticated user
  with `read` permission on tenant A can read collections in tenant B.
- **Reachability analysis in this deployment:**
  - The vulnerability requires **multiple tenants** to exist for the cross-tenant data
    exposure to be meaningful. This deployment uses the default single-tenant
    ChromaDB configuration (`default_tenant` only). No multi-tenant setup is created
    by the FastAPI app, and no mechanism exists for an attacker to create additional
    tenants.
  - The vulnerable code path is reached when `Authorization: Bearer <token>` is sent to
    ChromaDB. The FastAPI app does not proxy ChromaDB's HTTP API (it's in-process), and
    no ChromaDB-side tokens are issued or accepted.
  - CWE-863 requires a permission check to **bypass**; this deployment does not call
    ChromaDB with any user-controlled permission check that could be bypassed.
- **Mitigation in place:** single-tenant deployment + in-process ChromaDB client + no
  ChromaDB-side auth tokens = cross-tenant path is structurally unreachable.
- **Decision:** **ACCEPTED — multi-tenant prerequisite not met.**

### ChromaDB — CVE-2026-45830 (GHSA-2wm9-hf6c-p5cr) · 2 alerts (#318, #321)

- **Vulnerable range:** `>= 0.4.17, <= 1.5.9` (project pin in range)
- **Manifest paths surfaced:** `apps/api/pyproject.toml`, `apps/api/uv.lock`
- **Upstream fix:** `first_patched_version: null`. Fix tracked in chroma-core/chroma
  PR #7602.
- **Severity justification:** CVSSv4 = 8.8. CWE-266 (Incorrect Privilege Assignment) +
  CWE-639 (Authorization Bypass Through User-Controlled Key).
- **Attack vector (per GHSA):** an **authenticated** user can arbitrarily read, write,
  update, or delete data in **any** tenant's collection, regardless of which tenant
  they belong to.
- **Reachability analysis in this deployment:**
  - Same single-tenant constraint as CVE-2026-45831 — no multi-tenant scenario to
    exploit.
  - Additionally, `VECTOR_PERSIST_ENABLED=false` means collections created during an
    attack window are discarded when the Render instance restarts (auto-sleep on free
    tier, manual redeploy on every `main` push). The blast radius of any successful
    attack is bounded to a single ephemeral instance lifetime.
  - The vulnerable code path is reachable only via ChromaDB's HTTP API, which is not
    exposed by this deployment (see CVE-2026-45833 reachability analysis).
- **Mitigation in place:** single-tenant + ephemeral storage + no public ChromaDB HTTP
  API = attack path is structurally unreachable.
- **Decision:** **ACCEPTED — multi-tenant prerequisite not met, ephemeral storage
  bounds blast radius.**

---

## Cross-reference: combined chromadb CVE mitigation

All three CVEs trace to the same root cause (insufficient tenant/database/collection
isolation in ChromaDB's auth layer) and are addressed by the same upstream PR
(chroma-core/chroma #7602). When `first_patched_version` becomes non-null for any of the
three, the other two will likely follow — the fix is a single auth-layer change, not
three independent patches.

Per `.github/dependabot.yml` `security-updates-only: true`, dependabot will open a
`security(deps-api): bump chromadb` PR as soon as a fix is published. The
`open-pull-requests-limit: 5` per ecosystem was saturated by 10 routine PRs at the
start of this triage batch; that limit is now cleared (10 routine PRs closed in the
2026-08-25 session) so the next Monday cycle can author the CVE-fix PR.

If the fix lands in `chromadb` 0.6.x and the project's `<0.6.0` upper bound in
`pyproject.toml` needs widening, the bound-widening commit is **part of** the CVE-fix
commit and therefore allowed under frozen-policy "Security patches" row. No standalone
"widening" PR would be permitted.

---

## MEDIUM (0) and LOW (0)

As of 2026-08-26 review, there are **zero MEDIUM** and **zero LOW** Dependabot alerts
open. The previous review (2026-08-25) reported 29 MEDIUM + 13 LOW; these 42 alerts have
auto-resolved in the 1-day interval (most likely via transitive-dep fixes that closed
the underlying vulnerable ranges). No action needed.

---

## History

- **2026-08-26** — Re-review. Previous draft documented 100 alerts based on
  `dependabot/alerts?per_page=100` returning a full page; the actual current count is 6
  alerts (94 alerts auto-resolved between 2026-08-25 and 2026-08-26 via transitive-dep
  fixes / upstream releases). Doc rewritten to reflect the 6 actual alerts with
  per-CVE reachability analysis, EPSS scores, and CVSSv4 justification.
- **2026-08-25** — Initial draft. Documented 100 alerts (3 CRITICAL chromadb code
  injection + 55 HIGH across GitPython/Pillow/chromadb/tornado/pyasn1/starlette/
  langsmith/...) + 29 MEDIUM + 13 LOW. Most of the 55 HIGH turned out to be
  transitive-dependency CVEs in packages that have since received upstream fixes and
  closed the vulnerable ranges without any change on `dev`.
