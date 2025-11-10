# Trae Project Rules — AI Real Estate Assistant

Version: 1.0.0
Effective date: 2025-11-10
Document owner: Maintainers
Applies to: All contributors, maintainers, analysts, viewers, and automation/CI for this repository

---

## Purpose and Scope
These Trae Project Rules establish clear standards for code organization, development workflows, quality assurance, documentation, deployment, enforcement, and change control for the AI Real Estate Assistant. They are tailored to the current repository structure and toolchain, and are intended to ensure reliability, security, and maintainability.

This document complements and aligns with the "AI Real Estate Assistant User Rules" and does not supersede its security, compliance, and enforcement provisions. All contributors must comply with both documents.

---

## Repository Overview (Context)
The project is a Python-based application with a Streamlit UI and supporting analytics, agents, and model providers. Key directories:

- `agents/`: Query analysis, hybrid agent orchestration, recommendation logic.
- `ai/`: Agent abstractions and orchestration.
- `analytics/`: Market insights and session tracking.
- `ui/`: Visualization and dashboards (Streamlit components).
- `models/providers/`: Integrations with LLM providers (anthropic, openai, grok, google, deepseek, ollama, base).
- `vector_store/`: Chroma/hybrid retrieval and reranking utilities.
- `data/`: CSV loader and data schemas.
- `tools/`: Property tools accessible to the app/agents.
- `utils/`: App utilities, exporters, saved searches, docker/dev container helpers.
- `docs/`: Project docs, PRD, testing and deployment guides.
- `tests/`: Unit and integration tests; visual testing helpers.
- `app_modern.py`, `streaming.py`: Entrypoints/runtime scripts.
- `Dockerfile`, `docker-compose.yml`, `.devcontainer/`, `.env.example`: Deployment and environment configuration artifacts.

---

## 1) Code Organization Standards

### 1.1 Directory Structure Conventions
- Group code by domain and responsibility:
  - Core app/agents: `agents/`, `ai/`
  - Data access and schemas: `data/`
  - Models and providers: `models/`, `models/providers/`
  - Retrieval/ranking: `vector_store/`
  - UI and visualization: `ui/`, `assets/`
  - Analytics/metrics: `analytics/`, `ui/metrics.py`
  - Notifications: `notifications/`
  - Shared utilities: `utils/`, `common/`, `config/`
  - Tests: `tests/unit/`, `tests/integration/`, `tests/e2e/` (add when applicable)
  - Documentation: `docs/`

- Each top-level package must include `__init__.py` and clear module boundaries.
- Avoid deep nesting beyond 3 levels unless justified by complexity.
- Place scripts that launch the app in the project root (e.g., `app_modern.py`, `streaming.py`).

### 1.2 File Naming Patterns
- Python modules: `snake_case.py` (e.g., `query_analyzer.py`, `market_insights.py`).
- Classes: `PascalCase` (e.g., `RecommendationEngine`).
- Constants: `UPPER_SNAKE_CASE`.
- Tests: `test_<module>.py` within the appropriate testing tier directory.
- Configuration: `settings.py`, `cfg.py`; environment samples in `.env.example`.
- Scripts: `run_*.sh` for shell helpers; use descriptive names.
- Assets: Group by type under `assets/css/`, `assets/js/`, `assets/` for images.

### 1.3 Module Organization Principles
- Prefer absolute imports within packages (e.g., `from agents.query_analyzer import QueryAnalyzer`).
- Keep modules focused on a single responsibility; refactor if a module exceeds ~400–600 LOC or mixes unrelated concerns.
- Public interfaces: export via package `__init__.py` for commonly used classes/functions.
- Cross-package interactions go through well-defined interfaces (e.g., `models/providers` used by `agents` via provider factory).
- Avoid tight coupling to specific providers; use `models/provider_factory.py` abstractions.
- Data schemas go in `data/schemas.py`; loaders in `data/csv_loader.py`.
- UI visualization logic remains in `ui/` and should not import agents directly; interact via service layer functions if needed.

