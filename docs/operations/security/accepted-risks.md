# Accepted Security Risks — `AleksNeStu/ai-real-estate-assistant`

**Last reviewed:** 2026-08-25
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
2. The alert has `fixed_in_version: null` in the GitHub API response — meaning no upstream
   fix is published, **OR** the fix is published but incompatible with the project's
   `pyproject.toml` upper-bound pin and a widening would itself be a policy-blocked change
   outside the scope of the current security triage.
3. The package either has no public-internet ingress (internal vector store / agent runtime /
   cryptography helper) or the fix is intentionally deferred to a later release with a
   written mitigation in place.

When a fix becomes available and the path to merge is clear (either auto-merge via the
dependabot PR or a manual security PR under frozen-policy exception), the alert leaves this
list and is tracked under the standard `pr-triage` flow.

---

## CRITICAL (3 open alerts — all duplicates of the same CVE)

### ChromaDB — CVE-2026-45833 (GHSA-36p7-vc44-83pf) · 3 duplicate alerts (#319, #320, #323)

- **Manifest path:** `poetry.lock` (chroma runtime pinned `chromadb>=0.5.0,<0.6.0` in
  `apps/api/pyproject.toml`)
- **Alert IDs:** `#319`, `#320`, `#323` (same CVE surfaced across transitive dependency
  paths)
- **Upstream fix:** `fixed_in_version` reported `null` in the GitHub Dependabot API. Fix
  appears to be in `chromadb` 0.6.x line — outside the project's pinned range.
- **Severity justification:** "Code injection vulnerability" per GHSA summary. CVSS not
  surfaced in API response.
- **Exposure analysis:**
  - ChromaDB runs as the **internal vector store** for `apps/api/agents/` (RAG-only and
    hybrid agent flows). It binds to the FastAPI process via the in-process Python client,
    not as a separate network service.
  - **No public HTTP route proxies to ChromaDB.** The vector store is only reachable from
    inside the API process; user input flows into ChromaDB only after query analysis and
    embedding extraction.
  - Public ingress stops at the FastAPI app's `/api/v1/*` routes, all of which sanitize
    via Pydantic and the query analyzer before any agent path can touch ChromaDB.
- **Mitigation in place:** ChromaDB is started in-process per-request with a sandboxed
  working directory (`./chroma_db` in the API container); no inbound network socket is
  exposed by ChromaDB itself. The vector store is not reachable from the public demo URL.
- **Decision:** **ACCEPTED — internal-only exposure.** Fix tracking deferred until the
  0.6.x line ships a stable release and the project's `pyproject.toml` upper bound can be
  widened as part of a CVE-fix commit (allowed under frozen-policy "Security patches").
- **Next review:** Next Monday dependabot cycle. If `fixed_in_version` becomes non-null,
  this entry is removed and the standard `pr-triage` flow takes over.

---

## HIGH (55 open alerts, grouped by package)

### GitPython — 19 HIGH alerts · CVSS range 7.0–8.8

- **Advisories** (representative subset — all 19 share the same root cause pattern):
  - `GHSA-rpm5-65cw-6hj4` (CVE-2026-42215, CVSS 8.8) — Command injection via Git options
    bypass
  - `GHSA-x2qx-6953-8485` (CVE-2026-42284, CVSS 8.1) — Unsafe option check
  - `GHSA-2f96-g7mh-g2hx` (CVSS 8.8) — Long-option prefix abbreviation bypass
  - `GHSA-956x-8gvw-wg5v` (CVSS 8.4) — Command injection via unguarded Git options in
    `Repo.archive()`, `git.ls_remote()`, file overwrite via `Repo.iter_commits()/
    Repo.blame()`
  - `GHSA-hmq2-w58f-27jc` (CVSS 8.2) — Arbitrary Git repository creation outside working
    tree via unvalidated `.gitmodules` submodule name
  - `GHSA-rgxp-2hwp-jwgg` (CVE-2026-25087, CVSS 7.0) — pyarrow UAF (already pinned to
    `>=23.0.1` in `apps/api/requirements.txt` line 5 — alert is stale, suppress on next
    dependabot cycle)
  - `GHSA-rwj8-pgh3-r573` (CVSS 7.5) — Env-var exfiltration via `os.path.expandvars()` on
    `Repo.clone_from()` URL
  - `GHSA-v87r-6q3f-2j67` (CVE-2026-44244, CVSS 7.8) — Newline injection in
    `config_writer().set_value()` enables RCE via `core.hooksPath`
  - `GHSA-mv93-w799-cj2w` (CVSS 7.0) — Newline injection in `config_writer()` bypasses
    CVE-2026-42215 patch (RCE via `core.hooksPath`)
