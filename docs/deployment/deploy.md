# AI Real Estate Assistant — Deployment

## Target

| Environment | Platform | Host | Domain |
|---|---|---|---|
| Development | Local (Docker Compose or local scripts) | localhost | localhost |
| Staging | Your own host / your CI | your host | your staging domain |
| Production | Your own host / your CI | your host | your domain |

> **Frozen demo per Rule 09c.** The public repository is a demo: CI runs on every
> push and pull request to `main` and `dev` (path-filtered), and releases are
> tag-driven. Deployment to your own environment is a manual step.

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

- CI runs on every push and pull request to `main` and `dev`.
- Releases are tag-driven: push a `v*` tag to publish container images.
- Deployment to your own environment is manual — the public repository does not
  ship an environment-specific deployment configuration.
