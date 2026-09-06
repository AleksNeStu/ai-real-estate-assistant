# AI Real Estate Assistant — Deployment

## Target

| Environment | Platform | VPS | Domain |
|---|---|---|---|
| Development | Local (scripts/start.sh) | localhost | localhost |
| Staging | Dokploy | VPS2 | *(staging domain — see ops runbook)* |
| Production | Dokploy | VPS3 (or Render demo) | *(domain TBD)* |

> **Frozen demo per Rule 09c.** CI auto-triggers are disabled for this repo; deployments
> are manual only.

## Build

```bash
# Backend
cd apps/api
pip install -r requirements.txt
alembic upgrade head
uvicorn main:app --host 0.0.0.0 --port 8000

# Frontend
cd apps/web
pnpm install
pnpm build
pnpm start
```

## CI/CD

- Tag-based manual release (no auto-deploy).