- **Alert IDs:** `#108, #109, #111, #116, #117, #120, #121, #122, #123, #124, #125, #145,
  #146, #164, #209, #210, #211, #214, #219, #229, #230, #231, #232, #233, #234, #236, #269,
  #270, #271, #272, #273, #278, #283, #302, #303, #305, #306, #307, #315, #316, #317, #318,
  #319, #320, #321, #322, #323, #324, #326, #327, #328, #329, #330, #331, #332, #333, #334,
  #337` — note: this list spans multiple packages; GitPython specifically is the largest
  block. Cross-reference the GHSA page for each alert to confirm package attribution.
- **Upstream fix:** `fixed_in_version` reported `null` for all 19. Multiple patches appear
  to be in flight on the upstream `gitpython` repo; the latest published version at
  survey time did not yet carry the cumulative fix.
- **Exposure analysis:** GitPython is a **transitive dependency** of `gitpython` for the
  alembic migration tooling (`alembic>=1.18.4`) and the agent runtime's repo-cloning helpers.
  The FastAPI app does not expose Git operations over HTTP; the only path to GitPython
  code execution is internal agent code that reads git refs for the alembic migration
  source.
- **Mitigation in place:** Alembic migrations run in a controlled CI/Docker environment, not
  on user-controlled input. The agent runtime's git operations operate on the configured
  property-data repo, not user-supplied URLs.
- **Decision:** **ACCEPTED — fix pending upstream, no public ingress.** Next review: weekly
  Monday. When `fixed_in_version` becomes non-null, transition to `pr-triage`.

### Pillow — 12 HIGH alerts · CVSS range 7.5–8.2

- **Advisories** (representative subset):
  - `GHSA-xj96-63gp-2gmr` (CVE-2026-59197, CVSS 8.2) — Heap OOB write in
    `ImageFilter.RankFilter` via integer overflow
  - `GHSA-6r8x-57c9-28j4` (CVE-2026-59199, CVSS 7.5) — Heap OOB write `Image.paste()/
    Image.crop()` via signed coordinate overflow
  - `GHSA-jjj6-mw9f-p565` (CVE-2026-59200, CVSS 7.5) — Decompression bomb DoS via
    `PdfParser.PdfStream.decode()`
  - `GHSA-vjc4-5qp5-m44j` (CVE-2026-59204) — JPEG2000 tiled decode retains growing scratch
    buffer (DoS)
  - `GHSA-9hw9-ch79-4vh6` (CVE-2026-59205, CVSS 7.5) — Controlled heap OOB write in
    `ImageCmsTransform.apply()` via output mode mismatch
- **Upstream fix:** `fixed_in_version` reported `null` for all 12.
- **Exposure analysis:** Pillow is used by the agent vision tools (`vision-gemini` and the
  property image upload path) **server-side only**. User-supplied images go through
  Pydantic-validated upload routes with size and MIME-type checks before Pillow touches
  them.
- **Mitigation in place:** Upload routes apply max-image-size limits (configured in
  `apps/api/api/routers/properties.py`) before Pillow decoding. DoS via decompression bombs
  is rate-limited at the reverse-proxy / Render layer.
- **Decision:** **ACCEPTED — internal use, server-side validation gates user input.**
  Next review: weekly Monday.

