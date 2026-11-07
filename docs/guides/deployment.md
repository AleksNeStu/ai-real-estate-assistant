# Deployment Guide

This guide covers deploying the AI Real Estate Assistant.

## Table of Contents

- [Overview](#overview)
- [Pre-Deployment Checklist](#pre-deployment-checklist)
- [Deployment Methods](#deployment-methods)
- [Docker Deployment](#docker-deployment)
- [Render Staging Deployment](#render-staging-deployment)
- [Post-Deployment](#post-deployment)
- [Monitoring](#monitoring)

---

## Overview

The AI Real Estate Assistant consists of:

1. **Backend**: FastAPI application (Python 3.12+)
2. **Frontend**: Next.js application (React 19)
3. **Optional Services**: Redis, Ollama, SearXNG

### Architecture

```
                    ┌─────────────────┐
                    │   Browser       │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  Render (Front) │  ← HTTPS
                    │  Next.js App    │
                    │  /api/v1/*      │
                    └────────┬────────┘
                             │ Server-side proxy
                    ┌────────▼────────┐
                    │  Render (Back)  │  ← HTTPS
                    │  FastAPI        │
                    │  Port 10000     │
                    └─────────────────┘
```

---

## Pre-Deployment Checklist

### 1. Security

- [ ] Generated strong `API_ACCESS_KEY` (`openssl rand -hex 32`)
- [ ] Set `CORS_ALLOW_ORIGINS` to specific domains
- [ ] Configured `ENVIRONMENT=production`
- [ ] No secrets in client-side code
- [ ] Reviewed `.gitignore` for sensitive files

### 2. Code Quality

```bash
# Run full CI locally
make ci

# Security scan
make security
```

### 3. Database

- [ ] Database backup plan in place
- [ ] Migration strategy defined
- [ ] Database connection string configured

### 4. Environment Variables

```bash
# Production .env checklist
ENVIRONMENT=production
API_ACCESS_KEY=<strong-key>
CORS_ALLOW_ORIGINS=https://yourdomain.com
# At least one LLM provider
OPENAI_API_KEY=sk-...
```

---

## Deployment Methods

| Method | Backend | Frontend | Difficulty |
|--------|---------|----------|------------|
| Docker Compose | Docker | Docker | Medium |
| Render (staging) | Render | Render | Easy |

---

## Docker Deployment

### Prerequisites

- Server with Docker and Docker Compose installed
- Domain name configured
- SSL certificates (recommend Traefik or Caddy)

### Step 1: Prepare Server

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com | sh

# Install Docker Compose
sudo apt install docker-compose-plugin -y

# Add user to docker group
sudo usermod -aG docker $USER

# Re-login for group changes to take effect
```

### Step 2: Clone Repository

```bash
# Clone repo
git clone https://github.com/AleksNeStu/ai-real-estate-assistant.git
cd ai-real-estate-assistant

# Create production .env
cp .env.example .env
```

### Step 3: Configure Production

Edit `.env`:

```bash
# Environment
ENVIRONMENT=production

# Security (generate strong keys)
API_ACCESS_KEY=$(openssl rand -hex 32)

# CORS (your actual domain)
CORS_ALLOW_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# LLM Provider
OPENAI_API_KEY=sk-...
# or other provider

# Optional: Redis for caching
REDIS_URL=redis://redis:6379
```

### Step 4: Start Services

```bash
# Start all services
docker compose -f deploy/compose/docker-compose.yml up -d

# View logs
docker compose -f deploy/compose/docker-compose.yml logs -f

# Check status
docker compose ps
```

### Step 5: Configure Reverse Proxy (Recommended)

Using Caddy (automatic HTTPS):

```bash
# Create Caddyfile
cat > Caddyfile << 'EOF'
yourdomain.com {
    reverse_proxy frontend:3000
}

api.yourdomain.com {
    reverse_proxy backend:8000
}
EOF

# Start Caddy
docker run -d --name caddy \
  -p 80:80 -p 443:443 \
  -v $(pwd)/Caddyfile:/etc/caddy/Caddyfile \
  -v caddy_data:/data \
  caddy:latest
```

---

## Staging Deployment

The public repository does not ship an environment-specific deployment config —
you run the Docker Compose stack on your own host (see the Caddy walkthrough above).

### Services

| Service | Purpose |
|---------|---------|
| `ai-real-estate-backend` | Backend API (FastAPI) |
| `ai-real-estate-frontend` | Frontend (Next.js) |

### Step 1: Configure the environment

```bash
cp deploy/compose/.env.example deploy/compose/.env
```

**Backend:**

| Name | Value |
|------|-------|
| `ENVIRONMENT` | `production` |
| `API_ACCESS_KEY` | Your production API key |
| `OPENAI_API_KEY` | Your OpenAI key |
| `CORS_ALLOW_ORIGINS` | Your frontend URL |

**Frontend:**

| Name | Value |
|------|-------|
| `BACKEND_API_URL` | Your backend URL |
| `API_ACCESS_KEY` | Your production API key |
| `NEXT_PUBLIC_API_URL` | `/api/v1` |

**Important:** Never use `NEXT_PUBLIC_*` for secrets.

### Step 2: Deploy

```bash
docker compose -f deploy/compose/docker-compose.yml up -d
```

### Known Limitations (constrained host)

- A 512 MB cap is not enough for a local LLM, web search, or a multi-worker backend
- The disk is ephemeral — anything user-generated is lost on the next deploy

---

## Post-Deployment

### Health Checks

```bash
# Backend health
curl https://your-backend.com/health

# Expected response
# {"status":"healthy","version":"4.0.0","timestamp":"...","uptime_seconds":...}
```

### Smoke Tests

```bash
# Test API authentication
curl -X POST https://your-frontend.com/api/v1/verify-auth \
  -H "X-API-Key: $API_KEY"

# Expected response
# {"message":"Authenticated successfully","valid":true}
```

### Performance Checks

```bash
# Response time
curl -w "@curl-format.txt" -o /dev/null -s https://your-backend.com/health

# curl-format.txt
# time_namelookup: %{time_namelookup}\n
# time_connect: %{time_connect}\n
# time_appconnect: %{time_appconnect}\n
# time_pretransfer: %{time_pretransfer}\n
# time_starttransfer: %{time_starttransfer}\n
# time_total: %{time_total}\n
```

---

## Monitoring

### Health Endpoint Monitoring

Set up monitoring to ping `/health` endpoint every minute.

Recommended services:
- UptimeRobot (free)
- Pingdom
- Better Uptime

### Log Management

For Docker:

```bash
# View logs
docker compose logs -f

# Follow specific service
docker compose logs -f backend

# Export logs
docker compose logs > deployment-logs.txt
```

For Render:

1. Go to Render Dashboard → Your Service → Logs
2. Use `render logs` CLI command

### Metrics

The backend exposes Prometheus metrics at `/metrics` when `METRICS_ENABLED=true`.

---

## Rollback Procedure

### Docker Rollback

```bash
# Stop current deployment
docker compose down

# Pull previous version
git checkout <previous-tag>

# Rebuild and start
docker compose up -d --build
```

### Render Rollback

1. Go to Render Dashboard → Your Service → Deployments
2. Find previous successful deployment
3. Click "Promote to Production"

---

## Troubleshooting

### Issue: CORS Errors

**Solution:**
1. Verify `CORS_ALLOW_ORIGINS` includes your frontend URL
2. Check `ENVIRONMENT=production` is set
3. Backend validates CORS in production mode only

### Issue: 502 Bad Gateway

**Possible causes:**
1. Backend not running
2. Wrong port in proxy config
3. Backend crashing

**Solution:**
```bash
# Check backend status
docker compose ps

# Check logs
docker compose logs backend
```

### Issue: High Memory Usage

**Solution:**
1. Add swap space
2. Configure Redis max memory
3. Set `DB_POOL_SIZE` and `DB_MAX_OVERFLOW`

### Issue: Slow Response Times

**Solution:**
1. Enable Redis caching
2. Check LLM provider latency
3. Consider using faster model (e.g., gpt-4o-mini)

### Issue: Render Cold Start 502

**Cause:** Free tier services spin down after inactivity.

**Solution:**
- Wait ~2-3 minutes after first 502, then retry
- Or use a health check ping service to keep services warm

---

## Next Steps

- Compare against other deployment options: [DEPLOYMENT_VARIANTS.md](../../DEPLOYMENT_VARIANTS.md) (Local Docker vs VPS vs Render free tier)
- Configure [CI/CD Pipeline](ci-cd.md)
- Review [Monitoring](#monitoring)
- Read [Troubleshooting Guide](troubleshooting.md)
