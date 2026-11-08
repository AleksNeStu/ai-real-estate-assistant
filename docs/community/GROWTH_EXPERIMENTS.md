# Growth Experiments and Public Metadata Record

> **What this file is.** The record of the repository's public metadata and of
> the growth experiments run against it. Every row here was read back from
> GitHub or from the live deployment — this is a measured state, not a plan.
> Drafts and the publication plan live in [`docs/marketing/`](../marketing/README.md);
> the metric definitions live in [`METRICS.md`](./METRICS.md).

## Live public metadata

Read via the GitHub REST API on 2026-11-08:

| Field | Value |
|-------|-------|
| **Description** | `Open-source AI real estate assistant: RAG + vector search over your own listings, 16 LLM providers, FastAPI + Next.js. Run it on your own server with Docker, or try the live demo.` (179 chars) |
| **Homepage** | `https://realty.kittray.com` |
| **Topics** (17) | `ai-assistant`, `artificial-intelligence`, `chatbot`, `chromadb`, `docker`, `fastapi`, `langchain`, `llm`, `nextjs`, `open-source`, `property-search`, `python`, `rag`, `real-estate`, `self-hosted`, `typescript`, `vector-search` |
| **Default branch** | `dev` |
| **Stars / Forks / Watchers** | 321 / 119 / 6 |
| **Open issues / Open PRs** | 0 / 0 |
| **Contributors** | 6 (the owner, `dependabot[bot]`, `github-actions[bot]`, and three outside contributors: `stephenalexbrowne`, `Jwrede`, `KrabbiAI`) |

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
| Indexing the demo | 2026-07-22 → now | robots.txt was flipped to index/follow for a star-attraction test; the demo now serves a Disallow-all robots.txt and `X-Robots-Tag: noindex, nofollow` | reversed — the product is not released in this state |
| Pre-launch checks on the live demo | 2026-11-08 | Tour, try-these chips, lead capture with redaction, and og:image all verified against the running deployment | passed |

## What the traffic says

Fourteen days to 2026-11-08: 706 views, 272 unique visitors, +8 stars in thirty
days — 0.27 a day.

| Referrer | Unique visitors | Reading |
|----------|-----------------|---------|
| github.com | 84 | The repository's own traffic — people who already found it |
| aocr.org | 81 | Noise: a radiology college's site, not an open-source directory |
| Google | 21 | Organic, on a demo that is deliberately `noindex` |

The first wave of TaskMaster #14 targets 10 stars a day — about 37 times the
current rate. At today's conversion that means roughly 3,700 unique visitors a
day, or a channel of a different kind (Hacker News, Product Hunt, a directory
that actually converts). The full snapshot is in
[`metrics/2026-W45.md`](./metrics/2026-W45.md).

## What is deliberately not done here

- **Publishing.** Every channel is its own confirmation-gated task and it is
  executed by the operator under their own name. The drafts, the checklists and
  the reply templates are in [`docs/marketing/`](../marketing/README.md).
- **A metrics collection workflow.** That is new code in a repository frozen for
  demo purposes, so it is not taken; the weekly snapshot is collected by hand.
- **Indexing the demo.** The product is unfinished, so the demo stays out of
  the index: the deployment sets `SEARCH_INDEXING=false` (the guard in
  `apps/web/src/lib/indexing.ts`) and mounts a Disallow-all `robots.txt` over
  the product's own file. The release step — unset `SEARCH_INDEXING`, drop the
  mount — is documented in [`SEO_INDEXING_SETUP.md`](./SEO_INDEXING_SETUP.md)
  and in the deployment notes.
