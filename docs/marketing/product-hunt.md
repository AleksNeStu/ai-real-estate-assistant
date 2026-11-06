# Product Hunt — Draft

> **Status:** Draft. Operator to publish manually per Rule 1.
> **Launch day:** Tuesday or Wednesday (PH sweet spot), 12:01am PT
> so the day starts cleanly. Avoid Mondays (cluttered) and Fridays
> (low traffic).

---

## Asset checklist (upload to PH during submission)

- [ ] Logo: 512×512 PNG (transparent background) and JPG (white background)
- [ ] Screenshots: 4-6 (1280×800 minimum, PNG or JPG)
  - [ ] Landing / hero
  - [ ] AI chat with natural-language query
  - [ ] Search results with filters
  - [ ] Property detail page (v5.1 valuation + neighborhood one-liner)
  - [ ] AI valuation page (multi-year forecast)
  - [ ] Interactive map with clustered markers
- [ ] og-image: 1200×630 (already created at `apps/web/public/og-image.png`)
- [ ] Demo GIF (≤ 30s, optional but high-impact)
- [ ] Maker profile: AleksNeStu GitHub profile pic + bio

---

## Tagline (≤ 60 chars)

**Conversational AI for property search — open-source, self-hostable, MIT**

Alternatives:
- "AI property search with multi-provider LLM fallback"
- "The open-source Zillow alternative for developers"
- "Property search that speaks natural language, not filters"

## Description (≤ 260 chars)

Open-source conversational AI for property search. Ask in natural
language, get matched listings, valuation forecasts, and neighborhood
summaries. FastAPI + Next.js 16 + ChromaDB. 9 languages. MIT.

Alternatives (≤ 260 chars each):
1. An open-source AI property search platform. Built with FastAPI +
   Next.js 16 + ChromaDB. Multi-provider LLM fallback. 9 languages. MIT
   license. Self-hostable.
2. The open-source, AI-first alternative to filter-first property
   portals. Natural language queries, hybrid retrieval, multi-year
   price forecasts. FastAPI + Next.js 16 + ChromaDB. 9 languages. MIT.

---

## Topics (pick 3-5 from PH categories)

- Artificial Intelligence
- Open Source
- Real Estate
- Developer Tools
- Productivity
- Tech

## Maker-comment (operator to post first, immediately after launch)

Hey HN folks 👋 — solo developer here.

I built AI Real Estate Assistant because every "AI for real estate"
tool I tried was either $200/month or hallucinated square footage.

**The story:**

Three years ago I moved to Poland and tried to find an apartment. Every
portal was filter-first: dropdowns, sliders, checkboxes. I wanted to
type "2-bedroom apartment in Kraków under 500k, near a good school" and
get matched listings. Nothing did that. So I built it.

**What's interesting technically:**

- Hybrid semantic + keyword retrieval via ChromaDB with MMR reranking
  (30-40% relevance lift in our internal evals)
- Multi-provider LLM routing (OpenAI, Anthropic, Google, Grok,
  DeepSeek, local Ollama) with automatic fallback chain
- Environment-conditional lazy provider loading (stays under Render's
  512 MB free-tier cap, eager load on VPS)
- 9 languages with EU AI Act compliance labels built in

**What's NOT here:**

- Live MLS / Idealista / Otodom feeds (the demo uses curated mock data)
- Native mobile app (PWA only)
- Payment / escrow / contracts (not in scope)

**Open-core model:**

The engine is MIT-licensed and free. Live data, accounts, and AI CRM
gate the hosted tier at [propvectorai.com](https://propvectorai.com).
This repo is the marketing surface for developers.

Happy to answer questions about the RAG pipeline, ChromaDB tuning, or
the multi-provider routing logic.

---

## Reply templates for common PH comments

**Comment: "Why would I use this over Zillow?"**

> Zillow is great for end-users browsing real listings in the US.
> This is built for developers who want a self-hostable, AI-first
> reference stack. Different audiences. If you want live MLS data on
> top of this engine, the hosted tier at propvectorai.com covers it.

**Comment: "How is this different from Idealista / Otodom / Rightmove?"**

> Same answer — those are end-user portals with live feeds in specific
> markets. This is a developer platform with mock data out of the box.
> The hosted tier covers live data in markets where it's commercially
> viable.

**Comment: "Is the AI accurate?"**

> The demo uses simulated AI responses for instant exploration. In
> production deployments with real data and live LLM calls, accuracy
> depends on (a) the source data quality and (b) the LLM provider
> chosen for each task. Per-task priority cascade in
> `apps/api/models/provider_factory.py` — premium models for property
> valuation, cheap models for neighborhood summaries.

**Comment: "Can I self-host this?"**

> Yes — MIT license, Docker Compose, 5-minute quickstart.
> https://github.com/AleksNeStu/ai-real-estate-assistant/blob/dev/docs/development/QUICKSTART_5MIN.md
> Bring your own LLM API keys (any of the 6 supported providers or
> local Ollama).

**Comment: "Why not Pinecone / pgvector instead of ChromaDB?"**

> ChromaDB embedded mode runs in-process for the demo and scales to
> a small VPS for production. No external service to bill, no API
> rate-limits, no separate auth. For a solo developer, that's the
> right trade-off. Production at scale might want pgvector or a
> managed vector DB.

---

## Day-of launch checklist

- [ ] All assets uploaded
- [ ] Maker-comment ready to paste immediately at 12:01am PT
- [ ] Calendar blocked 9am-9pm PT launch day for reply triage
- [ ] Notify 5-10 friends / colleagues to upvote and leave genuine
      comments in the first 4 hours (PH algorithm weights first 4h
      heavily)
- [ ] Cross-post to X / Twitter the same morning with #ProductHunt tag
- [ ] Schedule a Show HN post 1-2 weeks after PH (give PH momentum
      time to settle)

## Post-launch (within 48h)

- [ ] Add PH badge to README
- [ ] Add "Featured on Product Hunt" to landing page (subtle, bottom-right)
- [ ] Save PH metrics: rank, upvotes, comments
- [ ] Update README's Project Growth section with PH screenshot