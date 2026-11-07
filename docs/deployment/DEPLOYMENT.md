# Deployment Guide

This guide covers deploying the AI Real Estate Assistant.

## Prerequisites

Before deploying, ensure you have:

- A GitHub repository with the code
- Generated `API_ACCESS_KEY` (run: `openssl rand -hex 32`)
- Docker and Docker Compose (for local/containerized deployment)
- A host with a domain and TLS (for a public deployment)

---

## Architecture Overview

```
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│   Browser       │──────│  Frontend       │──────│  Backend        │
└─────────────────┘      │  Next.js App    │      │  FastAPI        │
                         │  /api/v1/*      │      │  Port 10000     │
                         └─────────────────┘      └─────────────────┘
```

**Key:** The frontend proxies all `/api/v1/*` requests server-side, injecting the API key. The browser never sees backend credentials.

---

## Environment Variables

| Variable | Description | Where to Set |
|----------|-------------|-------------|
| `API_ACCESS_KEY` | Backend authentication key | Backend host + Frontend |
| `BACKEND_API_URL` | Backend endpoint URL | Frontend only (server-side) |
| `NEXT_PUBLIC_API_URL` | Frontend API prefix (`/api/v1`) | Frontend (build time) |
| `OPENAI_API_KEY` | LLM provider key | Backend |
| `CORS_ALLOW_ORIGINS` | Allowed origins | Backend |

---

## Docker Compose Deployment

### Step 1: Clone and Configure

```bash
git clone https://github.com/AleksNeStu/ai-real-estate-assistant.git
cd ai-real-estate-assistant
cp .env.example .env
# Edit .env with your keys
```

### Step 2: Start Services

```bash
docker compose -f deploy/compose/docker-compose.yml up -d

# Check status
docker compose -f deploy/compose/docker-compose.yml ps

# View logs
docker compose -f deploy/compose/docker-compose.yml logs -f
```

### Step 3: Verify

```bash
# Backend health
curl http://localhost:8000/health

# Frontend
open http://localhost:3000
```

---

## Self-Hosted Deployment

The repository ships the Docker Compose stack; you run it on your own host.

### Step 1: Build the backend image

```bash
cd apps/api
docker build -f ../../deploy/docker/Dockerfile.backend -t ai-real-estate-backend .
```

### Step 2: Build the frontend image

```bash
cd apps/web
docker build -f ../../deploy/docker/Dockerfile.frontend -t ai-real-estate-frontend .
```

### Step 3: Start the stack

```bash
cp deploy/compose/.env.example deploy/compose/.env
# Edit deploy/compose/.env with your keys

docker compose -f deploy/compose/docker-compose.yml up -d
```

### Environment variables

Backend:

```bash
ENVIRONMENT=production
API_ACCESS_KEY=<your-key>
OPENAI_API_KEY=sk-...
CORS_ALLOW_ORIGINS=https://your-frontend.example.com
```

Frontend:

```bash
BACKEND_API_URL=https://your-backend.example.com
API_ACCESS_KEY=<same-key-as-backend>
NEXT_PUBLIC_API_URL=/api/v1
```

### Step 4: Put a reverse proxy in front

Terminate TLS with Caddy, Traefik, or Nginx and point your domain at the frontend.
See [docs/guides/deployment.md](../guides/deployment.md) for the Caddy walkthrough.

### Known Limitations (constrained host)

- A 512 MB cap is not enough for a local LLM, web search, or a multi-worker backend
- The disk is ephemeral — anything user-generated is lost on the next deploy
- Use a persistent volume and a real database for anything load-bearing

---

## Post-Deployment Verification

```bash
# Backend health
curl https://your-backend.example.com/health

# Auth test
curl -X POST https://your-frontend.example.com/api/v1/verify-auth \
  -H "X-API-Key: $API_ACCESS_KEY"
```

---

## Troubleshooting

### CORS Errors

1. Verify `CORS_ALLOW_ORIGINS` includes your frontend URL
2. Check `ENVIRONMENT=production` is set

### 502 Bad Gateway

- The backend may still be starting up (wait 2-3 min)
- Check the backend container logs

### Build Failures

- Verify all environment variables are set
- Check the build logs

---

## Related

- [DEPLOYMENT_VARIANTS.md](../../DEPLOYMENT_VARIANTS.md) — comparison of Local Docker, VPS, and a constrained host (feature matrix)
- [Docker Deployment Guide](../guides/deployment.md)
- [CI/CD Pipeline](../guides/ci-cd.md)
- [Troubleshooting](../guides/troubleshooting.md)
