# Product Hunt — Draft

> **Status:** Draft. Operator to publish manually per Rule 1.
> **Launch day:** Tuesday or Wednesday (PH sweet spot), 12:01am PT
> so the day starts cleanly. Avoid Mondays (cluttered) and Fridays
> (low traffic).

---

## Asset checklist (upload to PH during submission)

Checked on 2026-11-16 (the assets are on disk; the live build is v5.3.9):

- [x] Logo: 512×512 PNG (transparent background) and JPG (white background) —
      `assets/logo.png` and `assets/logo.jpg`
- [x] Screenshots: 4-6 (1280×800 minimum, PNG or JPG) — the dark set is at
      `assets/screenshots/`
  - [x] Landing / hero — `assets/screenshots/home-dark.png`
  - [x] AI chat with natural-language query — `assets/screenshots/chat-dark.png`
  - [x] Search results with filters — `assets/screenshots/search-results-dark.png`
  - [x] City overview — the map, the ledger of the cities, the selected one
        (`assets/screenshots/city-overview-dark.png`)
  - [x] Property detail page — the listing on its own page, with the
        neighbourhood one-liner, the price, the numbers and the comparable
        listings (`/{locale}/property/{id}`) —
        `assets/screenshots/property-detail-dark.png`
  - [x] AI valuation page (multi-year forecast) —
        `assets/screenshots/valuation-dark.png`
  - [x] Interactive map with clustered markers — `assets/screenshots/search-dark.png`
  - [x] The sign-in screen — `assets/screenshots/login-dark.png` (and
        `register-dark.png`) — the visual proof of the Google sign-in that
        switches the buyer memory on
- [x] og-image: 1200×630 (already created at `apps/web/public/og-image.png`)
- [x] Demo GIF (≤ 30s, optional but high-impact) — `assets/clips/demo-6s.gif`
      (six seconds, dark)
- [x] Maker profile: AleksNeStu GitHub profile pic + bio

---

## Tagline (≤ 60 chars)

**Property search that speaks natural language — open source**

Alternatives:
- "AI property search with multi-provider LLM fallback"
- "The open-source Zillow alternative for developers"
- "Property search that speaks natural language, not filters"

## Description (≤ 260 chars)

Open-source conversational AI for property search. Ask in natural
language, get matched listings, valuation forecasts, and neighborhood
summaries. It remembers your budget and what you ruled out. UI in 9
languages (en/pl maintained). MIT.

Alternatives (≤ 260 chars each):
1. An open-source AI property search platform. Built with FastAPI +
   Next.js 16 + ChromaDB. Multi-provider LLM fallback. UI in 9 languages
   (en/pl maintained). MIT license. Self-hostable.
2. The open-source, AI-first alternative to filter-first property
   portals. Natural language queries, hybrid retrieval, multi-year
   price forecasts. UI in 9 languages (en/pl maintained). FastAPI +
   Next.js 16 + ChromaDB. MIT.

---

## Links (PH takes one primary link; the repository is the secondary)

- **Primary:** https://realty.kittray.com/en
- Live demo — no account and no API key to try search, chat and valuation.
  The hosted instance answers with a real model the project pays for, so
  exploring costs the visitor nothing. Sign in with Google to switch on the
  buyer memory.
- **Secondary:** https://github.com/AleksNeStu/ai-real-estate-assistant

---

## Topics (pick 3-5 from PH categories)

- Artificial Intelligence
- Open Source
- Real Estate
- Developer Tools
- Productivity
- Tech

## Maker-comment (operator to post first, immediately after launch)

Hey Product Hunt folks 👋 — solo developer here.

I built AI Real Estate Assistant because every "AI for real estate"
tool I tried was either $200/month or hallucinated square footage.

**The story:**

Three years ago I moved to Poland and tried to find an apartment. Every
portal was filter-first: dropdowns, sliders, checkboxes. I wanted to
type "2-bedroom apartment in Kraków under 500k, near a good school" and
get matched listings. Nothing did that. So I built it.

**What's interesting technically:**

- A buyer memory: every turn, the same model that answered it reads the
  conversation back and writes down what it learned — a budget, an area
  ruled out, a listing liked or disliked — into a per-buyer table. The next
  search reads that table back. A ruled-out area and a disliked listing are
  filters, not down-ranked results.
- Hybrid semantic + keyword retrieval via ChromaDB with MMR reranking
- Multi-provider LLM routing (17 providers: OpenAI, Anthropic, Google, Grok,
  DeepSeek, MiniMax, local Ollama among them) with automatic fallback chain
- Environment-conditional lazy provider loading (a memory-capped host
  imports one provider at startup, a VPS imports all 17)
- UI in 9 languages — English and Polish maintained, the rest fall back to
  English

**What's NOT here:**

- Live MLS / Idealista / Otodom feeds (the demo uses curated mock data)
- Native mobile app (PWA only)
- Payment / escrow / contracts (not in scope)

**Open-core model:**

The engine is MIT-licensed and free. Live data feeds, running it for
you, and the enterprise pieces gate the hosted tier at
[propvectorai.com](https://propvectorai.com). Accounts, favourites and
saved searches are in the repo — they need an account, not a payment.
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

> The demo answers with a real model the project pays for — MiniMax's
> MiniMax-M3.1-Flash — and falls back to a local model if that one is
> unreachable, so the answers are not canned. The catalogue is seeded demo
> data, not live listings; in a deployment with your own data, accuracy
> depends on (a) the source data quality and (b) the LLM provider chosen
> for each task. Per-task priority cascade in
> `apps/api/models/provider_factory.py`.

**Comment: "Can I self-host this?"**

> Yes — MIT license, Docker Compose, 5-minute quickstart.
> https://github.com/AleksNeStu/ai-real-estate-assistant/blob/dev/docs/development/QUICKSTART_5MIN.md
> Bring your own LLM API keys (any of the 17 supported providers or
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
- [ ] Update the README's "Ideas, forks, and other ways to work with us" section with PH screenshot
