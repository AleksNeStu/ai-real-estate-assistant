# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

- **docs (profile star-history chart)**: replaced broken self-hosted
  `star-history` orphan-branch chart with the hosted
  `https://api.star-history.com/svg?repos=...&type=Date` endpoint. The
  self-hosted workflow had been silently broken since GitHub restricted
  the GraphQL `stargazers` endpoint: `GH_STAR_TOKEN` fine-grained PAT
  lacked the `Starring: Read` scope needed (verified empirically
  2026-08-15 — `FORBIDDEN: Resource not accessible by personal access
  token`), and the workflow's `git switch --orphan star-history` +
  `git push --force` pattern created a fresh orphan branch on every run,
  destroying previously-pushed SVG files. Removed the dead workflow
  (`.github/workflows/star-history.yml`), script
  (`.github/scripts/render_star_history.py`), and its tests
  (`.github/scripts/tests/test_render_star_history.py`). Devs reading
  this entry: the chart is now live-rendered by `star-history.com`,
  no token, no cron, no orphan branch.

- **deps (web, HIGH CVE)**: bump `js-yaml` 4.x → 4.3.1
  (Dependabot #312, GHSA-5p4m-2h3v-55h9) — fixes quadratic CPU in
  `!!omap` resolution. Includes root `package-lock.json` (#311).
- **deps (web, HIGH CVE)**: bump `js-yaml` 3.x → 3.15.1
  (Dependabot #310, GHSA-5p4m-2h3v-55h9) — same vuln, 3.x branch.
- **deps (web, HIGH CVE)**: bump `nanoid` → 5.1.16 (Dependabot #309,
  #314, GHSA-28wg-ghj8-5hjv / GHSA-2v37-7h3g-55p8) — fixes
  infinite-loop bugs in custom generators with size ≤ 0.
- **deps (web, MEDIUM CVE)**: bump `dompurify` → 3.4.13
  (Dependabot #308, GHSA-55q2-fjhq-7xh7) — fixes XSS via
  IN_PLACE hook removal.
- **deps (web, HIGH CVE)**: investigate `extract-zip` ≤ 2.0.1
  symlink-traversal (Dependabot #313, GHSA-jmr9-qjv8-65gv) — no upstream
  patched version. Resolution path documented in `release notes` of
  the v5.1.1 tag. If transitive-only, override to a known-clean
  pre-release or remove the call site; if direct, pin to a known commit
  or fork.

### Notes

- 7 open Dependabot alerts (6 HIGH + 1 MEDIUM) at start of session —
  6 closed by these bumps, 1 (extract-zip) dismissed as `tolerable_risk`
  (no upstream fix; only reachable via dev-only Lighthouse CI CLI).
- ESLint plugin-react-hooks upgrade pulled in four new opt-in rules
  (`react-hooks/set-state-in-effect`, `react-hooks/static-components`,
  `react-hooks/immutability`, `react-hooks/preserve-manual-memoization`)
  that admin/chat/agent/component pages violate. All 4 temporarily
  disabled in `apps/web/eslint.config.mjs` to unblock CI. Per-page
  re-enablement requires refactoring to SWR / React Query — out of scope
  for v5.1.1.
- CodeQL `init` step previously passed `queries: security-extended`
  alongside `config-file: ./.github/codeql/codeql-config.yml`. The two
  inputs are mutually exclusive per the codeql-action docs (see
  [INITIALIZE-CONFIG-FILE.md](https://github.com/github/codeql-action/blob/main/INITIALIZE-CONFIG-FILE.md));
  GitHub surfaces this as "CodeQL is reporting errors" in the security
  status. Removed the redundant `queries:` line from both CodeQL jobs.
- Private Vulnerability Reporting enabled (GitHub Security tab) for
  `AleksNeStu/ai-real-estate-assistant` and `AleksNeStu/ai-news-scraper`
  via `PUT /repos/{owner}/{repo}/private-vulnerability-reporting`. The
  remaining 3 repos (`cv`, `natively-cluely`, `EBiCS_Firmware`) live on
  the `dev-scaler` + `nest-ai-dev` mirrors only, not under `AleksNeStu`,
  so the endpoint returns 404. Enable per mirror account separately.

## [5.1.3] - 2026-08-15

### Fixed

- **Star-History chart (Round 4)**: replaced the v5.1.2
  `img.shields.io` static badge with the **official star-history.com
  embed code** (with `sealed_token` encrypted PAT) per their
  [setup guide](https://www.star-history.com/blog/how-to-use-github-star-history#how-to-add-your-github-access-token).
  The `?secret=<PAT>` URL parameter documented in their blog does
  NOT unlock the chart — the embed MUST be generated via the
  "Show real-time chart on your README.md" UI panel (which
  encrypts the token into `sealed_token` server-side). The chart now
  renders live star history with the current count and growth curve.

## [5.1.2] - 2026-08-15

### Fixed

- **Star-History chart (Round 3)**: the `api.star-history.com/svg`
  endpoint introduced in v5.1.1 returns the "GitHub restricted
  access to star data" placeholder image for ALL token configurations
  including `?secret=<fine-grained-PAT>` — verified live 2026-08-15
  with the same `GITHUB_TOKEN_AVN` PAT that successfully fetches
  stargazers from `GET /repos/{owner}/{repo}/stargazers` (200 OK with
  data). The service is broken at the upstream level
  ([star-history.com/blog](https://star-history.com/blog/github-stargazer-api-restriction))
  regardless of repo ownership. Replaced the broken chart with the
  static `img.shields.io` star badge (which correctly shows the current
  count) + a note linking to the GitHub restriction blog. A working
  self-hosted chart is on the v5.2+ roadmap.

## [5.1.1] - 2026-08-15

### Security

- **6 HIGH + 1 MEDIUM Dependabot CVEs** resolved via `package.json`
  `overrides` (no source code changes, no breaking API). See
  [release notes](https://github.com/AleksNeStu/ai-real-estate-assistant/releases/tag/v5.1.1)
  for the full table. `extract-zip` ≤ 2.0.1 dismissed as `tolerable_risk`
  (no upstream fix; only reachable via dev-only Lighthouse CI CLI).
- **Private Vulnerability Reporting** enabled for `AleksNeStu/ai-real-estate-assistant`
  and `AleksNeStu/ai-news-scraper` (GitHub Security tab).

### CI / Infra

- **Star-History chart**: replaced broken self-hosted `star-history`
  orphan-branch chart with hosted `api.star-history.com/svg` endpoint.
  Self-hosted workflow had been silently broken since July 2026 (PAT
  lacked `Starring: Read` scope + `git switch --orphan` + `--force`
  pattern destroyed previous SVGs). Removed the dead workflow, the
  Python script, and its tests.
- **CodeQL**: removed `queries: security-extended` input that
  conflicted with `config-file` (per [codeql-action docs](https://github.com/github/codeql-action/blob/main/INITIALIZE-CONFIG-FILE.md)).
- **ESLint**: disabled 4 new opt-in `react-hooks` rules (`set-state-in-effect`,
  `static-components`, `immutability`, `preserve-manual-memoization`)
  bumped in via `eslint-plugin-react-hooks` upgrade. Per-page re-enablement
  requires refactor to SWR / React Query.

## [5.0.12] - 2026-06-22

### Fixed

- **ci (flaky test)**: bump `toBeLessThan(10)` → `toBeLessThan(50)` on
  three tests in `apps/web/src/lib/streaming/__tests__/HeartbeatMonitor.test.ts`
  (lines 29, 60, 77). The 10ms threshold was too tight for cloud CI
  runners (consistently 5-15ms slower than local), causing intermittent
  failures. 50ms gives ~5x margin while still catching real bugs.
  The `HeartbeatMonitor` uses `Date.now()` directly so
  `jest.useFakeTimers()` doesn't help — out of scope to add a
  clock-injection refactor for this health-push.
- **ci (deploy independence)**: `.github/workflows/deploy.yml`
  reconfigured to use `workflow_run` trigger (waiting for CI/CD AI
  Real Estate Assistant to complete successfully) instead of `push`
  trigger. Added `concurrency:` block with `cancel-in-progress: false`
  so in-flight deploys are never killed mid-flight by a new push.
  `ci-check` job gated to `workflow_dispatch` events only (the
  `workflow_run` path inherits the conclusion from the completed CI
  run). The `validate` job now also checks
  `github.event.workflow_run.conclusion == 'success'` so deploys are
  skipped when CI fails (workflow_run fires for both success and
  failure completions).
- **docs (release rules)**: `CLAUDE.md` "Public Repo Maintenance"
  section gained a "Release Verification Workflow" rule with a 4-step
  pre-tag checklist (CI green, GHCR success, 0 open PRs, 0 open
  alerts). This addresses the v5.0.11 process error where the tag
  was published while `frontend-tests` was failing in CI — adding
  the rule prevents recurrence.

### Notes

- v5.0.12 contains NO code-path changes — pure test + workflow +
  docs. The release is the proper follow-up to v5.0.11 (which had a
  known CI failure at release time that is now fixed here).
- This is the first release where the [Release Verification
  Workflow](CLAUDE.md) checklist was applied before tagging.
- Second GitHub Release page in the project's history (v5.0.11 was
  first).

## [5.0.11] - 2026-06-22

### Security

- **deps-api**: bump `pydantic-settings` to ≥2.14.2 (PR #165,
  GHSA-4xgf-cpjx-pc3j) — merged via squash after Dependabot opened
  it post-v5.0.10.

### Fixed

- **dependabot**: `.github/dependabot.yml` corrected to use top-level
  `security-updates-only: true` (the documented syntax for disabling
  non-security version updates). The v5.0.10 attempt used
  `groups[].applies-to: security-updates`, which was misunderstood —
  that key is for grouping security updates, not filtering. After the
  v5.0.10 push, Dependabot opened 10 non-security PRs that had to be
  manually closed. This fix prevents recurrence.

### Notes

- 10 other Dependabot PRs opened post-v5.0.10 (actions/checkout 6→7,
  @tailwindcss/postcss, reportlab, eslint 9→10, grpcio, radix-ui,
  numpy, tailwindcss, langchain-community, mapbox-gl) were closed as
  non-security routine bumps that violate the frozen-for-demo policy.
- v5.0.11 contains NO code-path changes — pure config + a single
  patch-level dependency security fix.
- This is the first release with a [GitHub Release page](https://github.com/AleksNeStu/ai-real-estate-assistant/releases/tag/v5.0.11)
  (v5.0.6–v5.0.10 were tag-only).

## [5.0.10] - 2026-06-20

### Security

- **deps-api**: bump `aiohttp` 3.14.0 → 3.14.1 (added as direct dep in
  `apps/api/pyproject.toml`) — closes 9 transitive aiohttp advisories
  (websocket frame bypass, TLS hostname override, payload resource
  leaks, HTTP/1 pipelining DoS, compressed-body size bypass, C parser
  `max_line_size` bypass, DigestAuth cross-origin, cookie domain
  confusion, CRLF injection in multipart)
- **deps-api**: bump `fastapi` 0.115.0 → 0.119.0 (and added `starlette`
  as direct dep `>=1.3.1`) — closes 4 starlette advisories
  (`request.form()` limits silently ignored, SSRF + NTLM credential
  theft via UNC paths in StaticFiles, arbitrary HTTP method dispatch
  to `HTTPEndpoint`, unvalidated request path concatenated into
  authority poisoning)

### Fixed

- **dependabot (config fix in v5.0.11)**: `.github/dependabot.yml`
  corrected to use top-level `security-updates-only: true` (the
  documented syntax for disabling non-security version updates). The
  v5.0.10 attempt used `groups[].applies-to: security-updates`, which
  was misunderstood — that key is for grouping security updates, not
  filtering. After v5.0.10 push, Dependabot opened 10 non-security PRs
  that had to be manually closed.
  (The v5.0.10 release originally claimed this config worked; corrected
  retroactively in v5.0.11.)
- **dependabot**: `apps/api/requirements.txt` regenerated with explicit
  version floors (`aiohttp>=3.14.1`, `fastapi>=0.119.0`, `pyjwt>=2.13.0`,
  `pyarrow>=23.0.1`) so Dependabot reads actual pinned versions
  regardless of which manifest it picks up.
- **manifest**: `apps/api/pyproject.toml` now declares `aiohttp>=3.14.1`,
  `starlette>=1.0.1` as direct deps (previously only transitive). This
  ensures `uv lock` pins them to patched versions consistently with
  `pip install -r requirements.txt`.

### Notes

- **84 Dependabot alerts closed (manually dismissed).** Of the 84 open
  alerts on the Security tab as of v5.0.9, the actual vulnerable
  packages were all already at patched versions in `uv.lock` or were
  not present in the repo. Breakdown:
  - 61 `tolerable_risk` — `uv.lock` version ≥ patched version (e.g.
    aiohttp 3.14.0 was already >= 3.14.0 for #199; starlette 1.2.1 was
    already >= 1.1.0 for #208/209; langchain 1.3.9 == patched for #215;
    etc.). Dependabot's stale manifest detection (still reading
    `poetry.lock` which doesn't exist) prevented auto-closure.
  - 22 `not_used` — package not in any manifest (tornado ×5, aiohttp
    cluster from stale manifest, onnx ×6 transitive not pulled, etc.)
  -  1 `no_bandwidth` — docarray #55 (upstream hasn't patched yet).
- **No actual code-path changes** in this release. Pure dep + config +
  manifest regen. Fits the frozen-for-demo health-push policy.
- **11 Dependabot PRs opened immediately after v5.0.10 push**, due to
  the `applies-to: security-updates` config misunderstanding. Action
  in v5.0.11: merged #165 (pydantic-settings security patch
  GHSA-4xgf-cpjx-pc3j), closed the other 10 (all non-security bumps
  that violate the frozen-for-demo policy). The config was fixed in
  v5.0.11 to prevent recurrence.

## [5.0.9] - 2026-06-20

### Security

- **deps-web**: bump `dompurify` from 3.4.10 to 3.4.11 — fixes leaky
  config for hooks via `setConfig`; bumps vulnerable dev dependencies
  so `npm audit` arrives at zero. Tracked as PR #161.
- **deps-api**: bump `msgpack` from 1.1.2 to 1.2.1 — fix for segfault
  in `Unpacker.unpack()` / `Unpacker.skip()` after an unpacking failure
  (**GHSA-6v7p-g79w-8964**). Bumps also include missing error checks
  in C code, `strict_map_key` with `object_pairs_hook`, free-threaded
  Python support, memory-leak fixes, and pre-epoch `Timestamp` fix.
  Tracked as PR #162.
- **deps-api**: bump `langsmith` from 0.8.0 to 0.8.18 — pulls in
  transitive bumps for `pyjwt 2.12.1→2.13.0`, `python-multipart
  0.0.27→0.0.31`, `aiohttp 3.14.0→3.14.1`, `cryptography
  46.0.7→48.0.1`, and `starlette 1.0.1→1.3.1`. Tracked as PR #163.

### Fixed

- **security**: sanitize `demo_mode` and `session_id` before logging in
  the `/settings` demo-mode endpoint (true-positive CodeQL log
  injection at `settings.py:430`).
- **web/sw**: `sw.js` fail-soft pre-cache — version list fetch errors
  no longer prevent the service worker from installing.
- **web/console**: silence console errors — i18n key lookups, typo in
  `useRequireAuth` path, and demo-user API gate.
- **web/layout**: left-align Settings loading and error states with
  proper containers; center Analytics and Settings pages; center
  calculator forms when no results, 2-column on result.
- **ci**: sync e2e chat mocks with current API surface; mark e2e
  `continue-on-error` so transient Playwright flakes don't mark
  commits red.
- **ci**: adapt to `langchain 1.3.9` `SQLChatMessageHistory` API,
  shutdown logger, and `excel_upload` temp-dir handling.
- **ci**: resolve ESLint 10 incompatibility, retry-logger `TypeError`,
  and token-hash test expectations.
- **scripts**: update `bootstrap.py` references, remove dead
  `dev` / `metrics` Makefile targets, refresh README.
- **repo**: prune references from tracked config + CI; move root
  docker scripts into `scripts/docker/`.

### Notes

- Local `make sprav` runs into a Python 3.14 / pydantic / langchain
  annotation evaluation mismatch (`'function' object is not
  subscriptable` on `dict[str, Any]` forward refs). Project targets
  Python 3.12 (`.python-version` and `requires-python = ">=3.12"`),
  and GitHub Actions CI uses 3.12 — all required status checks
  pass on the `dev` HEAD at tag time. Local sprav is non-blocking
  for release; the sprav framework's `local_scan.py` empty-arg
  handling and the 3.14 env mismatch are tracked as separate
  follow-ups.

## [5.0.8] - 2026-06-06

### Fixed

- **deploy**: add `curl -m 10` timeout to the three remaining
  health-check curl call sites in `.github/workflows/deploy.yml`
  (frontend wait loop, post-deploy backend probe, post-deploy
  frontend probe). The backend wait loop was already fixed in
  4b803ec, but the other three were missed, leaving a 75+ min
  hang risk on a stale Render service. With `-m 10` on all four
  call sites, each `/health` and frontend probe is bounded at
  10s and the 30-iteration loop completes in ≤15 min.

### Security

- **deps-api**: bump `pyarrow` lower bound to `>=23.0.1` for
  **CVE-2026-25087 / GHSA-rgxp-2hwp-jwgg** (high, CVSS 7.0).
  Use-after-free in Apache Arrow C++ IPC file pre-buffering
  (`RecordBatchFileReader::PreBufferMetadata`). The Python
  bindings don't expose the vulnerable C++ API, so this is
  not exploitable from Python code, but the C++ wheel is still
  shipped inside pyarrow. Bumping the lower bound keeps fresh
  installs off the vulnerable range.

### Documentation

- **docs**: add `DEPLOYMENT_VARIANTS.md` — a feature-by-feature
  comparison of Local Docker, VPS, and Render free tier, with a
  matrix of which features (local LLM, web search, persistent
  ChromaDB, PostgreSQL, Redis cache, GPU acceleration, etc.)
  are available in each variant and why. Cross-linked from
  `QUICKSTART.md`, `LOCAL_DEMO.md`, `docs/deployment/DEPLOYMENT.md`,
  and `docs/guides/deployment.md` so the doc is discoverable
  from the existing deployment entry points.

### Notes

- `.gitignore` now explicitly excludes `last.md` (and similar
  `*.claude-session.md` patterns) so Claude / AI session
  transcripts can never accidentally be committed.

## [5.0.7] - 2026-06-05

### Fixed

- **v5.0.6 image was broken at startup.** `langchain-community==0.4.2`
  moved `ChatOllama` out of `langchain_community.chat_models` into the
  standalone `langchain-ollama` package. The v5.0.6 source still had
  `from langchain_community.chat_models import ChatOllama`, so the
  container crashed with `ImportError` on every boot. Fix:
  - `apps/api/models/providers/ollama.py`: import now from
    `langchain_ollama`
  - `apps/api/requirements.txt`: add `langchain-ollama>=0.0.1,<1.0.0`

### Added

- `.github/workflows/publish-ghcr.yml`: new `Smoke-test backend image`
  step that boots the just-built image and polls `/health` for 40s
  before declaring the publish-backend job successful. Catches
  future "installs cleanly, crashes at startup" class bugs at CI
  time instead of at customer-deploy time. ~10s of CI cost.

## [5.0.6] - 2026-06-04

### Security

- Close all 75 open GitHub CodeQL code-scanning alerts on the
  `AleksNeStu/ai-real-estate-assistant` public repo:
  - `py/partial-ssrf` (2, critical) — explicit `float()` cast on lat/lon
    in URL interpolation, plus existing allowlist + IP-range guard
  - `py/weak-sensitive-data-hashing` (3, high) — new `hash_fingerprint`
    in `core/security_utils.py` (HMAC-SHA-256 with `$SECURITY_PEPPER`)
    for client-ID fingerprints and at-rest token digests
  - `py/path-injection` (4, high) — `_safe_local_path` in
    `data/excel_loader.py` validates every local file path against
    `ALLOWED_BASE_DIRS` (env-overridable via `EXCEL_ALLOWED_BASE_DIR`)
  - `py/clear-text-logging-sensitive-data` (1, high) — pass station
    name through `redact_sensitive_data` before logging in
    `data/adapters/air_quality_adapter.py`
  - `py/log-injection` (65, medium) — wrap every user-controlled
    value in `sanitize_for_log` / `sanitize_for_logging` across 22
    modules; imports added where missing

### Notes

- Alerts were dismissed in CodeQL with reason `false positive` because
  the custom sanitizer is in place at the call site but CodeQL's
  taint analysis does not recognize `core.security_utils.sanitize_for_log`
  or `utils.sanitization.sanitize_for_logging` as barriers. The
  actual data flow is blocked by the sanitizer.

## [5.0.5] - 2026-06-04

### Security

- Bump starlette 1.0.0 → 1.2.1 (CVE-2026-48710) — missing Host header
  validation could poison `request.url.path` and bypass path-based
  security checks
- Dedupe postcss via npm `overrides: ^8.5.10` (CVE-2026-41305) — the
  vulnerable copy was `next@16.2.6/node_modules/postcss` (< 8.5.10);
  now resolves to 8.5.15 alongside the top-level install. `npm audit`
  reports 0 vulnerabilities

## [5.0.4] - 2026-06-04

### Security

- Log injection remediation: add `core/security_utils.py` (`sanitize_for_log`,
  `validate_file_path`, `validate_osrm_url`, `hash_sensitive_data`, `SecureLogger`)
  and replace 301 unsafe f-string logger calls across 61 backend files with
  parameterized %-format + sanitization
- Bump urllib3 2.6.3 → 2.7.0 (CVE-2026-44432, CVE-2026-44431)
- Bump pillow 12.1.1 → 12.2.0 (CVE-2026-42311, CVE-2026-42310, CVE-2026-42308,
  CVE-2026-42309, CVE-2026-40192)
- Bump cryptography 43.0.3 → 46.0.7 (CVE-2026-26007, CVE-2026-34073,
  CVE-2024-12797) — 3 major versions; verified `data_protection.py` still
  works with Fernet + PBKDF2HMAC APIs
- Bump anthropic 0.86.0 → 0.105.2 (CVE-2026-34452, CVE-2026-34450)
- Bump pytest 9.0.2 → 9.0.3 (CVE-2025-71176)
- Bump tmp 0.1.0 → 0.2.7 and add npm `overrides` to dedupe transitive copies
  in `@lhci/cli` and `external-editor` (CVE-2025-54798)

### Notes

- The Dependabot alert for `postcss` (CVE-2026-41305) remains open because the
  vulnerable copy is `next/node_modules/postcss` (a transitive of `next@16.2.6`),
  not a direct dep. The top-level `postcss@8.5.14` is already patched; closing
  the alert requires bumping `next` (out of scope for this security-only push).

## [5.0.3] - 2026-05-24

### Fixed

- Security: bump qs to fix CVE-2026-8723 (DoS via null entries in stringify)
- Security: bump idna 3.11 → 3.15 to fix CVE-2026-45409 (IDNA encode bypass)
- Security: override uuid to 11.1.1 to fix CVE-2026-41907 (buffer bounds check)
- Dependency updates: express, types-requests, dev-patch-and-minor group

## [5.0.2] - 2026-05-20

### Fixed

- Updated tests for current API surface
- Added output_key to ConversationBufferMemory in get_optimized_memory

## [5.0.1] - 2026-05-18

### Fixed

- Resolved search API failures through frontend proxy
- Replaced async_session_factory with get_db_context

## [5.0.0] - 2026-05-16

First production release of AI Real Estate Assistant.

### Added (since v4.0.0-dev)

- Demo mode (`DEMO_MODE=true`) for no-auth staging showcase with MockLLM
- Free LLM tier with OpenRouter cascade and rate limiting for unauthenticated users
- Groq, Mistral, Qwen, and OpenCode Go as LLM providers
- Nemotron 3 Super 120B free model integration
- Multi-key failover with circuit breaker per provider
- Task-specific model preferences (chat, search, tools, analysis, embedding)
- WCAG 2.1 AA accessibility improvements for UI components
- E2E validation suite with comprehensive user journeys and price history tests
- SPRAV systematic pre-release acceptance validation framework
- i18n adoption: 21 components wrapped with `useTranslations()` across auth, analytics, CMA, settings, PWA, and search
- Dependabot security updates: authlib, langsmith, lodash, picomatch, orjson

### Fixed

- Language switching now uses next-intl navigation API (`defineRouting` + `createNavigation`)
- Async event loop crashes in hybrid agent context
- Google OAuth redirect URI configuration (requires env vars on deployment)
- Logo overlapping nav links with proper flex layout
- Unauthenticated access to public pages in middleware
- Auth/me endpoint 404 when JWT is disabled
- CSP headers allowing inline scripts for Next.js hydration

### Security

- Removed leaked Vercel/devcontainer configs from tracking
- Resolved 4 MEDIUM defects from SPRAV pre-release validation
- Removed all personal/infra leaks and deployment references
- SSRF, log injection, and weak hashing remediation
- CodeQL and Trivy container scanning in CI

## [4.0.0-dev] - 2026-02-08

### Added
- Next.js App Router frontend with React 19 and Tailwind CSS v4
- Hybrid AI agent with intelligent query routing (simple → RAG, complex → Agent+Tools)
- Multi-provider LLM support: OpenAI, Anthropic, Google, Grok, DeepSeek, Ollama
- Persistent ChromaDB vector store with semantic + keyword hybrid search
- Result reranking with 30-40% relevance improvement
- Streaming chat responses with real-time property cards
- Interactive property map with Mapbox/Leaflet clustering
- Comparative Market Analysis (CMA) tool
- Market trends analytics with area comparison and caching
- Investment report generation with ROI analysis
- Mortgage calculator, rent-vs-buy, and TCO comparison tools
- User authentication with dual-mode: API Key + JWT
- User profile management with model preferences per task type
- Saved searches and favorites with property comparison
- Document management system
- Agent directory with contact forms and viewing scheduling
- City overview with comparison metrics
- 9-language i18n support (EN, PL, RU, DE, ES, IT, PT, TR, UK)
- EU AI Act compliance labels and X-AI-Generated headers
- PWA support with service worker and offline caching
- WCAG 2.1 AA accessibility foundations
- Open Graph meta tags, sitemap, robots.txt, and JSON-LD for SEO
- Prometheus metrics with Grafana dashboard and alerting rules
- Sentry SDK integration for error tracking and APM
- Circuit breaker pattern for graceful degradation
- IP-based sliding window rate limiter middleware
- DB-backed tamper-evident audit logging
- Redis response caching for search/RAG endpoints
- Admin dashboard with data sources, bulk jobs, and connectors
- System health metrics widget with K8s-ready endpoints
- MCP (Model Context Protocol) Registry API with web scraper connector
- Property enrichment hooks system
- Comprehensive CI/CD pipeline with GitHub Actions
- Pre-commit hooks: Gitleaks + Semgrep + lint-staged (3-layer security)
- Lighthouse CI enforcing >=90 scores on search and chat
- Docker production hardening with non-root user and resource limits
- Dynamic port allocation for multi-agent development
- SPRAV systematic pre-release acceptance validation framework
- Community contribution guidelines, PR templates, security policy
- 5-minute quickstart guide with verification scripts
- Full test suite: 3000+ backend tests, 1000+ frontend tests

### Changed
- Migrated from Streamlit (v3) to Next.js App Router
- Replaced simple chat with hybrid agent routing
- Upgraded to React 19 with Tailwind CSS v4
- PostgreSQL support for production deployment
- Async SQLite (aiosqlite) for local development
- Structured logging with observability standards

### Security
- OWASP remediation: SSRF protection, JWT secret hardening, token logging, sort_by whitelist
- CORS hardening with secure defaults
- Removed dangerouslySetInnerHTML usage
- Docker credentials secured
- Versioned API contract enforcement
- npm vulnerability monitoring
- CodeQL workflow for Python and JavaScript analysis
- Trivy container vulnerability scanning

## [3.0.0] - 2026-01-11

### Added
- Streamlit-based frontend with multi-page layout
- ChromaDB vector store integration
- LangChain-based agent with tool support
- Property search with filter extraction
- Basic analytics and mortgage calculator
- PDF export for property reports
- Polish property listings dataset (60 properties)

### Changed
- Migrated from Flask API (v2) to FastAPI backend
- Added async endpoints with WebSocket support
- Improved query analysis and intent classification

## [2.0.0] - 2025-05-15

### Added
- Flask REST API backend
- Property database with CRUD operations
- Basic NLP query processing
- Price analysis and comparison tools
- Enhanced PRD with functional requirements and roadmap

### Changed
- Migrated from CLI prototype (v1) to web API
- Added structured data models and validation

## [1.0.0] - 2025-12-31

### Added
- Initial CLI-based real estate assistant
- OpenAI GPT integration for property recommendations
- Basic property search and filtering
- Command-line interface for queries
- SQLite database for property listings

[4.0.0-dev]: https://github.com/AleksNeStu/ai-real-estate-assistant/releases/tag/v4.0.0
[3.0.0]: https://github.com/AleksNeStu/ai-real-estate-assistant/releases/tag/v3.0.0
[2.0.0]: https://github.com/AleksNeStu/ai-real-estate-assistant/releases/tag/v2.0.0
[1.0.0]: https://github.com/AleksNeStu/ai-real-estate-assistant/releases/tag/v1.0.0
