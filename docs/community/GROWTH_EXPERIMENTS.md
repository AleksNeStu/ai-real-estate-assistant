# Growth Experiments and Public Metadata Record

> **What this file is.** The record of the repository's public metadata and of
> the growth experiments run against it. Every row here was read back from
> GitHub or from the live deployment — this is a measured state, not a plan.
> Drafts and the publication plan live in [`docs/marketing/`](../marketing/README.md);
> the metric definitions live in [`METRICS.md`](./METRICS.md).

## Live public metadata

Read via the GitHub REST API on 2026-11-20:

| Field | Value |
|-------|-------|
| **Description** | `Open-source AI real estate assistant: RAG + vector search over your own listings, 16 LLM providers, FastAPI + Next.js. Run it on your own server with Docker, or try the live demo.` (179 chars) |
| **Homepage** | `https://realty.kittray.com` |
| **Topics** (17) | `ai-assistant`, `artificial-intelligence`, `chatbot`, `chromadb`, `docker`, `fastapi`, `langchain`, `llm`, `nextjs`, `open-source`, `property-search`, `python`, `rag`, `real-estate`, `self-hosted`, `typescript`, `vector-search` |
| **Default branch** | `dev` |
| **Stars / Forks / Watchers** | 325 / 117 / 6 |
| **Open issues / Open PRs** | 0 / 5 (Dependabot) |
| **Contributors** | 6 (the owner, `dependabot[bot]`, `github-actions[bot]`, `dev-scaler`, and two outside contributors: `stephenalexbrowne`, `Jwrede`) |

## How the metadata got here

| Date | Change | Source of the record |
|------|--------|----------------------|
| 2026-07-21 | Read back 20 topics and a 133-char description; proposed a 13-topic shortlist and a 124-char description | `.superpowers/sdd/progress.md` (Task 5) |
| 2026-07-21 | The 13-topic shortlist and the 124-char description were applied to the public repository | `.superpowers/sdd/progress.md` (Task 8) |
| 2026-07-21 | The social preview card was regenerated from its SVG source, with the decaying star count removed | `.superpowers/sdd/progress.md` (Task 5) |
| 2026-07-21 | A second card variant was added next to the live one | `.superpowers/sdd/progress.md` (Task 8) |
| 2026-11-08 | Read back for this record: 17 topics, a 179-char description naming the 16 providers, the vector search and the Docker path | GitHub REST API |

The current description says what a visitor can verify in the README — the
provider count, the retrieval stack and the two ways to run it — and nothing
that decays.

## Social preview

| File | Role |
|------|------|
| `.github/social-preview.svg` | Source of the live card |
| `.github/social-preview.png` | **The live card** — 1280×640, the canvas GitHub reads |
| `.github/social-preview-v2.svg` / `.png` | A wording variant, kept as a source; not published (it still carries the draft `v2` chip) |

The PNG is generated from the SVG by `.runtime/render.mjs` (sharp), so a wording
change is an edit to the SVG and a re-render — never a hand-painted PNG.

### What the card claims, and what backs it up (checked 2026-11-08)

| On the card | Evidence |
|-------------|----------|
| HYBRID RAG — RAG + VECTOR SEARCH | `agents/hybrid_agent.py` — retrieval plus the ChromaDB vector store |
| 8,000+ TESTS | 7,033 backend tests collected by pytest, 1,309 frontend Jest tests, 182 Playwright end-to-end tests |
| 80%+ coverage | Backend 85.10% — the union of the unit and integration coverage artifacts of CI run 42502491594; frontend 85.18% of lines |
| 9 LANGUAGES | `en`, `pl`, `ru`, `de`, `es`, `it`, `pt`, `tr`, `uk` |
| WCAG 2.1 — AA audited | `ACCESSIBILITY.md` (audit of 2026-05-09: 69 fixes across 15 components, 3 documented map-component limitations), `jest-axe` suites under `apps/web/src/components/ui/__tests__/`, Lighthouse accessibility 92 on the live demo |
| MIT License · Live Demo · FastAPI · Next.js · ChromaDB | `LICENSE`, the demo URL, the stack |

Two of those claims were corrected on 2026-11-08: the card used to read
**"90%+ backend coverage"** (the real figure is 85.10%) and **"AA compliant"**
(the audit itself documents three components where full compliance needs an
architectural change). Both now say what is true.

## Growth experiment ledger

