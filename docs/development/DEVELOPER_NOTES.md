# Developer Notes

## Overview
This document captures practical details for working on the FastAPI backend and Next.js frontend.

## Development Process
- CI is expected to run on every PR and push; keep ruff and the test suites green before merging.
  The pipeline does not run mypy and reports the coverage thresholds rather than enforcing them;
  `scripts/ci/ci_parity.py` is the local helper that runs the full set.

## Backend (FastAPI)
- Entry point: `api/main.py`
- Routers: `api/routers/*` (chat, search, tools, settings, admin, auth)
- OpenAPI:
  - Runtime schema: `http://localhost:8000/openapi.json`
  - Repo snapshot: `docs/api/openapi.json`
  - The committed endpoint list is compared with that snapshot by the test suite
    (`tests/integration/api/test_api_reference_full_integration.py`)
- Observability: `api/observability.py` adds:
  - `X-Request-ID` header to all responses (including unexpected `500` errors)
  - Per-client rate limiting for `/api/v1/*`
  - Structured JSON logs (`utils/json_logging.py`) with `event`, `request_id`, `client_id`,
    `method`, `path`, `status`, `duration_ms`
- Auth: API key via `X-API-Key` header (`config/settings.py` -> `API_ACCESS_KEY` / `API_ACCESS_KEYS`)
- CORS:
  - Development: `ENVIRONMENT!=production` → `allow_origins=["*"]`
  - Production: `ENVIRONMENT=production` → `CORS_ALLOW_ORIGINS` (comma-separated list)
  - **Production validation**: Wildcard `*` and empty origins are rejected in production (fail-fast at startup)
  - The API exposes `X-Request-ID` via `Access-Control-Expose-Headers` so browser clients can read it
  - Example:
    ```powershell
    $env:ENVIRONMENT="production"
    $env:CORS_ALLOW_ORIGINS="https://yourapp.com,https://your-app.example.com"
    ```

## Configuration
- Source: `config/settings.py` (`AppSettings`)
- Key env vars:
  - `ENVIRONMENT` (`development` | `production`)
  - `CORS_ALLOW_ORIGINS` (comma-separated URLs; used in production)
  - `API_RATE_LIMIT_ENABLED` (`true`/`false`)
  - `API_RATE_LIMIT_RPM` (requests per minute)
  - `API_ACCESS_KEY` (single key; defaults to `dev-secret-key` when `ENVIRONMENT!=production` and unset)
  - `API_ACCESS_KEYS` (comma-separated list for key rotation; any listed key is accepted; whitespace is trimmed, empty entries are ignored, and duplicates are removed)
  - Key rotation runbook: deploy with `API_ACCESS_KEYS="NEW,OLD"` (both valid), migrate clients/operators to `NEW`, then redeploy with `API_ACCESS_KEYS="NEW"` and verify `OLD` fails against `GET /api/v1/verify-auth` (details in `docs/SECURITY.md`)
  - Chat sources payload limits (SSE `event: meta` and non-stream `ChatResponse.sources`):
    - `CHAT_SOURCES_MAX_ITEMS` (default `5`)
    - `CHAT_SOURCE_CONTENT_MAX_CHARS` (default `2000`)
    - `CHAT_SOURCES_MAX_TOTAL_BYTES` (default `20000`)
  - Local RAG upload limits:
    - `RAG_MAX_FILES` (default `10`)
    - `RAG_MAX_FILE_BYTES` (default `10485760`)
    - `RAG_MAX_TOTAL_BYTES` (default `26214400`)
  - Email (optional; enables digest delivery when users opt in):
    - `SMTP_PROVIDER` (`gmail` | `outlook` | `sendgrid` | `custom`)
    - `SMTP_USERNAME` / `SMTP_PASSWORD`
    - `SMTP_FROM_EMAIL` (optional; defaults to username)
    - `SMTP_FROM_NAME` (optional; defaults to "Real Estate Assistant")
    - `SMTP_USE_TLS` / `SMTP_USE_SSL` (optional; defaults `true` / `false`)
    - `SMTP_TIMEOUT` (optional; seconds, default `30`)
    - Custom SMTP only: `SMTP_SERVER`, `SMTP_PORT`
  - `CRM_WEBHOOK_URL` (optional; enables CE CRM webhook connector)
  - `DATA_ENRICHMENT_ENABLED` (`true`/`false`; enables CE enrichment endpoint)
  - `VALUATION_MODE` (default `simple`; set to non-`simple` to disable CE valuation stub)
  - `LEGAL_CHECK_MODE` (default `basic`; set to non-`basic` to disable CE legal check stub)
  - `UPTIME_MONITOR_ENABLED` (`true`/`false`)
  - `UPTIME_MONITOR_HEALTH_URL` (default `http://localhost:8000/health`)
  - `UPTIME_MONITOR_EMAIL_TO` (ops email recipient)
  - `UPTIME_MONITOR_INTERVAL` (seconds, default `60`)
  - `UPTIME_MONITOR_FAIL_THRESHOLD` (default `3`)
  - `vector_persist_enabled` (`true`/`false`; enable Chroma persistence)
  - `CHROMA_FORCE_FASTEMBED` (`1` to force FastEmbed on Windows)
  - `FORCE_FASTEMBED` (`1` to force FastEmbed on Windows; alias)
  - `UPTIME_MONITOR_COOLDOWN_SECONDS` (default `1800`)