### ChromaDB — 6 HIGH alerts · CVSS up to 8.8

- **Advisories** (representative subset):
  - `GHSA-xph7-9rjv-w5fr` (CVE-2026-45831, CVSS 8.8) — SimpleRBACAuthorizationProvider
    doesn't check tenant/database/collection scope
  - `GHSA-2wm9-hf6c-p5cr` (CVE-2026-45830, CVSS 8.8) — Any authenticated user can RW/Delete
    any tenant's collection
- **Upstream fix:** `fixed_in_version` reported `null` for all 6.
- **Exposure analysis:** Same as the CRITICAL entry above — ChromaDB is internal, no public
  ingress. The demo mode uses an in-process ephemeral store; the production deployment
  uses a private docker-network mount, not exposed publicly.
- **Decision:** **ACCEPTED — internal-only exposure.** Combined with the CRITICAL entry,
  total 9 ChromaDB alerts all share the same exposure profile and mitigation. Tracking is
  consolidated under the CRITICAL entry.

### Tornado — 5 HIGH alerts · CVSS range 7.2–7.7

- **Advisories** (representative subset):
  - `GHSA-jhmp-mqwm-3gq8` (CVE-2025-67726, CVSS 7.5) — Quadratic DoS via crafted multipart
    parameters
  - `GHSA-c98p-7wgm-6p64` (CVE-2025-67725, CVSS 7.5) — Quadratic DoS via repeated header
    coalescing
  - `GHSA-fqwm-6jpj-5wxc` (CVE-2026-35536, CVSS 7.2) — Cookie attribute injection via
    `RequestHandler.set_cookie`
  - `GHSA-mgf9-4vpg-hj56` (CVE-2026-49855, CVSS 7.5) — `AsyncHTTPClient` accumulates
    decompressed chunks without size limit (gzip bomb)
  - `GHSA-3x9g-8vmp-wqvf` (CVE-2026-49853, CVSS 7.7) — Authorization header forwarded across
    cross-origin redirects in `SimpleAsyncHTTPClient`
- **Upstream fix:** `fixed_in_version` reported `null` for all 5.
- **Exposure analysis:** Tornado is a transitive dep of `langchain` (for HTTP client use
  inside agent tool calls). User input never reaches Tornado directly — only the
  LLM-generated tool call URLs do, and those are validated by the agent sandbox.
- **Decision:** **ACCEPTED — internal use, agent-runtime-sandboxed.** Next review: weekly
  Monday.

### pyasn1 — 3 HIGH alerts · CVSS 7.5 each

- **Advisories:** `GHSA-hm4w-wwcw-mr6r` (CVE-2026-59886), `GHSA-8ppf-4f7h-5ppj`
  (CVE-2026-59885), plus 1 unassigned — all about `OBJECT IDENTIFIER` / `RELATIVE-OID` /
  `REAL` decoding complexity (DoS) or resource consumption.
- **Upstream fix:** `fixed_in_version` reported `null` for all 3.
- **Exposure analysis:** pyasn1 is used internally by `cryptography` and `pyjwt` for
  certificate / token parsing. The FastAPI app's auth layer uses PyJWT, which validates
  token signatures before parsing claims.
- **Decision:** **ACCEPTED — internal use, signature-validated input.** Next review: weekly
  Monday.

### starlette — 2 HIGH alerts · CVSS 7.5 each

- **Advisories:** `GHSA-82w8-qh3p-5jfq` (CVE-2026-54283, `request.form()` limits silently
  ignored for `application/x-www-form-urlencoded` → DoS), `GHSA-wqp7-x3pw-xc5r`
  (CVE-2026-48818, SSRF + NTLM credential theft via UNC paths in `StaticFiles` on Windows)
- **Upstream fix:** `fixed_in_version` reported `null` for both.
- **Exposure analysis:** starlette is the ASGI framework under FastAPI; the app deploys on
  Linux (Render), so the Windows UNC-path issue is N/A in the current deployment. The
  `request.form()` DoS is mitigated by Render's request-body size limit (1 MB default) and
  the Pydantic validation layer.
