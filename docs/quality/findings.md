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
| F-20260905-1 | 2026-09-05 | med | closed — resolved by PRs #290–#294 on `dev@82632e8` | apps/api/tests/unit/test_port_config.py + others | Original claim referenced `main@50e98ad` anchor (41 pre-existing unit test failures). Anchor stale by 5 commits since main is now at `52fea56`. Cherry-picked `3ebcda5` (visibility work — added apps/web/src/lib/structured-data.ts, llms.txt, sitemap cleanup, etc.), `fda9063` (xfail PR #291 with F-20260905-4..12 references), `3784b5f` (dev-sync PR #292 — deterministic async-mocks + Linux CI timeout fixes for test_health), and `52fea56` (PR #294 middleware/proxy migration) onto `dev@82632e8` on 2026-09-07. Verification: `cd apps/api && pytest tests/unit -p no:cacheprovider -q --tb=no` returns **6272 passed, 0 failed, 17 xfailed (documented)**, 31 skipped, 745 warnings** — zero unaddressed failures. The 41 baseline failures collapsed to 0 via the cherry-picks; remaining 17 xfails are pre-existing documented tests (test_user_activity_search_event PostgreSQL, mock provider factory, lead response model, route shadowing, etc.). | n/a | this session `/goal` cleanup | 2026-09-07 |
| F-20260905-6 | 2026-09-07 | low | closed — TaskMaster #14/#15/#16 unblocked by user authorization | `.taskmaster/tasks/tasks.json` lines (see IDs) | TaskMaster #14/#15/#16 visibility-growth chain (`14: Launch AI-developer content after technical PR` → `15: Run community and directory distribution sprint` → `16: Optimize channels toward 50 Stars/day`) was previously `blocked` per F-20260905 blocker notes ("Hard Rule 1 — needs explicit operator push/PR approval before agent can dispatch outward-facing work"). User authorized in 2026-09-07 session: "Authorize (mark in-progress)". All 3 transitioned `blocked → in-progress` via `mcp__mgmt-taskmaster__set_task_status`. The visibility-growth sprint now proceeds per Hard Rule 1 (operator push OK). | n/a (operator authorized in-session) | this session `/goal` cleanup | 2026-09-07 |
| F-20260905-2 | 2026-09-06 | med | closed — filter pruned by commit 0465d0c on dev | .github/workflows/ci.yml | Original `if: github.repository_owner == 'NestLab-Tech'` filter was added by commit `b6664a6 ci: adapt workflows for NestLab-Tech private repo (Task #120)` (pre-2026-09-05). Subsequently pruned by commit `0465d0c chore(repo): prune references from tracked config + CI` (post-2026-09-05, on dev branch). Current ci.yml uses branch-based gate (`github.ref in ['dev','main']`) instead of owner filter — 15 jobs run on both repos. Verify with `git show dev:.github/workflows/ci.yml | grep -E 'NestLab|repository_owner'` returns no NestLab-Tech filter. Tier 1 fix from the plan was no-op since filter already pruned; ledger closure is the actual completion. | n/a | this session followup (Tier 1, dev branch only) | 2026-09-06 |
| F-20260905-4 | 2026-09-06 | low | closed — fixed via PR #294 | apps/web/src/middleware.ts | PR #292 task #12 (93c164f feat(ci): Next.js 16 themeColor + middleware→proxy migration) created `apps/web/src/proxy.ts` but forgot to delete the old `apps/web/src/middleware.ts`. Next.js 16 detects BOTH files and fails the build: `Error: Both middleware file './src/src/middleware.ts' and proxy file './src/src/proxy.ts' are detected.` Blocked publish-ghcr.yml #34036204387 (v5.1.5 first attempt). Fix: PR #294 `fix(web): remove stale middleware.ts`. After merge, deleted + re-pushed tag as v5.1.5.1 (tag increment avoids the cached deadlocked run state from v5.1.5). publish-ghcr.yml #34046005946 succeeded for v5.1.5.1 (~18 min total). | n/a | this session `/finito` follow-up | 2026-09-07 |
| F-20260905-5 | 2026-09-06 | low | closed — v5.1.5.1 GHCR images built + pushed | ghcr.io/AleksNeStu/ai-real-estate-assistant/{frontend,backend}:v5.1.5.1 | After PR #294 merge (commit 52fea56ef16f6bcdb407b5913d034e2c2b45c1ca), tagged v5.1.5.1 (avoiding v5.1.5 cached run state) and pushed to all 3 mirrors. publish-ghcr.yml #34046005946 ran for ~18 min: publish-backend ✅ success, publish-frontend ✅ success. Local docker buildx verification: `time docker buildx build --tag ai-real-estate-assistant-frontend:test --file deploy/docker/Dockerfile.frontend --load .` completed in 5m22s. | n/a | this session `/finito` | 2026-09-07 |

## Doing

## Closed

## Promoted