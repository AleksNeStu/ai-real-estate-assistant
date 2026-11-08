# Quickstart: Run Your AI Realtor in 5 Minutes

> **New here?** Try the **[5-Minute Quickstart →](QUICKSTART_5MIN.md)** for the fastest path to a running app.

## Prerequisites

- Docker and Docker Compose
- Create `.env` from `deploy/compose/.env.example`
- Provide BYOK: `OPENAI_API_KEY` or configure local Ollama (`OLLAMA_BASE_URL`)

## Steps

1. Copy environment:

   ```powershell
   # Windows (PowerShell)
   Copy-Item deploy/compose/.env.example deploy/compose/.env
   ```

   ```bash
   # macOS / Linux
   cp deploy/compose/.env.example deploy/compose/.env
   ```

2. Edit `deploy/compose/.env` — set your API key (e.g. `OPENAI_API_KEY=sk-...`).

3. Start services:

   ```bash
   # External AI models only (default)
   docker compose -f deploy/compose/docker-compose.yml up --build

   # Optional: with local Ollama (requires GPU)
   docker compose -f deploy/compose/docker-compose.yml --profile local-llm up --build

   # Optional: with web research (SearXNG)
   docker compose -f deploy/compose/docker-compose.yml --profile internet up --build
   ```

   Or use Makefile shortcuts:

   ```bash
   make docker-up          # External AI models
   make docker-gpu         # With GPU/Ollama
   make docker-internet    # With web search
   ```

4. Open:

   | Service | URL |
   |---------|-----|
   | Frontend | http://localhost:3082 |
   | Backend API docs | http://localhost:8082/docs |
   | Redis | redis://localhost:16379 |

5. Verify:

   ```bash
   bash scripts/docker/quickstart-verify.sh
   ```

## Local RAG

Upload PDFs/Docs in the app and query property details.

## Troubleshooting

- Ensure backend CORS allows the frontend origin.
- Check logs:

  ```bash
  docker compose -f deploy/compose/docker-compose.yml logs -f
  ```

- See [Troubleshooting Guide](TROUBLESHOOTING.md) for common issues.