## Optional Dependencies
- `langchain-experimental` is required only for the legacy dataframe agent (`ai/agent.py` -> `RealEstateGPT`). The API does not depend on it.

## Testing
- Full CI parity commands (Windows): see `docs/testing/TESTING_GUIDE.md`.
- One-command backend CI parity:
  ```powershell
  python scripts\ci\ci_parity.py
  ```
- CI parity (dry run; prints commands only):
  ```powershell
  python scripts\ci\ci_parity.py --dry-run
  ```
- Run all tests:
  ```powershell
  python -m pytest
  ```
- Unit/integration specificity:
  ```powershell
  python -m pytest tests/unit
  python -m pytest tests/integration
  ```
- Coverage (backend packages):
  ```powershell
  python -m pytest -q --cov=api --cov=config --cov-report=term-missing
  ```
- Linting:
  ```powershell
  python -m ruff check .
  ```
- Type checking:
  ```powershell
  python -m mypy
  ```

## Quality Gates
- Static rules: RuleEngine checks line length, secrets, and loop concatenations.
- Config: rules/config.py defines IGNORE_PATTERNS and MAX_LINE_LENGTH.
- i18n safety: backend tests validate any `get_text("<literal>")` usage references an existing translation key.
- Run RuleEngine (CI-equivalent):
  ```powershell
  python -m pytest -q tests\integration\test_rule_engine_clean.py
  ```
- Forbidden token scan (CI-equivalent):
  ```powershell
  python scripts\security\forbidden_tokens.py
  ```
- Run RuleEngine (sample):
  ```powershell
  python -c "from rules.engine import RuleEngine; print('rules ready')"
  ```
- Lint/typecheck: keep ruff and mypy clean before commit.
- Coverage thresholds (CE): unit ≥85%, integration ≥70% — reported by the pipeline on its
  coverage artifacts, and enforced by the local parity helper.

## Frontend (Next.js)
- Directory: `frontend/`
- One-command dev start (backend + frontend):
  ```powershell
  .\scripts\dev\start.ps1
  ```
- Useful flags:
  - `--mode local --service backend` (backend only)
  - `--mode local --dry-run` (prints commands; secrets redacted)
  - `--mode local --no-bootstrap` (skip uv bootstrap)
- More: `docs/scripts/LOCAL_DEVELOPMENT.md`
- Dev:
  ```powershell
  cd frontend
  npm install
  npm run dev
  ```
- Tests:
  ```powershell
  cd frontend
  npm test
  ```
- Mapping (Search Map view):
  - Libraries: `leaflet`, `react-leaflet`
  - Tiles: OpenStreetMap (`https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png`) via the browser (no API key required)
  - Marker clustering: client-side, zoom-aware grouping to keep dense result sets readable
  - Cluster interaction: clicking a cluster fits to the cluster bounds (max zoom = current zoom + 2, capped at 18)
- E2E (Playwright):
  ```powershell
  $env:PLAYWRIGHT_START_WEB='1'
  npx playwright test -c playwright.config.ts --reporter=list
  ```
- Playwright env vars:
  - `PLAYWRIGHT_BASE_URL` (default `http://localhost:3000`)
  - `PLAYWRIGHT_START_WEB` (`1`/`true` to auto-start Next.js dev server)
  - `PLAYWRIGHT_OUTPUT_DIR` (default `artifacts/playwright`)
  - `PLAYWRIGHT_SCREENSHOT_DIR` (default `artifacts/playwright/screenshots`)
  - `PLAYWRIGHT_LOG_DIR` (default `artifacts/playwright/logs`)
- Client configuration:
  - `NEXT_PUBLIC_API_URL` points to the frontend proxy base (default `/api/v1`)
  - Next.js proxies `/api/v1/*` server-side to `BACKEND_API_URL`, injecting `API_ACCESS_KEY` (or first of `API_ACCESS_KEYS`) as `X-API-Key` (no `NEXT_PUBLIC_*` secret fallback)
  - Production safety: `BACKEND_API_URL` is required when `NODE_ENV=production` and must not point to localhost; the proxy returns `500 {"detail": "..."}`
  - `userEmail` stored in `localStorage` is forwarded as `X-User-Email`
  - `modelPrefs:<email>` stored in `localStorage` caches per-user default model selection
  - Knowledge (Local RAG) page: `frontend/src/app/knowledge/page.tsx` calls `/api/v1/rag/upload` via multipart FormData (do not set `Content-Type` manually)
