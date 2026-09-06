# AI Real Estate Assistant — Database

| Item | Value |
|---|---|
| Engine | PostgreSQL 16 LTS (prod) / 18 (dev) |
| ORM | SQLAlchemy + Alembic |
| Connection env var | `DATABASE_URL` |

## Multi-tenancy

Single-tenant demo deployment (per-tenant scoping deferred to post-freeze).

## Migration workflow

```bash
cd apps/api
alembic revision --autogenerate -m "<change>"
alembic upgrade head
```

## Schema overview

- `users` — auth + profile
- `conversations` — chat session metadata
- `messages` — conversation history
- `property_cache` — recent property search results (TTL cleanup)
- `mls_listings` — ingested MLS data
