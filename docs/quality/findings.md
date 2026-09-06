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
| F-20260905-2 | 2026-09-06 | med | closed — filter pruned by commit 0465d0c on dev | .github/workflows/ci.yml | Original `if: github.repository_owner == 'NestLab-Tech'` filter was added by commit `b6664a6 ci: adapt workflows for NestLab-Tech private repo (Task #120)` (pre-2026-09-05). Subsequently pruned by commit `0465d0c chore(repo): prune references from tracked config + CI` (post-2026-09-05, on dev branch). Current ci.yml uses branch-based gate (`github.ref in ['dev','main']`) instead of owner filter — 15 jobs run on both repos. Verify with `git show dev:.github/workflows/ci.yml | grep -E 'NestLab|repository_owner'` returns no NestLab-Tech filter. Tier 1 fix from the plan was no-op since filter already pruned; ledger closure is the actual completion. | n/a | this session followup (Tier 1, dev branch only) | 2026-09-06 |
| F-20260905-4 | 2026-09-06 | low | closed — fixed via PR #294 | apps/web/src/middleware.ts | PR #292 task #12 (93c164f feat(ci): Next.js 16 themeColor + middleware→proxy migration) created `apps/web/src/proxy.ts` but forgot to delete the old `apps/web/src/middleware.ts`. Next.js 16 detects BOTH files and fails the build: `Error: Both middleware file './src/src/middleware.ts' and proxy file './src/src/proxy.ts' are detected.` Blocked publish-ghcr.yml #34036204387 (v5.1.5 first attempt). Fix: PR #294 `fix(web): remove stale middleware.ts`. After merge, deleted + re-pushed tag as v5.1.5.1 (tag increment avoids the cached deadlocked run state from v5.1.5). publish-ghcr.yml #34046005946 succeeded for v5.1.5.1 (~18 min total). | n/a | this session `/finito` follow-up | — |
| F-20260905-5 | 2026-09-06 | low | closed — v5.1.5.1 GHCR images built + pushed | ghcr.io/AleksNeStu/ai-real-estate-assistant/{frontend,backend}:v5.1.5.1 | After PR #294 merge (commit 52fea56ef16f6bcdb407b5913d034e2c2b45c1ca), tagged v5.1.5.1 (avoiding v5.1.5 cached run state) and pushed to all 3 mirrors. publish-ghcr.yml #34046005946 ran for ~18 min: publish-backend ✅ success, publish-frontend ✅ success. Local docker buildx verification: `time docker buildx build --tag ai-real-estate-assistant-frontend:test --file deploy/docker/Dockerfile.frontend --load .` completed in 5m22s. | n/a | this session `/finito` | — |

## Doing

## Closed

## Promoted