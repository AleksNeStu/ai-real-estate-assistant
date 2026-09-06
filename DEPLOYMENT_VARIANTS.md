# Deployment Variants

This document describes the supported deployment variants of the AI Real Estate Assistant, what features are available in each, and the trade-offs you should know about before choosing one.

> **TL;DR — Local Docker and VPS deployments run the full feature set. The Render free-tier staging demo is memory-constrained (512 MB per service), so a subset of features is disabled by default.** If you want full functionality locally, use Docker Compose. If you want full functionality for real users, use a VPS.

---

## Variants at a glance

| Variant | Best for | Memory per service | All features? |
|---------|----------|--------------------|---------------|
| **Local Docker** | Contributors, evaluators, demos | 1 GB backend + 256 MB frontend (configurable) | ✅ Yes |
| **VPS / dedicated server** | Real users, custom domain | Whatever your server has (≥ 2 GB recommended) | ✅ Yes |
| **Render free tier** | Public demo link, marketing | 512 MB (Render hard cap) | ⚠️ Partial — see matrix |

A fourth option, **Kubernetes manifests** (`deploy/k8s/`), exists for orchestrating on any Kubernetes cluster. Functionally it matches a VPS deployment with more moving parts to manage.

---

## Feature availability matrix

| Feature | Local Docker | VPS | Render free | Notes |
|---------|--------------|-----|-------------|-------|
| Conversational AI (hosted LLM) | ✅ | ✅ | ✅ | Requires an API key for OpenAI / Anthropic / Google / etc. |
| Conversational AI (local Ollama) | ✅ via `--profile local-llm` | ✅ | ❌ OOMs at 512 MB | Needs 4–8 GB RAM for a useful model |
| Vector search (ChromaDB) | ✅ persistent volume | ✅ | ⚠️ in-memory only | `VECTOR_PERSIST_ENABLED=false` on Render; disk is ephemeral on free tier |
| Web search (SearXNG) | ✅ via `--profile internet` | ✅ | ❌ | `INTERNET_ENABLED=false` on Render |
| PostgreSQL | ✅ via `--profile postgres` | ✅ | ❌ SQLite only | Default in `render.yaml` |
| OAuth (Google) | ✅ | ✅ | ✅ | Requires `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` envs |
| SMTP / email | ✅ | ✅ | ✅ | Requires `SMTP_*` envs |
| Notifications scheduler | ✅ | ✅ | ✅ | Conditional on env config |
| Uptime monitor | ✅ | ✅ | ⚠️ (no scheduler on free) | Use an external monitor (UptimeRobot, Better Stack) |
| Demo mode (MockLLM) | ✅ | ✅ | ✅ | Toggleable from the UI |
| Response cache (Redis) | ✅ | ✅ | ❌ not provisioned in `render.yaml` | Backend env is set, but no Redis service runs alongside |
| Persistent sessions | ✅ via volumes | ✅ | ❌ ephemeral filesystem | Render free instances restart on deploy |
| GPU acceleration (Ollama) | ✅ via `--profile local-llm,gpu` | ✅ | ❌ | Local development only; needs NVIDIA Container Toolkit |
| Multi-worker backend | ✅ | ✅ | ⚠️ tight at 512 MB | Set `WEB_CONCURRENCY=1` on Render free |

Legend: ✅ supported · ⚠️ supported with caveats · ❌ not supported / disabled

---

## Local Docker — full functionality

The baseline deployment runs the entire stack on a single machine. Optional profiles add services (local LLM, web search, GPU, PostgreSQL) without changing the core stack.

### Core services (always on)

- **Backend** — FastAPI on host port `8082` → container `8000`
- **Frontend** — Next.js on host port `3082` → container `3000`
- **Redis** — host port `16379` → container `6379` (response cache, session storage)

### Optional profiles

| Profile flag | Adds | When to use |
|--------------|------|-------------|
| `--profile local-llm` | Ollama (CPU) | You want a local LLM and don't have a GPU |
| `--profile local-llm,gpu` | Ollama (NVIDIA GPU) | You have an NVIDIA GPU + Docker NVIDIA toolkit |
| `--profile internet` | SearXNG (web search) | You want the agent to search the web |
| `--profile postgres` | PostgreSQL 16 | You want a production-grade DB instead of SQLite |

Profiles compose with each other. For example, `docker compose ... --profile local-llm --profile internet up -d` starts Ollama and SearXNG alongside the core services.

### Quick start

```bash
# 1. Configure
cp .env.example .env
# Edit .env — at minimum set API_ACCESS_KEY and one LLM provider key

# 2. Start core services
docker compose -f deploy/compose/docker-compose.yml up -d

# 3. Open
# Frontend: http://localhost:3082
# Backend:  http://localhost:8082
# API docs: http://localhost:8082/docs
```

For **pre-built GHCR images** (no local build):

```bash
docker compose -f deploy/compose/docker-compose.quick.yml up -d
```

For a **production-style overlay** (stricter rate limits, Sentry, no seed data):