Example of recommended import layering:
```
ui -> agents -> models/providers -> vector_store -> data
       ^            ^                 ^             ^
    analytics     notifications     utils        config/common
```

---

## 2) Development Workflow Requirements

### 2.1 Branch Naming Conventions
- Use lowercase, hyphen-separated descriptions; include scope when helpful.
- Allowed prefixes:
  - `feature/<short-description>`
  - `fix/<short-description>`
  - `docs/<short-description>`
  - `chore/<short-description>` (e.g., dependencies, CI, tooling)
  - `refactor/<short-description>`
  - `perf/<short-description>`

Examples:
- `feature/recommendation-reranker`
- `fix/notification-email-encoding`
- `docs/deployment-guide-updates`

### 2.2 Commit Message Guidelines (Conventional Commits)
- Format: `type(scope): summary\n\nbody\n\nfooter`
- Types: `feat`, `fix`, `docs`, `chore`, `refactor`, `perf`, `test`, `build`, `ci`.
- Scope: directory or module (e.g., `agents`, `ui`, `models/providers`).
- Include issue references where applicable (e.g., `(#123)`).

Examples:
```
feat(agents): add hybrid reranker to recommendation engine (#241)

fix(ui): address dark mode flicker on initial load

docs(deployment): clarify docker-compose env overrides
```

### 2.3 Code Review Process
- All non-trivial changes require at least one Maintainer or designated Reviewer approval.
- PR checklist must include:
  - Tests added/updated; all tests pass.
  - Linting, type-checking, and static analysis pass.
  - No secrets added; `.env` files are not committed.
  - Docs updated (`docs/` and inline docstrings) if behavior changes.
  - Performance considerations addressed for hot paths (agents, vector_store, ui rendering).
- Prefer small, focused PRs; if large, provide clear rationale and design overview.

### 2.4 Merge Request Procedures
- Target branch: `main`.
- Use squash merges unless an exception is approved by Maintainers.
- Required checks must be green: unit/integration tests, lint/type/static analysis, security scans.
- Resolve conflicts before requesting merge; avoid merging with red or flaky checks.
- For breaking changes, add migration notes in PR description and `docs/`.

---

## 3) Quality Assurance Standards

### 3.1 Testing Requirements
- Tiers:
  - Unit tests: `tests/unit/` — isolated functions/classes with mocks; required for all new code.
  - Integration tests: `tests/integration/` — modules working together (e.g., agents + providers stubs); required for new features and cross-module changes.
  - E2E tests: `tests/e2e/` — application-level flows (e.g., Streamlit interactions via playwright/selenium or API if introduced). Add when UI automation is in scope.
  - Visual tests: `tests/visual/` — regression checks for charts/dashboards (optional gate, informative only).

- Naming: `test_<module_or_behavior>.py` with descriptive test names.
- Fixture data must be sanitized and non-PII; use synthetic datasets for testing. Do not load restricted data in test runs.

### 3.2 Code Coverage Thresholds
- Global thresholds (gated in CI):
  - Unit tests: ≥ 85% line coverage.
  - Integration tests: ≥ 70% line coverage.
  - Critical modules (agents, models/providers, vector_store): ≥ 90% line coverage.
- PRs that reduce coverage beyond 1% must include justification and approval.

### 3.3 Linting Configurations
- Formatting: Black (line length 100), isort (compat with Black).
- Linting: Ruff for fast lint checks (enable common rules: F, E, W, N, C90; ban unused imports, ambiguous variables).
- Type checking: mypy in `strict` mode for `agents/`, `models/`, `vector_store/`, `data/`, `analytics/`.
- Security: Bandit for Python security checks.
- Secrets: Gitleaks in CI to detect secret leaks.

Recommended pre-commit hooks:
```
black
isort
ruff
mypy --strict (subset packages)
bandit -r .
```