| Experiment | Window | Outcome | Verdict |
|------------|--------|---------|---------|
| Public metadata (description, homepage, topics) | 2026-07-21 → now | Applied and read back; the repository front page shows the 179-char description, 17 topics and the demo link | keep |
| Evergreen social preview (no star count on the card) | 2026-07-21 → now | The card carries no decaying number; the star count was replaced by test and coverage figures, which grow | keep — re-check the numbers at each release |
| Hosted star-history chart | 2026-07 → 2026-08-15 | Removed: the PAT lacked the `Starring: Read` scope, and the workflow's orphan-branch pattern destroyed its own history | stopped — the README carries no star-history chart |
| Weekly metrics workflow | 2026-08-15 → now | Removed together with star-history; the weekly snapshot is collected by hand and committed | manual — see [`METRICS.md`](./METRICS.md) |
| Indexing the demo | 2026-07-22 → 2026-11-16 | robots.txt was flipped to index/follow for a star-attraction test, then reversed (the demo served a Disallow-all robots.txt and `X-Robots-Tag: noindex, nofollow`). On 2026-11-16 the operator lifted it for good: the product is the open-source funnel, and a demo no search engine can find is a demo nobody arrives at | done — the demo is indexable on its canonical host `realty.kittray.com`; the first impressions arrived on 2026-11-17 (1 on the 17th, 1 on the 18th, positions 4–5, 0 clicks), with both sitemaps submitted and no errors |
| Pre-launch checks on the live demo | 2026-11-08 | Tour, try-these chips, lead capture with redaction, and og:image all verified against the running deployment | passed |
| Dependency auto-merge | 2026-06 → 2026-11-11 | The workflow never merged anything, for two reasons: it waited 60 s for the PR's CI checks to appear and gave up before they existed, and it ran on `pull_request_target` while the merge action reads the bump's type only on `pull_request` — so the update type arrived empty and the action refused with "Semver bump '' is invalid!". Both fixed on 2026-11-11; eight bumps merged the same day | fixed — a safety net, not a silent failure |

## What the traffic says

Fourteen days to 2026-11-20: 733 views, 185 unique visitors, +7 stars in thirty
days — 0.23 a day.

| Referrer | Unique visitors | Reading |
|----------|-----------------|---------|
| github.com | 73 | The repository's own traffic — people who already found it |
| aocr.org | 81 | Noise: a radiology college's site, not an open-source directory |
| Google | 22 | Organic, measured when the demo was still `noindex` |

This split is the last one measured (W46): the traffic API returned an empty
referrer list for the W48 window, so no newer split exists.

The first wave of TaskMaster #14 targets 10 stars a day — about 43 times the
current rate. At today's conversion that means roughly 3,700 unique visitors a
day, or a channel of a different kind (Hacker News, Product Hunt, a directory
that actually converts). The full snapshot is in
[`metrics/2026-W48.md`](./metrics/2026-W48.md).

## What the stars and forks are doing

**The star count has never fallen.** Read from the stargazer timestamps, the
whole history is 325 stars, and the newest is dated the day before this
collection. June 2026 carried 73 of them in one month — more than the five
months before it combined — and what followed was not decline but the return
to the ordinary rate: 18, 20, 7, 8, 6 a month. The four stars of the last
seven days are the best fortnight since July.

**Forks are clones, not contributions.** The counter says 117, the network list
returns 122, and every one of them has 0 stars and 0 forks of its own. Two were
created in the last 30 days and two were deleted in the last five. The number
that says whether somebody took the work further is the contributor count, and
that stands at 6 — the owner, two bots, the mirror account, and two outside
contributors.

**The index has only just started.** The demo has been indexable since
2026-11-16; the property carries no search data before 2026-11-11, and the demo
was `noindex` until the 16th. The site has produced its first impressions ever
— one on the 17th, one on the 18th, positions 4 and 5, no clicks yet. Both
sitemaps are submitted without errors and the product's own sitemap lists 261
URLs. Two days of impressions is the start of a channel, not a result.

## What is deliberately not done here

- **Publishing.** Every channel is its own confirmation-gated task and it is
  executed by the operator under their own name. The drafts, the checklists and
  the reply templates are in [`docs/marketing/`](../marketing/README.md).
- **A metrics collection workflow.** That is new code in a repository frozen for
  demo purposes, so it is not taken; the weekly snapshot is collected by hand.
- **Indexing the demo.** Done, on 2026-11-16: the deployment no longer sets
  `SEARCH_INDEXING=false` (the guard in `apps/web/src/lib/indexing.ts`) and no
  longer mounts a Disallow-all `robots.txt` over the product's own file, so
  the pages are indexable and a crawler reads the product's own robots.txt —
  the one that explicitly invites the AI crawlers. The canonical host is
  `realty.kittray.com`; the apex `kittray.com` carries the index of the
  domain. The procedure, and the one-command undo, are in
  [`SEO_INDEXING_SETUP.md`](./SEO_INDEXING_SETUP.md) and in the deployment
  notes.
