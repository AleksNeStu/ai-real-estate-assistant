# Developer Guides

This section contains comprehensive guides for developers working on the AI Real Estate Assistant project.

## Getting Started

| Guide | Description |
|-------|-------------|
| [Local Development](local-development.md) | Set up your development environment (Docker & non-Docker) |
| [Environment Setup](environment-setup.md) | Configure environment variables and LLM providers |
| [Testing Guide](testing.md) | Run tests, understand coverage requirements, and CI parity |
| [Pricing from notarial deeds](pricing-from-notarial-deeds.md) | How a place is valued against the official register of notarial prices, and what that evidence looks like |

## Deployment & Operations

| Guide | Description |
|-------|-------------|
| [Deployment Guide](deployment.md) | Deploy with Docker |
| [CI/CD Pipeline](ci-cd.md) | Understand the GitHub Actions workflow |
| [Troubleshooting](troubleshooting.md) | Common issues and solutions |

## Quick Reference

### Essential Commands

```bash
# Development
make dev              # Auto-detect Docker or local mode
make dev-api          # Backend only (localhost:8000)
make dev-web          # Frontend only (localhost:3000)

# Testing
make test             # All tests (backend + frontend)
make test-api         # Backend tests with coverage
make test-web         # Frontend tests

# Code Quality
make lint             # All linting
make format           # Format all code
make security         # All security scans
make ci               # Full CI pipeline locally

# Docker
make docker-up        # Start containers
make docker-down      # Stop containers
make docker-logs      # View logs
```

### Project Structure

```
ai-real-estate-assistant/
├── apps/
│   ├── api/           # FastAPI backend (Python 3.12+)
│   │   ├── api/       # Routers, main.py, dependencies
│   │   ├── agents/    # HybridAgent, QueryAnalyzer
│   │   ├── tools/     # LangChain tools
│   │   ├── models/    # LLM provider factory
│   │   └── tests/     # pytest (unit/, integration/)
│   └── web/           # Next.js frontend (React 19)
│       └── src/
│           ├── app/   # App Router pages
│           ├── lib/   # API client, utilities
│           └── contexts/  # Auth, Favorites
├── deploy/
│   ├── compose/       # Docker Compose files
│   └── docker/        # Dockerfiles
├── scripts/           # Utility scripts
├── docs/              # Documentation
└── Makefile           # Quick commands
```

### Key Ports

| Service | Port | Description |
|---------|------|-------------|
| Backend | 8000 | FastAPI API |
| Frontend | 3000 | Next.js Dev Server |
| Redis | 6379 | Cache/Sessions |
| Ollama | 11434 | Local LLM |
| SearXNG | 8081 | Web search (optional) |

## Contributing

Before contributing, please read:

1. [Local Development](local-development.md) - Set up your environment
2. [Testing Guide](testing.md) - Ensure tests pass
3. [Deployment Guide](deployment.md) - Understand how changes deploy

## Need Help?

- Check the [Troubleshooting](troubleshooting.md) guide for common issues
- Review existing [Architecture Documentation](../architecture/ARCHITECTURE.md)
- See [CLAUDE.md](../../CLAUDE.md) for project-specific conventions
- See [Support & Customization](../../README.md#support--customization) for sponsorship and commercial support