### 3.4 Static Analysis Rules
- Enforce no wildcard imports; explicit imports only.
- Disallow `print` in library code (use logging); mask sensitive fields in logs.
- No network calls in unit tests; use provider stubs/mocks.
- Validate environment variables via `utils/api_key_validator.py` or equivalent before runtime operations.
- Ensure `config/settings.py` defaults are safe; no hardcoded secrets.

---

## 4) Documentation Specifications

### 4.1 API Documentation Standards
- Use Python docstrings (Google or NumPy style) for all public functions/classes.
- Document parameters, return types, exceptions, and side effects.
- Generate developer documentation via MkDocs or pdoc, published from `docs/`.

Docstring example (Google style):
```
class RecommendationEngine:
    """Reranks properties based on user preferences and market data.

    Args:
        retriever: Hybrid retriever instance.
        providers: ProviderFactory for model access.

    Returns:
        Ranked list of property recommendations.

    Raises:
        ValueError: If input preferences are invalid.
    """
```

### 4.2 In-code Commenting Requirements
- Comment complex algorithms and non-obvious decisions.
- Use `TODO(#issue-id):` for follow-ups; link to issues/PRs.
- Keep comments up to date with code changes; delete obsolete comments.

### 4.3 Project Documentation Structure
- `docs/PRD.MD`: Product requirements (keep updated for scope changes).
- `docs/TESTING_GUIDE.md`: Testing practices and how to run tests locally/CI.
- `docs/DEPLOYMENT.md` and `docs/DOCKER.md`: Build/deploy instructions; environment handling.
- Add `docs/ARCHITECTURE.md`: High-level system overview (agents, providers, vector store, UI).
- Add `docs/SECURITY.md`: Secret management, data handling classifications, and incident procedures (mirror User Rules section 3).
- Release notes: `docs/RELEASE_NOTES.md` per version.

---

## 5) Deployment Guidelines

### 5.1 Environment Configurations
- Manage secrets via environment variables and secret managers; never commit secrets.
- Use `.env.example` for documenting required variables; do not commit `.env`.
- Environments: `dev`, `staging`, `prod` with separate configurations.
- TLS 1.2+ for data in transit; encrypt backups/archives that contain confidential or restricted data.

### 5.2 Build Processes
- Prefer Docker builds using the provided `Dockerfile` and `docker-compose.yml`.
- CI should: lint, type-check, test, build image, run security scans (Safety for dependencies, Trivy for images if available).
- Keep dependencies pinned and updated; address critical vulnerabilities within 7 days, high within 14 days.

### 5.3 Release Procedures
- Semantic Versioning: MAJOR.MINOR.PATCH.
- Tag releases in VCS and publish container images with matching tags.
- Generate release notes summarizing changes, risks, migrations.
- Require Maintainer approval for `prod` releases; `staging` may be automated after green CI.

### 5.4 Rollback Protocols
- Roll back by deploying the prior known-good tag/image.
- Revert DB/schema changes with counterpart down migrations if applicable.
- Use feature flags/toggles to disable new functionality rapidly.
- Document rollback execution and postmortem in `docs/RELEASE_NOTES.md`.

---

## 6) Enforcement Mechanisms
- CI gates: PRs must pass tests, coverage thresholds, linting/type/static analysis, and security scans.
- CODEOWNERS: Enforce review from domain owners for sensitive areas (providers, vector_store, agents, analytics).
- Logs: Do not print secrets or PII; redact sensitive fields.
- Access: Follow least privilege; role changes require Maintainer approval.
- Violations: Consequences follow the User Rules Enforcement Policy (warnings, restrictions, suspension, termination).

---

## 7) Change Control and Versioning for This Document
- Storage: `.trae/rules/project_rules.md` in the repository.
- Versioning: Semantic Versioning (MAJOR.MINOR.PATCH) with effective date.
- Change Process: Propose updates via PR; require Maintainer approval and green checks.
- Review Cadence: At least quarterly or after major architectural changes.
- Change Log: Maintain below.

