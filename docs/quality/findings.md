---
name: findings-ledger
description: Rule 279 v2 schema — quality findings ledger for ai-real-estate-assistant
metadata:
  type: project
---

# Quality Findings Ledger — ai-real-estate-assistant

Rule 279 v2 schema. Rows are written automatically by `/finish`, `/finito`, `/end`,
`/burst`, and `/prerelease`; the agent and operator triage them via `/findings-review`,
`/findings-triage`, and `/findings-promote`. Status ∈ `open` · `doing` · `postponed —
<reason>` · `blocked — <reason>` · `promoted` · `closed`. `Verified` is the date the
claim was last re-checked (`—` if never). Escape a literal `|` inside a cell as `\|`.

| ID | Date | Sev | Status | Location | Claim | Next step | Source | Verified |

## Open

| ID | Date | Sev | Status | Location | Claim | Next step | Source | Verified |
| F-20260905-1 | 2026-09-05 | med | blocked — pre-existing baseline on `main@50e98ad`, out of session scope | apps/api/tests/unit/test_port_config.py + others | 41 pre-existing unit test failures on `main@50e98ad` — 8 in `test_port_config.py` (CORS-returns-asterisk regression), 1 known parallel-flake `test_upload_jpeg_success` (F-20260903-01 pattern), 7 in `test_user_repos.py` token-repo tests, plus system-dep `test_weasyprint_not_available` and others | File health-push task; cherry-pick PR #290 already merged with zero backend Python logic changes | this session `/finito` | — |
| F-20260905-2 | 2026-09-05 | med | blocked — requires separate workflow fix in its own session | .github/workflows/ci.yml lines ~50, ~75, ~110 | `if: github.repository_owner == 'NestLab-Tech'` filter skips 15 CI jobs on `AleksNeStu/ai-real-estate-assistant` (the canonical public repo per RepoALX matrix since 2026-06-22) — backend-tests, frontend-tests, backend-lint, frontend-build, codeql-python, codeql-javascript, container-scan, lighthouse, e2e, compose-smoke, secret-validation, gitleaks all auto-skip due to owner-mismatch | Update filter to `github.repository_owner in ['AleksNeStu','NestLab-Tech']` or AleksNeStu-specific; verify by opening test PR from any feature branch | this session `/finito` (PR #290 evidence) | — |
| F-20260905-3 | 2026-09-05 | low | blocked — requires operator action via `pwsh /e/repo/repo-alex/push-all.ps1 main` | mirror1/main, mirror2/main | After PR #290 squash-merge to `AleksNeStu/main`, the mirror1 (`dev-scaler`) and mirror2 (`nest-ai-dev`) `main` branches are NOT synchronized — RepoALX pre-push cascade hook fires only on local `git push`, not on GitHub web merges | Run `pwsh /e/repo/repo-alex/push-all.ps1 main` to sync | this session `/finito` | — |

## Doing

## Closed

## Promoted