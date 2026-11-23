# Product Hunt — Draft

> **Status:** Draft. Operator to publish manually per Rule 1.
> **Launch day:** Tuesday or Wednesday (PH sweet spot), 12:01am PT
> so the day starts cleanly. Avoid Mondays (cluttered) and Fridays
> (low traffic).

---

## Asset checklist (upload to PH during submission)

Checked on 2026-11-23 (the assets are on disk; the live build is v5.5.0):

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

**Property valuation on official notarial prices — open source**

Alternatives:
- "Free valuation on Poland's official notarial prices"
- "The open-source Zillow alternative for developers"
- "Property search that speaks natural language, not filters"

## Description (≤ 260 chars)

Open-source property search and valuation. Value any address against
Poland's official register of notarial prices — with the comparable sales,
the sample and the period shown. Search in natural language. MIT.

Alternatives (≤ 260 chars each):
1. Open-source property search with a free valuation on official notarial
   prices. The comparable sales, the sample and the period are shown, not
   hidden. FastAPI + Next.js + ChromaDB. 17 LLM providers. UI in 9 languages
   (en/pl maintained). MIT, self-hostable.
2. The open-source, AI-first alternative to filter-first property portals.
   Value an address from the government register of notarial transactions.
   Hybrid retrieval, buyer memory, natural-language queries. FastAPI +
   Next.js + ChromaDB. MIT.

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

I built AI Real Estate Assistant because every "AI for real estate" tool I
tried either invented its square footage or asked for a subscription before
it would show its work.

**The thing to try first:**

Ask for a flat — city, street, area, rooms — and you get a valuation of it
against **Poland's official register of notarial transaction prices**. The
register is published weekly by the state mapping office as open data: no
key, no licence. The engine ingests the sales and compares your address with
the ones people actually paid for.

You get the price, the band it is confident in, the median price per square
metre, **how many registered sales the comparison stands on, the period those
sales cover** — and the comparable sales themselves: address, area, price,
date, floor and the notary's deed reference. If the comparison is thin, it
says so instead of inventing a number.

**The story:**

Three years ago I moved to Poland and tried to find an apartment. Every
portal was filter-first: dropdowns, sliders, checkboxes. I wanted to
type "2-bedroom apartment in Kraków under 500k, near a good school" and
get matched listings. Nothing did that. So I built it.

**What's interesting technically:**

- The register is ingested as open GeoParquet per voivodeship and stored
  sale by sale, so a valuation never waits for a download and every answer
  names the sample it stands on
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
- A neighbourhood index measured from OpenStreetMap features — every score
  names the map features it was computed from
- UI in 9 languages — English and Polish maintained, the rest fall back to
  English

**What's NOT here:**

- Live portal feeds (Otodom, Idealista, MLS) — those are the hosted tier's
  job. The notarial prices are free and official; the listing feeds are not
- Native mobile app (PWA only)
- Payment / escrow / contracts (not in scope)

**Open-core model:**

The engine is MIT-licensed and free. Listing feeds, running it for you, and
the enterprise pieces gate the hosted tier at
[propvectorai.com](https://propvectorai.com). Accounts, favourites and
saved searches are in the repo — they need an account, not a payment.
This repo is the marketing surface for developers.

Happy to answer questions about the register, the RAG pipeline, ChromaDB
tuning, or the multi-provider routing logic.

---

## Reply templates for common PH comments

**Comment: "Why would I use this over Zillow?"**

> Zillow is great for end-users browsing real listings in the US.
> This one is built for developers who want a self-hostable, AI-first
> reference stack — and, differently, for anyone who wants a price for a
> specific flat that stands on the notarial register with the comparable
> sales listed. If you want live portal feeds on top of this engine, the
> hosted tier at propvectorai.com covers it.

**Comment: "How is this different from Idealista / Otodom / Rightmove?"**

> Same answer — those are end-user portals with live listing feeds in
> specific markets. This is a developer platform: the prices it values
> against are the official notarial register, which is open data, and the
> comparables behind every answer are listed. The hosted tier covers live
> listing feeds in markets where it's commercially viable.

**Comment: "Is the AI accurate?"**

> The demo answers with a real model the project pays for — MiniMax's
> MiniMax-M3.1-Flash — and falls back to a local model if that one is
> unreachable, so the answers are not canned. The valuation is not a model
> estimate at all: it is a median over the registered sales of comparable
> flats, and every answer states how many sales it used and over which
> period. Accuracy then depends on (a) the source data quality and (b) the
> LLM provider chosen for the request. The provider chain is in
> `apps/api/api/dependencies.py`.

**Comment: "Can I self-host this?"**

> Yes — MIT license, Docker Compose, 5-minute quickstart.
> https://github.com/AleksNeStu/ai-real-estate-assistant/blob/dev/docs/development/QUICKSTART_5MIN.md
> Bring your own LLM API keys (any of the 17 supported providers or
> local Ollama). The official price register needs no key at all — it is
> open data, and one command refreshes it.

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
