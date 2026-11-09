# Contributing to AI Real Estate Assistant

Thank you for your interest in contributing! This guide will help you get started.

## Quick Start

1. Fork the repository
2. Clone your fork: `git clone https://github.com/<your-username>/ai-real-estate-assistant.git`
3. Run setup: `make setup` (or `make install` for dependencies only)
4. Start developing: `make dev`

## Development Environment

### Prerequisites

- Python 3.12+
- Node.js 18+
- [uv](https://docs.astral.sh/uv/) (Python package manager)

### Backend Setup

```bash
cd apps/api
uv sync                    # Install Python dependencies
cp ../../.env.example ../../.env  # Configure environment
```

### Frontend Setup

```bash
cd apps/web
npm ci                     # Install Node dependencies
cp .env.example .env.local # Configure environment
```

## Code Style

### Python (Backend)

- **Formatter**: Ruff (line-length: 100, target: Python 3.12)
- **Type hints**: Required for all function signatures
- **Imports**: Use absolute imports from project root

```bash
cd apps/api && ruff check .     # Lint
cd apps/api && ruff format .    # Format
```

### TypeScript (Frontend)

- **Linter**: ESLint
- **Formatter**: Prettier (via lint-staged)

```bash
cd apps/web && npm run lint     # Lint
```

## Testing

### Backend

```bash
cd apps/api
pytest tests/unit tests/integration --cov=. -n auto  # All tests with coverage
pytest tests/unit/test_query_analyzer.py -v          # Single file
```

### Frontend

```bash
cd apps/web
npm test               # All tests
npm run test:ci        # CI with coverage
```

## Commit Convention

Format: `type(scope): description (Task #XX)`

| Type | Use for |
|------|---------|
| `feat` | New features |
| `fix` | Bug fixes |
| `docs` | Documentation |
| `refactor` | Code restructuring |
| `test` | Test additions/changes |
| `chore` | Maintenance, CI, tooling |
| `ci` | CI/CD changes |

## Community Edition (CE) Contributions

This project offers a **Community Edition** that is open-source and welcomes contributions. Some features are reserved for paid editions (Pro, Enterprise) as noted in the MCP connector allowlist.

### CE-Compatible Contributions

Contributions are CE-compatible when they:

- Do not introduce Pro/Enterprise-only features into CE code paths
- Use edition-gated patterns (see `apps/api/mcp/config/mcp_allowlist.yaml`)
- Include tests that run without paid API keys
- Do not require proprietary data or services

### Edition Access Control

Connectors and features use an edition-based allowlist:

| Edition | Available Connectors |
|---------|---------------------|
| Community (CE) | echo_stub, google_maps, openstreetmap, web_scraper |
| Pro | + salesforce, stripe, hubspot |
| Enterprise | + slack, custom connectors |

When adding a new connector, add it to the appropriate section in `mcp/config/mcp_allowlist.yaml`.

## Developer Certificate of Origin (DCO)

By contributing to this project, you agree that you have the right to submit your contribution under the project's license. Each commit must include a `Signed-off-by` line:

```
feat(search): add polygon-based spatial filter

Signed-off-by: Your Name <your.email@example.com>
```

You can add this automatically with `git commit -s`.

By signing off, you certify that:

- The contribution was created in whole or in part by you
- You have the right to submit it under the open-source license indicated
- The contribution does not violate any third-party intellectual property rights

## Where the work lands

The maintainers' own work lands directly on `dev` — the branch that carries the
redesign of the interface. `main` is the released line, and it moves only on a
reviewed promotion: a pull request from `dev` into `main`, fast-forwarded, never
a force-push (the repository's ruleset requires linear history). Contributors
work on a branch and open a pull request against `dev` — the process below.

| | |
|---|---|
| The working branch | `dev` — the commits, the CI and the live demo are checked here |
| The released line | `main` — moved only by a reviewed promotion, fast-forwarded |
| What deploys | a `vX.Y.Z` tag: it publishes the images and rolls the server |

A release is cut from `dev`, and only after the CI on that commit is green.

## Pull Request Process

1. Create a feature branch from `dev`: `git checkout -b feature/short-description`
2. Make your changes with tests
3. Run `make lint` and `make test` to verify
4. Push and open a PR against `dev`
5. Ensure CI passes (linting, tests, security scans)

### PR Review SLA

| PR Source | Initial Review | Follow-up Review |
|-----------|---------------|-----------------|
| Community contributors | Within 48 hours | Within 24 hours |
| Maintainers | Within 24 hours | Within 12 hours |

We aim to provide actionable feedback on every community PR within 48 hours. If you haven't received a review after 48 hours, please comment on the PR to bump it.

### PR Checklist

When submitting a PR, ensure you have addressed all items in the pull request template, including:

- [ ] Code follows project style guidelines
- [ ] Self-review completed
- [ ] Tests added for new functionality
- [ ] All existing tests pass
- [ ] Documentation updated (if applicable)
- [ ] License headers added to new files (SPDX: `SPDX-License-Identifier: MIT`)
- [ ] CE compliance verified (no Pro/Enterprise features in CE code paths)
- [ ] No secrets or credentials in the diff

## Good First Issues

Looking for a place to start? Check these community-friendly issues:

- **[Community: Implement Telegram Bot MCP Connector](https://github.com/AleksNeStu/ai-real-estate-assistant/issues/16)** - Build a Telegram bot connector following the MCP pattern
- **[Community: Add Email Notification MCP Connector](https://github.com/AleksNeStu/ai-real-estate-assistant/issues/NEW)** - Implement email notifications via SMTP/sendgrid
- **[Community: Add iCal Export for Saved Searches](https://github.com/AleksNeStu/ai-real-estate-assistant/issues/NEW)** - Calendar export for property viewing schedules
- **[Community: Add CSV Export for Property Results](https://github.com/AleksNeStu/ai-real-estate-assistant/issues/NEW)** - Export search results as spreadsheet
- **[Community: Add Property Comparison Tool](https://github.com/AleksNeStu/ai-real-estate-assistant/issues/NEW)** - Side-by-side property comparison UI

Filter by [`good first issue`](https://github.com/AleksNeStu/ai-real-estate-assistant/labels/good%20first%20issue) label for more opportunities.

### Community Metrics Goals

We track community health metrics to measure project growth. See [docs/community/METRICS.md](docs/community/METRICS.md) for the full tracking framework.

| Goal | Target | Why |
|------|--------|-----|
| GitHub Stars | >= 100 | Visibility and adoption |
| External PRs Merged | >= 1 | Active community participation |
| Open Good First Issues | >= 5 | Always have onboarding opportunities |
| External Contributors | >= 3 | Diverse contributor base |

## Architecture Overview

For a detailed architecture reference, see [Developer Guide](docs/community/DEVELOPER_GUIDE.md).

```
apps/
├── api/              # FastAPI backend (Python 3.12+)
│   ├── api/          # Routers, auth, middleware
│   ├── agents/       # HybridAgent, QueryAnalyzer
│   ├── mcp/          # MCP connector framework
│   ├── tools/        # LangChain tools
│   └── tests/        # Unit, integration, e2e tests
└── web/              # Next.js App Router frontend
    └── src/
        ├── app/      # Pages and API routes
        ├── components/ # UI components
        └── lib/      # API client, utilities
```

### MCP Connector Pattern

Community connectors follow the `MCPConnector[T]` abstract base class:

1. Extend `MCPConnector` from `apps/api/mcp/base.py`
2. Implement required methods: `connect()`, `disconnect()`, `health_check()`, `execute()`
3. Register in `apps/api/mcp/registry.py`
4. Add to `apps/api/config/mcp_allowlist.yaml` under `community_edition`
5. Add tests in `apps/api/tests/unit/mcp/`

Reference implementation: `apps/api/mcp/connectors/web_scraper.py`

## Security

Please report security vulnerabilities privately. See [SECURITY.md](SECURITY.md) for our responsible disclosure process.

**Do not** report security issues through public GitHub issues.

## Code of Conduct

This project follows the [Contributor Covenant Code of Conduct](.github/CODE_OF_CONDUCT.md). By participating, you agree to uphold this code.

## Questions?

Open an issue with the `question` label and we will help you out.
