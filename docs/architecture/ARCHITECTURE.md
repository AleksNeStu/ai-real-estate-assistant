# Architecture

## System Overview
The AI Real Estate Assistant is a modern, conversational AI platform helping users find properties
through natural language. It features a split architecture with a Next.js frontend and a FastAPI
backend and follows an Open Core & Walled Garden model: Community Edition (public) and Hosted Pro
(private, non-repo).

### Core Components
- **Frontend**: Next.js 16 (App Router), React 19, TypeScript, Tailwind CSS v4, Shadcn UI.
- **Backend**: FastAPI (Python 3.12+), Pydantic, SSE streaming.
- **AI Engine**: Hybrid Agent (RAG + Tools), Query Analyzer, Strategic Reranker.
- **Data**: ChromaDB (Vector Store), Pandas (Analytics), PostgreSQL/JSON (Persistence).

### Open Core Split
- **Community Edition (Open Source, MIT)**: local RAG, chat/tools, prompt templates, local
  deployment (Docker Compose), BYOK for LLM (OpenAI key or local Ollama/Llama 3), webhooks for
  integrations.
- **Hosted Pro (Private)**: multi-agent orchestration, legal risk checks on proprietary datasets,
  data enrichment via configured APIs, deep CRM sync, voice/telephony, analytics dashboards.
  Implemented outside this repository.

## Detailed Component Design

### 1. Frontend Architecture (Next.js)
- **Framework**: Next.js 16 (App Router).
- **Styling**: Tailwind CSS + Shadcn UI.
- **State Management**: React Hooks + LocalStorage for preferences.
- **Directory Structure**:
    - `src/app`: Pages and layouts (App Router).
    - `src/components/ui`: Atomic UI components (Button, Input, Card).
    - `src/components/layout`: Global layout components (MainNav).
    - `src/lib`: Utility functions, API clients (`api.ts`), and types.

#### Key Features
- **Theming**: Dark/light mode via `next-themes` or manual CSS class toggling.
- **Streaming**: Consumes Server-Sent Events (SSE) from `/api/v1/chat` for real-time AI responses.
- **API Proxy**: The web app calls `/api/v1/*` on the Next.js server, which proxies to the FastAPI backend and injects `X-API-Key` server-side (no secrets in browser bundles). In production, the proxy requires `BACKEND_API_URL` and rejects localhost targets.
- **Auth**: Email-based OTP login flow (`/api/v1/auth`).

### 2. Backend Architecture (FastAPI)
- **API Router**: Modular routers in `api/routers/` (chat, search, admin, settings).
- **Dependencies**: Dependency injection for LLMs, Vector Store, and Services via `api/dependencies.py`.
- **Observability**: Request ID tracking, structured logging, rate limiting.
- **CORS**: In production, allowed origins are pinned via `CORS_ALLOW_ORIGINS`; development allows `*`.

#### Extension Points (Interfaces)
- **LLM Provider (`models/provider_factory.py`)**: abstraction to select local/Ollama or BYOK
  providers. Pro overrides can plug higher-tier models privately.
- **RAG Provider (`vector_store/*`)**: interface for embedding and retrieval. CE uses local stores;
  Pro can route to managed/paid stores.
- **Valuation Provider (`agents/services/valuation.py`)**: default stub/simple formula in CE. Pro
  replaces with a paid API adapter.
- **CRM Connector (`agents/services/crm_connector.py`)**: CE uses webhooks. Pro provides
  bidirectional connectors (AmoCRM/Bitrix24/kvCORE) privately.
- **Data Enrichment Service (`agents/services/data_enrichment.py`)**: disabled/minimal in CE. Pro
  uses configured open data APIs.
- **Legal Check Service (`agents/services/legal_check.py`)**: CE basic heuristics. Pro uses a
  proprietary legal KB and models.

#### Feature Flags
- Flags select implementations for interfaces above. CE exposes only safe toggles; Pro flags are
  private and not published. Flags are read from env and never expose secrets in client code.

