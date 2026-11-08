# Project Structure

```
ai-real-estate-assistant/
├── apps/
│   ├── api/                      # FastAPI backend (Python)
│   │   ├── api/                  # Routers, middleware, app entrypoint
│   │   ├── agents/               # Query analysis + orchestration
│   │   ├── tools/                # Tool implementations (mortgage, compare, web tools)
│   │   ├── vector_store/         # ChromaDB + retrievers + reranker
│   │   ├── data/                 # Schemas + providers/adapters
│   │   ├── analytics/            # Market insights + financial metrics
│   │   ├── notifications/        # Digests, alerts, scheduling
│   │   ├── models/               # Provider factory + model implementations
│   │   ├── utils/                # Shared helpers (sanitization, exporters, caching)
│   │   └── tests/                # Backend unit/integration/e2e tests
│   └── web/                      # Next.js frontend (TypeScript)
│       ├── src/app/              # App Router pages
│       ├── src/components/       # UI components
│       └── src/lib/              # API client + shared types/utils
├── deploy/                       # Docker/Compose files
├── docs/                         # Documentation (PRD, ADRs, architecture, security)
├── scripts/                      # Dev/CI/docs/security/validation scripts
├── k8s/                          # Kubernetes manifests (optional)
└── .taskmaster/                  # Taskmaster PRD/tasks (project tracking)
```
