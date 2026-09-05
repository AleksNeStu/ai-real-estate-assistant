# GitHub Metadata Planning Record

> **Task 5 companion file.** This document records the current vs proposed public GitHub repository metadata. It is a planning record only — no mutation has been applied. Mutation is reserved for Task 8.

## Current State (read via GitHub REST API, 2026-07-21)

| Field | Current Value |
|-------|---------------|
| **Description** | `AI-powered real estate platform with conversational property search, analytics, and market insights. Built with FastAPI + Next.js + ChromaDB.` (133 chars) |
| **Homepage** | `https://realestate-web-dz1y.onrender.com/` |
| **Topics** (20) | `ai`, `assistant`, `chatbot`, `chromadb`, `conversational-ai`, `docker`, `fastapi`, `llm`, `mapbox`, `mortgage-calculator`, `multi-llm`, `nextjs`, `property-search`, `proptech`, `python`, `python3`, `rag`, `real-estate`, `typescript`, `vector-database` |

## Proposed Changes

### Description
| | Value |
|---|---|
| **Proposed** | `Open-source AI real estate search with RAG, vector search, multi-provider LLMs, FastAPI, Next.js, ChromaDB, and a live demo.` |
| **Length** | 124 chars (within 160-char GitHub limit) |

### Homepage
| | Value |
|---|---|
| **Proposed** | `https://realestate-web-dz1y.onrender.com/` |
| **Change** | None |

### Topics
| | Value |
|---|---|
| **Proposed** (13) | `artificial-intelligence`, `real-estate`, `rag`, `vector-search`, `fastapi`, `nextjs`, `chromadb`, `llm`, `chatbot`, `property-search`, `python`, `typescript`, `open-source` |

## Social Preview

| Field | Value |
|-------|-------|
| **File** | `.github/social-preview.png` |
| **Dimensions** | 1280 x 640 px |
| **Change vs previous** | Removed stale "259 GitHub Stars" card; replaced with evergreen "Hybrid RAG / RAG + Vector Search" card; other cards unchanged |
| **Footer** | MIT License / Live Demo / FastAPI · Next.js · ChromaDB |

## Constraints Respected

- No push to any remote.
- No mutation of live public GitHub settings in this task.
- No external dependencies added for image generation.
- Evergreen: no decaying star counts or dates in the PNG.

## Task 7 Verified Baseline (2026-07-21)

| Metric | Value | Source |
|--------|-------|--------|
| Stars | 284 | `gh api repos/AleksNeStu/ai-real-estate-assistant` |
| Forks | 111 | same |
| Watchers | 6 | same |
| Open issues | 10 | same |
| Captured at | 2026-07-21T11:09:18Z | read-only |

| Gate | Result |
|------|--------|
| Python tests (`unittest`) | 11/11 pass |
| Frontend targeted tests (`site.test.ts`, `structured-data.test.ts`) | 17/17 pass |
| Frontend full suite (`jest --runInBand`) | 1157 pass / 39 skipped / 0 fail |
| Frontend lint | 0 errors, 18 pre-existing warnings (unrelated to visibility diff) |
| Frontend production build | exit 0; 261 pages; `/sitemap.xml` static; all 9 locale routes including `/valuation` |
| `ai-real-estate.example.com` in tracked SEO files | none |
| Render demo live endpoints | still serve pre-Task-2 placeholders; pending deploy after push approval |
| MISSING_MESSAGE SSG warnings | pre-existing; tracked in TaskMaster #17 |

**No push, no live GitHub settings mutation, no campaign executed.** Tasks 1-5 ready for the technical PR. Task 8 (public metadata + indexing) remains confirmation-gated.