#### Key Data Flows
- **Ingestion**: CSV/API -> Pandas -> Cleaning -> Embeddings -> ChromaDB.
- **Search**: Query -> Analyzer -> Hybrid Retrieval (Semantic + Keyword) -> Reranking -> Response.
- **Filters**: Frontend collects min/max price, rooms, property type -> API forwards `filters` ->
  Vector Store converts to Chroma query via `_build_chroma_filter`
- **Chat**: User Message -> Hybrid Agent -> Tool Selection (Calculator, Search, etc.) -> LLM Response.

### 3. Notification System
The digest system bridges raw property data and user notifications.

- **DigestGenerator (`notifications/digest_generator.py`)**:
    - Gathers data for email digests from `VectorStore` (new matches) and `MarketInsights`.
    - Iterates through `SavedSearch` objects to find relevant updates.
- **AlertManager (`notifications/alert_manager.py`)**:
    - Sends emails for price drops, new property matches, and digests with deduplication.
    - Persists queued alerts (`pending_alerts.json`) and dedupe keys (`sent_alerts.json`) under `.alerts/`.
- **NotificationScheduler (`notifications/scheduler.py`)**:
    - Runs periodic digest + instant alert checks and enforces quiet hours by queuing alerts.
    - Processes queued alerts after quiet hours end.
- **EmailService**:
    - Renders responsive HTML templates (`DigestTemplate`) and sends via SMTP/SendGrid.

### 4. Data Providers
- **BaseDataProvider**: Abstract interface for data fetching.
- **Implementations**:
    - `CsvProvider`: Loads local/remote CSVs.
    - `ApiProvider`: Fetches from external REST APIs.
    - `JsonProvider`: Loads JSON datasets.

## Technology Stack
- **Web**: Next.js 16 (App Router), TypeScript, Tailwind CSS v4
- **Backend**: FastAPI (Python 3.12), Pydantic 2.5+, SSE streaming
- **Vector Store**: ChromaDB 0.5+
- **Embeddings**: FastEmbed (BGE) or OpenAI embeddings
- **Testing**: Pytest (Backend), Jest (Frontend)
- **Deployment**: Docker, Render (staging)
- **CI/CD**: GitHub Actions (ruff lint, unit and integration pytest with coverage artifacts)

## Security & Licensing
- **Licensing**: Community Edition under the MIT licence (see `LICENSE`). Hosted Pro is
  proprietary and operated privately.
- **Secrets**: Never stored client‑side. Env variables on server; redact logs; rate limit per client.

## Quality Gates
- Static analysis: ruff (lint) in CI; mypy is configured in `apps/api/pyproject.toml` but
  is not run by the pipeline; a custom RuleEngine lives in `rules/`.
- RuleEngine scope: ignores translation/templates; enforces max line length and no secrets.
- Coverage targets: unit ≥85%, integration ≥70% — the thresholds the pipeline
  reports on its coverage artifacts.

## API Surface
- **Search**: `/api/v1/search`
- **Chat**: `/api/v1/chat` (SSE supported; responses include `X-Request-ID`; streaming emits text deltas plus a final `meta` event with `sources` that may be truncated via `CHAT_SOURCES_*` limits)
- **Tools**: `/api/v1/tools/*` (mortgage, compare, price analysis, location analysis; CE stubs:
  valuation, legal-check, enrich-address, crm-sync-contact)
- **Prompt Templates**: `/api/v1/prompt-templates`, `/api/v1/prompt-templates/apply`
- **Settings**: `/api/v1/settings/notifications`, `/api/v1/settings/models` (local providers include `runtime_available`/`available_models`/`runtime_error`), `/api/v1/settings/test-runtime` (targeted local runtime check), `/api/v1/settings/model-preferences`
- **Auth**: `/api/v1/auth/*`
- **Admin**: `/api/v1/admin/*` (health, metrics, ingest, reindex, notifications-stats)
- **RAG (CE)**: `/api/v1/rag/upload`, `/api/v1/rag/qa`, `/api/v1/rag/reset` (optional per-request `provider`/`model` overrides; citations include `source`/`chunk_index` plus optional `page_number`/`paragraph_number`)