```bash
docker compose \
  -f deploy/compose/docker-compose.yml \
  -f deploy/compose/docker-compose.prod.yml \
  --profile postgres up -d
```

See [LOCAL_DEMO.md](LOCAL_DEMO.md) for the scripted demo path (auto-seeded data), and [QUICKSTART.md](QUICKSTART.md) for the three common ways to run locally.

### Why local Docker is the recommended baseline

- No memory ceiling below whatever your machine has
- No egress restrictions (SearXNG, HuggingFace, Google APIs all reachable)
- Persistent volumes for ChromaDB, sessions, audit logs, notifications
- Profiles let you turn features on or off without editing files
- The same compose files work on a VPS — only the network exposure changes

---

## VPS / dedicated server — full functionality

A VPS runs the same Docker Compose stack as local Docker, but exposed to the public internet through a reverse proxy and a real domain. There are no feature compromises relative to local Docker; the only differences are operational (HTTPS, persistent host, monitoring).

### Recommended server sizing

| Workload | vCPU | RAM | Disk |
|----------|------|-----|------|
| Hosted LLM only (OpenAI / Anthropic / Google) | 2 | 4 GB | 40 GB |
| Hosted LLM + web search (SearXNG) | 2 | 6 GB | 40 GB |
| Hosted LLM + web search + local Ollama (llama3.2:3b) | 4 | 16 GB | 60 GB |
| Hosted LLM + web search + PostgreSQL | 2 | 8 GB | 80 GB |

These are floors. Always leave 30 % RAM headroom for the OS and spikes.

### Deployment outline

1. Provision a Linux VPS (Ubuntu 22.04+ recommended)
2. Install Docker Engine + the Compose plugin
3. Clone the repository and configure `.env` for production (`ENVIRONMENT=production`, real `API_ACCESS_KEY`, real `CORS_ALLOW_ORIGINS`)
4. Put a reverse proxy in front of the frontend (Caddy, Traefik, or Nginx) for HTTPS via Let's Encrypt
5. Start the stack:

   ```bash
   docker compose \
     -f deploy/compose/docker-compose.yml \
     -f deploy/compose/docker-compose.prod.yml \
     --profile postgres up -d
   ```

6. Point your domain's DNS at the server
7. Verify: `curl https://your-domain.com/api/v1/health`

The Caddy example in [docs/guides/deployment.md](docs/guides/deployment.md) walks through the full setup. Kubernetes manifests in `deploy/k8s/` are an alternative for clusters.

### What you get

- ✅ Every feature in the matrix above
- ✅ Real domain + automatic HTTPS
- ✅ Persistent data (Postgres, ChromaDB on disk, sessions, audit logs)
- ✅ Multi-day uptime without cold starts
- ✅ Custom resource limits sized to your server

---

## Render free tier — limited functionality

The public staging demo at <https://realestate-api-wkm7.onrender.com> runs on Render's free plan. Each service is hard-capped at **512 MB RAM**, which is the dominant constraint on what can run there.

### What works

- Conversational AI with any hosted LLM provider (OpenAI, Anthropic, Google, etc.)
- Demo mode (MockLLM)
- OAuth login (if Google env vars are set)
- SMTP / email (if SMTP env vars are set)
- The full chat, search, favorites, and lead-management UI

### What is **not** available (and why)

