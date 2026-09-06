# 5-Minute Quickstart

Get the AI Real Estate Assistant running locally with Docker in under 5 minutes.

> **Time:** ~5 min (first run builds from source, ~3 min on subsequent starts)
> **Cost:** Free to start — use [Google Gemini free tier](https://aistudio.google.com/app/apikey) or [Ollama](https://ollama.com) (fully local, no API key needed)
> **Requirements:** Docker + 1 LLM API key (or Ollama)

---

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) (with Docker Compose v2+)
- 1 LLM API key or local Ollama — any of:

| Provider | Cost | Get Key |
|----------------|----------------|----------------|
| [Google Gemini](https://aistudio.google.com/app/apikey) | **Free tier** | API key instant |
| [OpenAI](https://platform.openai.com/api-keys) | Paid | API key instant |
| [Anthropic](https://console.anthropic.com/settings/keys) | Paid | API key instant |
| [Ollama](https://ollama.com) | **Free, local** | No key needed |

---

## Step 1 — Clone

```bash
git clone https://github.com/AleksNeStu/ai-real-estate-assistant.git
cd ai-real-estate-assistant
```

## Step 2 — Configure

```bash
# Copy the Docker Compose environment template
cp deploy/compose/.env.example deploy/compose/.env
```

Open `deploy/compose/.env` in any editor. Set **one** API key:

**Cloud LLM (pick one):**

```ini
# Uncomment and paste your key — only one is needed:
OPENAI_API_KEY=sk-your-key-here
# ANTHROPIC_API_KEY=sk-ant-your-key-here
# GOOGLE_API_KEY=AI...
```

**Local LLM (zero cost, no API key):**

```ini
# Set the provider to ollama and point to the Docker service:
DEFAULT_PROVIDER=ollama
OLLAMA_API_BASE=http://ollama:11434
```

Then start with the `local-llm` profile (see Step 3).

All other settings have sensible defaults — skip them.

## Step 3 — Start

**Option A — Pre-built images (fastest, recommended):**

```bash
docker compose -f deploy/compose/docker-compose.quick.yml up -d
```

Pulls pre-built images from GHCR — no build step needed.

**Option B — Build from source:**

```bash
docker compose -f deploy/compose/docker-compose.yml up --build -d
```

Builds images locally (~3-5 min on first run).

**Option C — With local LLM (Ollama, no API key):**

```bash
docker compose -f deploy/compose/docker-compose.yml --profile local-llm up --build -d
```

**Or use the Makefile shortcut:**

```bash
make quickstart
```

## Step 4 — Verify

Open in your browser:

| Service | URL |
|---------|-------------------------------------|
| **Frontend** | <http://localhost:3082> |
| **Backend API docs** | <http://localhost:8082/docs> |
| **Health check** | <http://localhost:8082/health> |

Run the verification script for a quick health check:

```bash
# macOS / Linux
bash scripts/docker/quickstart-verify.sh

# Windows PowerShell
.\scripts\docker\quickstart-verify.ps1
```

You should see:

```text
Backend health:   PASS
Frontend:         PASS
API auth:         PASS

All checks passed. Open http://localhost:3082 to start chatting.
```

---

## What's Next?

- Open <http://localhost:3082> and ask a question about properties
- Upload documents in the Knowledge tab for RAG-powered Q&A
- Explore the API at <http://localhost:8082/docs>

### Going Further

- [Developer setup (local without Docker)](development/QUICKSTART.md)
- [Full Docker options (Ollama, GPU, web search)](../docs/guides/local-development.md)
- [Troubleshooting](development/TROUBLESHOOTING.md)
- [Architecture overview](ARCHITECTURE.md)
- [Contributing guide](../CONTRIBUTING.md)

### Stop & Clean Up

```bash
docker compose -f deploy/compose/docker-compose.yml down
```

To remove all data (ChromaDB, Redis, volumes):

```bash
docker compose -f deploy/compose/docker-compose.yml down -v
```

---

## FAQ

**"I don't have any API keys."** Use Option C (Ollama) in Step 3 — completely free, runs locally, no cloud dependency.

**"Port 3082 is already in use."** Edit `WEB_PORT` in `deploy/compose/.env` to a free port.

**"Docker build fails."** Ensure Docker has at least 4 GB RAM allocated (Docker Desktop > Settings > Resources).
