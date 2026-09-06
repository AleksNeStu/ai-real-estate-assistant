# AI Real Estate Assistant — Architecture

**Track:** Large-SaaS
**Stack:** FastAPI (Python 3.12+) + Next.js 19 + React 19 (monorepo `apps/api` + `apps/web`)
**Status:** Production-ready (frozen demo per Rule 09c)

## Layer summary

| Layer | Choice | Notes |
|---|---|---|
| Frontend | Next.js 19 (App Router), React 19, Tailwind CSS | `apps/web` |
| Backend | FastAPI in `apps/api` (routers, dependencies, middleware, auth.py) | |
| Auth | Per-product FastAPI JWT | See [docs/auth.md](../security/auth.md) |
| Database | PostgreSQL 16 + SQLAlchemy + Alembic | See [docs/database.md](../database/database.md) |
| AI | Multi-provider (OpenAI, Gemini) for conversational property search | — |
| Deploy | Dokploy | See [docs/deploy.md](../deployment/deploy.md) |

## Monorepo structure

```
apps/
├── api/        # FastAPI backend
└── web/        # Next.js frontend
```

## Key decisions

- Independent auth controller, no shared SSO.
- Frozen demo per Rule 09c (CI disabled for this repo).

## Acquirability test

✅ Own DB, own auth, own secrets, own AI provider keys.