| Feature | Status | Why |
|---------|--------|-----|
| Local LLM (Ollama) | ❌ | Would OOM at 512 MB; needs 4–8 GB for a useful model |
| Web search (SearXNG) | ❌ | `INTERNET_ENABLED=false` in `render.yaml`; saves ~1 GB for the agent process |
| Persistent ChromaDB | ⚠️ in-memory only | `VECTOR_PERSIST_ENABLED=false`; Render free tier has ephemeral disk |
| Redis cache | ❌ | Not provisioned in `render.yaml`; backend is configured for Redis but no service runs alongside |
| PostgreSQL | ❌ | SQLite only on free tier; ephemeral disk |
| Uptime monitor worker | ❌ | Use an external monitor (UptimeRobot, Better Stack, Render's own) |
| GPU acceleration | ❌ | Render free has no GPU instances |
| Multi-worker backend | ⚠️ tight at 512 MB | Set `WEB_CONCURRENCY=1` to avoid OOM |

### Free-tier memory configuration (diploma demo mode)

The `render.yaml` at the repo root already pins the env vars below so the service can boot and stay under 512 MB. This is the "diploma demo" recipe — the app runs, the demo flows work, but a lot of optional features are intentionally turned off.

| Env var | Value | Why |
|---------|-------|-----|
| `DEMO_MODE` | `true` | Use `MockLLM` instead of real provider calls. **No external LLM API needed for the demo flow.** |
| `INTERNET_ENABLED` | `false` | Don't start SearXNG. Saves the agent process ~1 GB it would otherwise need for the search worker. |
| `SEED_ON_STARTUP` | `true` | Populate demo data on first boot so the chat and search UIs have something to show. |
| `VECTOR_PERSIST_ENABLED` | `false` | ChromaDB stays in-memory; no disk writes. |
| `WEB_CONCURRENCY` | `1` | **Single uvicorn worker.** Default would spawn 2+, each duplicating the FastAPI + LangChain + ONNX runtime heap (~400 MB / worker). 2 workers OOMs immediately at 512 MB. |
| `UPTIME_MONITOR_ENABLED` | `false` | Don't start the in-process uptime monitor worker. Use an external service (UptimeRobot, Better Stack) for actual monitoring. |
| `ENABLE_NOTIFICATIONS` | `false` | Don't start the notifications scheduler — another background worker that holds heap resident. |
| `DB_POOL_SIZE` | `3` | Smaller SQLAlchemy pool (default 10) — each connection holds memory. |
| `DB_MAX_OVERFLOW` | `3` | Match the smaller pool ceiling. |
| `CHROMA_INDEXING_WORKERS` | `1` | Single-threaded ChromaDB indexing. |
| `POOL_MAX_WORKERS` | `2` | Smaller global thread pool. |
| `CACHE_ENABLED` | `false` | Don't try to initialize the response cache (no Redis sidecar exists on the free plan). |

**Net effect of the knobs above:** the backend boots in ~250–350 MB of RSS (vs. ~600–800 MB with defaults), which fits under the 512 MB cap with ~150–250 MB of headroom for request bursts. The frontend is a Next.js standalone build (~150 MB RSS) and fits well within the same plan.

**Trade-off:** in this mode, the demo can't answer questions that need real LLM reasoning, real embeddings, or real web search. The UI works end-to-end (chat, search, favorites, leads) but the LLM replies are scripted (MockLLM). For a diploma demo, that's usually fine — the goal is to show the architecture and UX, not the model quality.

### How to deploy to Render

See [docs/deployment/DEPLOYMENT.md](docs/deployment/DEPLOYMENT.md) for step-by-step instructions. The `render.yaml` at the repository root is the source of truth for the staging service config.

### When Render free is the right choice

- You want a public URL that anyone can hit without setting up Docker
- Marketing screenshots, link sharing, a "look, it works" demo
- A cheap staging environment to verify a PR end-to-end
- A **diploma / coursework demo** — the configured knobs (DEMO_MODE, no Ollama, no SearXNG, single worker) keep the service under 512 MB so the full UI is reachable end-to-end without paying for a Render plan. The trade-off is that the LLM replies are scripted (MockLLM), not real. See "Free-tier memory configuration" below.

### When Render free is the wrong choice

- Real users with real traffic (cold starts + 512 MB cap are not production-ready)
- You need vector search, web search, or a local LLM
- You need a persistent database (anything user-generated will be lost on the next deploy)

For those workloads, use a VPS.

---

## Choosing the right variant

| Your goal | Use this |
|-----------|----------|
| Try the app quickly without setting up anything | Render free (click the demo link) |
| Try the app locally with no build step | `docker-compose.quick.yml` |
| Develop or evaluate locally with full features | `docker-compose.yml` (with optional profiles) |
| Develop locally with GPU-accelerated Ollama | `docker-compose.yml` + `--profile local-llm,gpu` |
| Host for real users on your own infrastructure | VPS with `docker-compose.yml` + `docker-compose.prod.yml` overlay |
| Host on a Kubernetes cluster | `deploy/k8s/` manifests |
| Public staging link for a PR / demo | Render free (acknowledge feature limits) |

If you are unsure, start with `docker-compose.quick.yml` locally — it pulls pre-built images, takes about a minute, and gives you the full feature set without any compilation.

---

## Related docs

- [QUICKSTART.md](QUICKSTART.md) — three ways to run the app
- [LOCAL_DEMO.md](LOCAL_DEMO.md) — local demo scripts (auto-seeded data)
- [DOCKER_NAMING.md](DOCKER_NAMING.md) — container naming convention
- [docs/deployment/DEPLOYMENT.md](docs/deployment/DEPLOYMENT.md) — main deployment guide (Render focus)
- [docs/guides/deployment.md](docs/guides/deployment.md) — Docker + Caddy VPS guide
- [docs/guides/local-development.md](docs/guides/local-development.md) — local dev workflow
- [docs/guides/troubleshooting.md](docs/guides/troubleshooting.md) — common issues
- [render.yaml](render.yaml) — Render service config (source of truth for staging)
- [deploy/compose/docker-compose.yml](deploy/compose/docker-compose.yml) — local / VPS compose baseline
- [deploy/compose/docker-compose.quick.yml](deploy/compose/docker-compose.quick.yml) — pre-built-image variant
- [deploy/compose/docker-compose.prod.yml](deploy/compose/docker-compose.prod.yml) — production overlay
- [deploy/compose/docker-compose.gpu.yml](deploy/compose/docker-compose.gpu.yml) — GPU overlay (local dev only)
- [deploy/k8s/](deploy/k8s/) — Kubernetes manifests