- Chat streaming:
  - `streamChatMessage` parses SSE messages from `POST /api/v1/chat` when `"stream": true`
  - Text deltas are JSON: `data: {"content":"<delta>"}`
  - Final citations are emitted as `event: meta` with `data: {"sources":[...],"sources_truncated":false,"session_id":"..."}`
  - `data: [DONE]` ends the stream; `X-Request-ID` is available on the streaming response

## Settings (Backend)
- Notification preferences storage: `.preferences/notification_preferences.json`
- Model preferences storage: `.preferences/model_preferences.json`
- Endpoints:
  - `GET/PUT /api/v1/settings/notifications` (requires `X-User-Email` or `?user_email=`)
  - `GET /api/v1/settings/models` (catalog only; local providers include `runtime_available`, `available_models`, and `runtime_error` derived from `validate_connection()`). The Settings UI exposes a **Refresh Catalog** action that re-fetches this endpoint to update local runtime diagnostics.
  - `GET /api/v1/settings/test-runtime?provider=<provider_name>` (local providers only; runs a targeted runtime check without reloading the entire catalog)
  - `GET/PUT /api/v1/settings/model-preferences` (requires `X-User-Email` or `?user_email=`)
- LLM selection:
  - [get_llm](../../apps/api/api/dependencies.py) loads per-user model preferences
    via `X-User-Email`
  - Falls back to `settings.default_provider`/`settings.default_model` if preferences are missing or invalid

## CI/CD
- GitHub Actions workflow: `.github/workflows/ci.yml`
- Backend:
  - Lint: `ruff`
  - Tests: the unit and integration suites, each with `--cov`, uploading a coverage artifact
  - Coverage: the line-rate of each suite is compared with its threshold (unit 85,
    integration 70) and reported as an annotation - the job is not failed by it
  - `mypy` is not part of the pipeline; the local parity helper runs it together with
    `scripts/ci/coverage_gate.py` (diff and critical coverage)
- Frontend:
  - Lint: `npm run lint`
  - Tests + coverage: `npm run test -- --ci --coverage` (thresholds enforced in `jest.config.ts`)
- Artifacts: coverage reports uploaded per job
- Docker Compose smoke:
  - CI runs a Compose smoke job that builds backend/frontend images and waits for `/health` + the frontend `/`.
  - If `API_ACCESS_KEY` or `API_ACCESS_KEYS` is set, the smoke script also verifies `GET /api/v1/verify-auth` using `X-API-Key`.
  - Local equivalent: `python scripts\ci\compose_smoke.py --ci`
- Security:
  - CI jobs: `security` (Bandit) and `audit` (pip-audit) in `.github/workflows/ci.yml`
  - Static analysis: Bandit (fail on high severity/high confidence): `python -m bandit -r api agents ai analytics config data i18n models notifications rules scripts tools utils vector_store workflows -lll -iii`
  - Dependency audit: pip-audit (fail on vulnerabilities): `python -m pip_audit -r requirements.txt`

## Branch Protection
- Protect `main` and `dev` branches with required CI checks:
  - Backend jobs (ruff lint; unit and integration pytest with coverage artifacts)
  - Frontend job (eslint, jest)
  - Security job (Bandit: high severity/high confidence)
- Enable “Require branches to be up to date”, “Include administrators”, and “Block force pushes”.

## Notes
- Do not commit secrets; use environment variables.
- In development, `auth/request-code` returns the code inline for easier testing.
- Notifications:
  - The notification scheduler starts on API startup and evaluates user preferences periodically.
  - If SMTP is not configured, email delivery is skipped (preferences are still stored).
  - Instant alerts during quiet hours are queued to `.alerts/pending_alerts.json` and delivered after quiet hours end.
  - Alert deduplication uses `.alerts/sent_alerts.json` to avoid repeated sends for the same event.
  - Ops visibility: `GET /api/v1/admin/notifications-stats` returns queue/sent counts derived from `.alerts/*` (requires `X-API-Key`).

## Monitoring
- Health endpoints:
  - `/health` (system)
  - `/api/v1/admin/health` (admin with cache/store indicators)
  - `/api/v1/admin/version` (admin runtime/build info)
- Uptime monitor:
  - Module: `notifications/uptime_monitor.py`
  - Periodically runs a checker and sends alert emails on consecutive failures
  - Configurable interval, fail threshold, and alert cooldown

