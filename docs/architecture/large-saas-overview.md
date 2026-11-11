# AI Real Estate Assistant — Architecture

**Track:** Large-SaaS
**Stack:** FastAPI (Python 3.12+) + Next.js 16 + React 19 (monorepo `apps/api` + `apps/web`)
**Status:** Public release (MIT-licensed, self-hostable)

## Layer summary

| Layer | Choice | Notes |
|---|---|---|
| Frontend | Next.js 16 (App Router), React 19, Tailwind CSS | `apps/web` |
| Backend | FastAPI in `apps/api` (routers, dependencies, middleware, auth.py) | |
| Auth | Per-product FastAPI JWT | See [docs/auth.md](../security/auth.md) |
| Database | SQLite (aiosqlite) in the deployment, PostgreSQL 16 + SQLAlchemy + Alembic for the platform tier | See [docs/database.md](../database/database.md) |
| Retrieval | ChromaDB, hybrid semantic + keyword with MMR reranking | `apps/api/vector_store/` |
| AI | Multi-provider (17 providers) for conversational property search, with a fallback chain | — |
| Deploy | Docker / Docker Compose on your own host | See [docs/deploy.md](../deployment/deploy.md) |

## Monorepo structure

```
apps/
├── api/        # FastAPI backend
└── web/        # Next.js frontend
```

## Key decisions

- Independent auth controller, no shared SSO.
- The deployment runs a real model: the provider and the model it answers with
  are reported by `GET /api/v1/capabilities`, and the interface says so.
- The catalogue is the vector store. The properties the search answers with
  live there, and the property page reads them from the same place, so the
  two speak about the same listing in the same words.

## Acquirability test

✅ Own DB, own auth, own secrets, own AI provider keys.
