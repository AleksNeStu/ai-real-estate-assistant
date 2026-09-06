# AI Real Estate Assistant - Backend

This is the FastAPI backend for the AI Real Estate Assistant.

## Tech Stack

- **Framework**: FastAPI (Python 3.12+)
- **ASGI Server**: Uvicorn
- **ORM**: SQLAlchemy 2.0 (async) with Alembic migrations
- **Vector Store**: ChromaDB
- **LLM Integration**: LangChain (multi-provider: OpenAI, Anthropic, Google, Ollama, OpenCode)
- **Auth**: API Key (header `X-API-Key`) + optional JWT (header `Authorization: Bearer`)
- **Package Manager**: uv (`uv.lock` is committed)
- **Testing**: pytest + pytest-asyncio + pytest-xdist

## Getting Started

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

### Install

```bash
# From this directory (apps/api/)
uv sync

# Or with pip
pip install -r requirements.txt
```

### Configure

```bash
cp .env.example .env
# Edit .env and set at least one LLM provider key (OPENAI_API_KEY, ANTHROPIC_API_KEY, GOOGLE_API_KEY)
# Set API_ACCESS_KEY to a generated secret
```

### Run

```bash
# Development (with auto-reload)
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# Production
uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 4
```

Open [http://localhost:8000/docs](http://localhost:8000/docs) for interactive Swagger UI.

### Migrate Database

```bash
alembic upgrade head
```

## Project Structure

- `api/` — FastAPI routers, `main.py`, `dependencies.py`, `middleware/`, `auth.py`
- `agents/` — HybridAgent, QueryAnalyzer, services, web_research_agent
- `tools/` — LangChain tools (mortgage, comparison, etc.)
- `models/` — LLM provider factory and per-provider implementations
- `config/` — Settings (Pydantic)
- `db/` — SQLAlchemy models, schemas, repositories, database session
- `alembic/` — Database migrations
- `vector_store/` — ChromaPropertyStore, KnowledgeStore, reranker
- `data/` — Data loaders, enrichment pipeline, schemas
- `services/` — Business logic services
- `core/` — JWT, security utilities, shared helpers
- `notifications/` — Email service, scheduler, uptime monitor
- `tests/` — unit, integration, e2e, performance

## Key Features

- **Conversational AI**: Property search via natural language with query routing (RAG / Hybrid / Agent+Tools)
- **Multi-tenancy**: User-isolated data via `X-User-Email` header → per-user preferences
- **Vector Search**: ChromaDB-backed semantic property search with reranking
- **LLM Provider Cascade**: Per-user, per-task model preferences with system defaults and Ollama fallback
- **Auth Dual-Mode**: API Key for backend access, JWT for user features (favorites, saved searches, market, leads)
- **API Proxy Friendly**: Designed to be called via the Next.js frontend proxy (X-API-Key is server-injected)

## Environment Variables

See `.env.example` for the full list. Critical ones:

| Variable | Required | Description |
|----------|----------|-------------|
| `ENVIRONMENT` | Yes | `local` for development |
| `API_ACCESS_KEY` | Yes | Backend API key (server-side only) |
| `OPENAI_API_KEY` | One+ | LLM provider key |
| `ANTHROPIC_API_KEY` | One+ | LLM provider key |
| `GOOGLE_API_KEY` | One+ | LLM provider key |
| `CORS_ALLOW_ORIGINS` | Yes | Allowed frontend origins |
| `SECURITY_PEPPER` | Recommended | High-entropy secret for HMAC-SHA-256 fingerprinting |
| `ENABLE_JWT_AUTH` | No | Enable JWT auth (default: `false`) |
| `OLLAMA_BASE_URL` | No | Local LLM fallback |

## Testing

```bash
# All tests with coverage (from this directory)
pytest tests/unit tests/integration --cov=. --cov-report=term -n auto

# Single file
pytest tests/unit/test_query_analyzer.py -v

# Single test
pytest tests/unit/test_query_analyzer.py -k test_fn -v
```

## Linting & Formatting

```bash
ruff check .        # Lint
ruff format .       # Format
mypy .              # Type check (strict)
```

## Security Notes

- Never expose `API_ACCESS_KEY`, `SECURITY_PEPPER`, or any `*_API_KEY` to the browser. These must stay server-side.
- The `SECURITY_PEPPER` env var should be set to a high-entropy secret in production. An insecure placeholder is used as a fallback if unset — the app logs a warning when this happens.
- CORS is enforced via `CORS_ALLOW_ORIGINS`. In development, set this to your frontend dev origin (e.g. `http://localhost:3000`).
- API rate limiting is on by default (`API_RATE_LIMIT_ENABLED=true`, `API_RATE_LIMIT_RPM=600`).
- See [SECURITY.md](SECURITY.md) for the full security policy and responsible disclosure process.

## Deployment

Docker images are published to GHCR (`ghcr.io/aleksnestu/ai-real-estate-assistant/backend`).
See the [Deployment Guide](../../docs/deployment/DEPLOYMENT.md) for Dokploy / Render setup.

For the public demo, see [https://realestate-api-wkm7.onrender.com/health](https://realestate-api-wkm7.onrender.com/health).