## Search Filters (End-to-End)
- UI (Next.js): `frontend/src/app/search/page.tsx` collects `min_price`, `max_price`, `rooms`,
  `property_type` and validates query/price range (neutral state before first search)
- UI Map view: toggles between list and map; map plots results with `property.latitude`/`property.longitude`
- Client API: `frontend/src/lib/api.ts` sends `filters` in `POST /api/v1/search` payload
- Backend Router: `api/routers/search.py` forwards `request.filters` to `store.hybrid_search`
- Vector Store: `vector_store/chroma_store.py` converts filters to Chroma format via `_build_chroma_filter`

Testing:
- Unit: `tests/unit/api/test_api_search_filters.py` (router forwards filters)
- Unit: `tests/unit/test_chroma_filters.py` (filter conversion)
- Integration: `tests/integration/api/test_api_search_filters_integration.py` (endpoint accepts filters)

## Search Sorting (End-to-End)
- UI (Next.js): `frontend/src/app/search/page.tsx` provides `sort_by` and `sort_order` controls
- Client API: `frontend/src/lib/api.ts` includes `sort_by` and `sort_order` in `POST /api/v1/search`
- Backend Router: `api/routers/search.py` forwards sort params to `store.hybrid_search`
- Vector Store: `vector_store/chroma_store.py` sorts by metadata fields (`price`, `price_per_sqm`,
  `area_sqm`, `year_built`)

Testing:
- Unit: `tests/unit/api/test_api_search_sorting.py` (router forwards sorting)
- Integration: `tests/integration/api/test_api_search_sorting_integration.py` (endpoint accepts sorting)

## Export (End-to-End)
- UI (Next.js):
  - `frontend/src/app/search/page.tsx` exports search results (format + optional columns + CSV locale options)
  - `frontend/src/app/tools/page.tsx` exports by IDs from the Compare tool
- Client API: `frontend/src/lib/api.ts` provides `exportPropertiesBySearch(...)` and `exportPropertiesByIds(...)`
- Backend Router: `api/routers/exports.py` handles `POST /api/v1/export/properties` for IDs or search
- Utils: `utils/exporters.py` supports `csv`, `xlsx`, `json`, `md`, `pdf` (columns filtering for `csv`/`xlsx`/`json`)

Testing:
- Unit: `tests/unit/api/test_api_exports.py` (formats, headers, errors)
- Integration: `tests/integration/api/test_api_exports_integration.py` (auth + validation + CSV option acceptance)

## Prompt Templates (End-to-End)
- Templates library: `ai/prompt_templates.py` (CE-safe, static catalog)
- Router: `api/routers/prompt_templates.py`
- Endpoints (requires `X-API-Key`):
  - `GET /api/v1/prompt-templates` (catalog + variable schemas)
  - `POST /api/v1/prompt-templates/apply` (render by `template_id` + `variables`)
- Placeholder syntax: `{{variable_name}}` (validated against the declared variable list)

Testing:
- Unit: `tests/unit/test_prompt_templates.py` (render/validation)
- Unit (API): `tests/unit/api/test_api_prompt_templates.py`
- Integration: `tests/integration/api/test_api_prompt_templates_integration.py`

## Local RAG (Community Edition)
- Knowledge store module: `vector_store/knowledge_store.py`
- Routers: `api/routers/rag.py` (`/api/v1/rag/upload`, `/api/v1/rag/qa`, `/api/v1/rag/reset`)
- Supported ingestion types (CE): `.txt`, `.md`
- Supported with optional install: `.pdf` (`pip install pypdf`), `.docx` (`pip install python-docx`)
- PDF uploads preserve `page_number` metadata per chunk; DOCX uploads preserve `paragraph_number` metadata per chunk.
- `/api/v1/rag/qa` citations include `source` + `chunk_index` and may include `page_number` / `paragraph_number`.
- If nothing is indexed (only errors), the upload endpoint returns `422` with a structured error list.
- `/api/v1/rag/qa` accepts optional `provider` / `model` overrides in the JSON body; otherwise it uses per-user preferences (`X-User-Email`) or defaults.
- `/api/v1/rag/reset` clears all indexed documents to allow deterministic “start fresh” flows in the UI and tests.

Environment flags:
- `EMBEDDING_MODEL` via `settings.embedding_model` (FastEmbed/OpenAI)
- `vector_persist_enabled` controls Chroma persistence (`config/settings.py`)
- `RAG_MAX_FILES`, `RAG_MAX_FILE_BYTES`, `RAG_MAX_TOTAL_BYTES` control upload limits for `/api/v1/rag/upload`

Testing:
- Unit: `tests/unit/api/test_api_rag.py`
- Integration: `tests/integration/api/test_api_rag_integration.py`