### Change Log
- 1.0.0 (2025-11-10)
  - Initial version aligned with current repository structure and User Rules.

---

## 8) Practical Examples and Checklists

### 8.1 PR Checklist (copy into PR description)
- [ ] Unit tests added/updated and pass
- [ ] Integration tests added/updated as needed
- [ ] Coverage meets thresholds (unit ≥85%, integration ≥70%, critical modules ≥90%)
- [ ] Linting (Black/isort/Ruff), type checking (mypy), static analysis (Bandit) pass
- [ ] No secrets added; environment variables documented in `.env.example`
- [ ] Docs updated (docstrings, `docs/`)
- [ ] Performance considerations addressed
- [ ] Reviewer assigned per CODEOWNERS

### 8.2 Commit Examples
```
feat(vector_store): implement hybrid retriever batch scoring (#355)
fix(notifications): correct SMTP TLS setting and mask credentials
refactor(ui): extract radar chart color mapping into utils
```

### 8.3 Module Template
```
# my_module.py
"""Short summary of module purpose.

Functions:
    foo: Does X.
Classes:
    Bar: Represents Y.
"""

from __future__ import annotations
from typing import List

class Bar:
    """Example class.

    Args:
        name: Identifier.
    """

    def __init__(self, name: str) -> None:
        self.name = name
```

---

## 9) Alignment Notes
- These rules are designed to operate alongside the "AI Real Estate Assistant User Rules". Where conflicts arise, security and compliance requirements from the User Rules take precedence.
- Secret management, data handling classifications, and incident reporting must follow Section 3 of the User Rules.

---

## 10) Contacts and Ownership
- Maintainers: Responsible for approvals, reviews, and enforcement.
- Contributors: Responsible for adhering to these rules and updating docs/tests.
- Automation/CI: Restricted to necessary scopes for builds, tests, deployments, and scans.

---

## 11) External AI Tools and Providers Policy

### 11.1 Supported Providers (current)
- OpenAI, Anthropic (Claude), Google (Gemini), Grok, DeepSeek, Ollama.
- Anthropic integration uses `ANTHROPIC_API_KEY` and is implemented under `models/providers/anthropic.py`.

### 11.2 Adding a New Provider or Tool
Before proposing integration of an external AI tool/provider (e.g., new vendor SDKs or compilers):
- Prepare an RFC in `docs/RFC/<provider_or_tool>.md` that includes:
  - Purpose, scope, benefits, and risks.
  - Licensing and terms of use; confirm compatibility with the project LICENSE.
  - Security review: secret management plan, data handling, and privacy considerations.
  - Operational implications (quotas, costs, rate limits).
  - Rollout plan (feature flags, opt-in, telemetry if applicable).
- Implementation checklist:
  - Create provider module under `models/providers/<name>.py` (follow `base.py` abstractions).
  - Update `models/provider_factory.py` to register the provider.
  - Add environment variable(s) to `.env.example` and `.streamlit/secrets.toml.example` (no real secrets).
  - Extend `config/settings.py` to read env vars and expose config.
  - Add unit tests (≥85% coverage) and integration tests as needed (≥70% coverage).
  - Ensure lint/type/static/security checks pass (Black/isort/Ruff/mypy/Bandit/Gitleaks).
  - Update `README.md` and `docs/DEPLOYMENT.md` with setup instructions.
  - Add CODEOWNERS entries if a dedicated reviewer/owner is needed.

### 11.3 Experimental Tools and Private Prototypes
- Keep early experiments private (sandbox repo or private branch) until:
  - CI gates are green and coverage thresholds are met.
  - Licensing/security reviews are completed.
  - Documentation and RFC are ready for review.
- Use feature flags or config guards to prevent breaking changes in `main`.

### 11.4 Secrets and Compliance
- Never commit secrets; use environment variables or secret managers.
- Validate keys using `utils/api_key_validator.py` when applicable.
- Follow data handling classifications from the User Rules; do not transmit PII to external providers without explicit approval.