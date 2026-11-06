# Show HN — Draft

> **Status:** Draft. Operator (AleksNeStu) to publish manually per Rule 1
> (no push / no publish from agent identity).
> **Tag length:** title ≤ 80 chars; body ~250-400 words.

---

## Title (≤ 80 chars)

**Show HN: AI Real Estate Assistant — conversational property search (FastAPI + Next.js 16, MIT)**

Alternatives:
- "Show HN: An open-source AI property search with multi-provider LLM fallback"
- "Show HN: I built an AI real estate assistant because Zillow doesn't speak natural language"

## Body

Hi HN,

I built **AI Real Estate Assistant** — an open-source conversational AI
platform for property search, analytics, and market insights. You ask in
natural language ("2-bedroom apartment in Kraków under 500k"), and the
platform extracts filters, runs hybrid semantic + keyword retrieval over
ChromaDB, and returns matched listings.

The codebase is FastAPI + Next.js 16 + ChromaDB with MMR reranking. It
plugs into six LLM providers (OpenAI, Anthropic, Google, Grok, DeepSeek,
local Ollama) with an automatic fallback chain so a single provider
rate-limit doesn't kill the demo. Per-task and per-user provider
selection lives in `apps/api/models/provider_factory.py`.

What works today:
- Conversational search with automatic filter extraction
- Financial tools: mortgage calculator, rent-vs-buy, ROI, TCO, CMA reports
- AI property valuation with multi-year price forecast (1/3/5/10y)
- AI neighborhood one-liner on property detail pages
- Interactive maps with clustered markers (Mapbox / Leaflet)
- 9 languages (English, Polish, Russian, German, Spanish, Italian,
  Portuguese, Turkish, Ukrainian) with EU AI Act compliance labels

Why I built it: I'm not trying to replace Zillow or Idealista. They're
aggregators with live MLS feeds and millions of users — I'm a solo
developer. What I wanted was a developer-friendly reference stack for
AI-first property UX, open-core, self-hostable, MIT-licensed, that
someone could fork on a Friday and ship a custom property experience on
Monday. The hosted SaaS tier (PropVector AI, propvectorai.com) covers
live data feeds, accounts, and AI CRM for when you outgrow the demo.

Stack: FastAPI · Next.js 16 · React 19 · ChromaDB · PostgreSQL · Docker ·
GitHub Actions · Render · Uptime Kuma.

Live demo (no signup): https://realestate-web-dz1y.onrender.com/
Source: https://github.com/AleksNeStu/ai-real-estate-assistant

Happy to answer questions about the RAG pipeline, multi-provider
fallback, ChromaDB tuning, or anything else.

---

## First comment (operator to post immediately after submission)

Thanks for the questions — happy to dig into anything.

Quick answers to the inevitable ones:

- **Why not just use Zillow API?** No Zillow API for end developers
  anymore (they killed the public API years ago). This is built for
  developers who want a self-hostable stack, not end-users browsing real
  listings. PropVector AI (propvectorai.com) is the hosted tier that
  bridges to live feeds.

- **Multi-provider LLM routing isn't just a config flag — why bother?**
  Reliability. When one provider rate-limits or has an outage, the demo
  keeps working. Per-task priority (chat → property valuation →
  neighborhood one-liner) lets you send cheap tasks to cheaper models.
  See `apps/api/models/provider_factory.py` for the priority cascade.

- **ChromaDB vs Pinecone vs pgvector?** ChromaDB is the right call for
  a single-developer project — embedded mode runs in-process for
  demo, scales to a small VPS for production, no external service to
  bill. MMR reranking lifted relevance noticeably (30-40% in our
  internal evals).

- **Why MIT if you're building a hosted business?** Open-core. The
  engine stays free; commercial features (live data, accounts, AI CRM)
  gate the hosted tier. The repo is the marketing surface — it's how
  developers discover PropVector AI.

---

## Assets checklist before posting

- [ ] Live demo URL responds 200: `https://realestate-web-dz1y.onrender.com/`
- [ ] GitHub repo link works
- [ ] og:image renders (Twitter Card Validator check)
- [ ] One good demo GIF or screenshot linked in post
- [ ] Title under 80 chars
- [ ] Body under 400 words
- [ ] First comment drafted and ready to paste immediately

## Posting day-of checklist

- [ ] Post early UTC (HN peak: 8-10am UTC = 4-6am EST = 1-3am PST)
- [ ] Stay online for the first 2-3 hours to respond to comments
- [ ] Upvote substantive comments, not just "great post" ones
- [ ] Do NOT use HN-bait ("AMA", "I quit my job", etc.)
- [ ] Tag accurately: include "open source", "AI", "real estate"