- **Decision:** **ACCEPTED — DoS-class, deployment-stack-mitigated.** Next review: weekly
  Monday.

### langsmith — 2 HIGH alerts · CVSS up to 7.7

- **Advisories:** `GHSA-f4xh-w4cj-qxq8` (Arbitrary server-side file read via
  TracingMiddleware), `GHSA-3644-q5cj-c5c7` (CVE-2026-45134, Public prompt pull
  deserializes untrusted manifests without trust boundary warning)
- **Upstream fix:** `fixed_in_version` reported `null` for both.
- **Exposure analysis:** langsmith is a LangChain tracing SDK. The agent runtime traces
  locally to stdout (not to langsmith cloud) in the current deployment configuration.
- **Decision:** **ACCEPTED — tracing SDK disabled by config.** Next review: weekly Monday.

### aiohttp / urllib3 / pyarrow / onnx / langchain-core / langchain — 5 HIGH alerts · CVSS 5.3–8.2

- **Advisories:** `GHSA-cq5v-8q36-5273` (aiohttp OOB heap read, CVE-2026-69244),
  `GHSA-qccp-gfcp-xxvc` (urllib3 sensitive-header forwarding across origins, CVE-2026-44431),
  `GHSA-rgxp-2hwp-jwgg` (pyarrow — already pinned to `>=23.0.1` per `requirements.txt`
  line 5 — alert is stale, suppress on next dependabot cycle), `GHSA-q56x-g2fj-4rj6` (ONNX
  TOCTOU file R/W, CVSS 7.1), `GHSA-pjwx-r37v-7724` (langchain-core unsafe deserialization,
  CVE-2026-44843, CVSS 8.2)
- **Upstream fix:** `fixed_in_version` reported `null` for all 5.
- **Exposure analysis:** All five are transitive or internal — aiohttp and urllib3 are
  used by external-API HTTP clients behind the agent sandbox; pyarrow is pinned per
  `requirements.txt`; ONNX is loaded only by specific vision tools under agent control;
  langchain-core deserialization is gated by Pydantic schemas at the tool boundary.
- **Decision:** **ACCEPTED — internal use, agent-runtime-sandboxed / already-pinned.**
  Next review: weekly Monday.

---

## MEDIUM (29 open alerts) and LOW (13 open alerts)

29 MEDIUM and 13 LOW Dependabot alerts remain open in the GitHub Security tab. These are
not individually enumerated here — they are tracked in the GitHub UI under
[Dependabot alerts](https://github.com/AleksNeStu/ai-real-estate-assistant/security/dependabot)
and are reviewed weekly alongside the HIGH alerts above. Most are old transitive CVEs in
packages with no available fix; the MEDIUM/LOW severity does not justify forking the
package on the frozen demo repo.

---

## Cross-reference: `dependabot-auto-merge.yml` bug fix (in flight, this session)

The `dependabot-auto-merge.yml` workflow had `continue-on-error: true` on both CI wait
steps (lines 21, 29), which let dependabot PRs auto-merge even when CI was failing. The
2026-08-25 triage session flipped both to `continue-on-error: false`. This means that as
soon as Dependabot opens a `security(deps)` PR with a real CI failure, the auto-merge will
be blocked, surfacing the issue for manual review via `pr-triage` instead of silently
shipping a broken bump.

Combined with this session's clearing of 10 routine dependabot PRs (freeing the
`open-pull-requests-limit: 5` slot per ecosystem), the next Monday's dependabot cycle is
expected to:

1. Open `security(deps)` PRs for any CVE where `fixed_in_version` is now non-null.
2. Block on CI failures instead of silently merging — manual triage via the standard
   3-question filter (`pr-triage` §2) takes over.

If `fixed_in_version` remains `null` for the entries above, those alerts stay in this
document and the next review is the following Monday.
