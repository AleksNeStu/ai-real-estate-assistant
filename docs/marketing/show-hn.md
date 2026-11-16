# Show HN — Draft

> **Status:** Draft. Operator (AleksNeStu) to publish manually per Rule 1
> (no push / no publish from agent identity).
> **Tag length:** title ≤ 80 chars; body ~250-400 words.

---

## Title (≤ 80 chars)

**Show HN: AI Real Estate Assistant — property search in plain language (MIT)**

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
plugs into 17 LLM providers (OpenAI, Anthropic, Google, Grok, DeepSeek,
OpenRouter, Groq, Mistral, MiniMax and local Ollama among them) with an
automatic fallback chain so a single provider rate-limit doesn't kill the
demo. Per-task and per-user provider selection lives in
`apps/api/models/provider_factory.py`.

What works today:
- Conversational search with automatic filter extraction
- A buyer memory: sign in once and the assistant keeps what you told it —
  your budget, the areas you ruled out, the listings you liked and disliked —
  and applies it to every later search. A ruled-out area and a disliked
  listing are filters, not down-ranked results.
- Financial tools: mortgage calculator, rent-vs-buy, ROI, TCO, CMA reports
- AI property valuation with multi-year price forecast (1/3/5/10y)
- AI neighborhood one-liner on property detail pages
- Interactive maps with clustered markers (Mapbox / Leaflet)
- 9 interface languages (English, Polish, Russian, German, Spanish, Italian,
  Portuguese, Turkish, Ukrainian), with English and Polish maintained and the
  rest falling back to English

Why I built it: I'm not trying to replace Zillow or Idealista. They're
aggregators with live MLS feeds and millions of users — I'm a solo
developer. What I wanted was a developer-friendly reference stack for
AI-first property UX, open-core, self-hostable, MIT-licensed, that
someone could fork on a Friday and ship a custom property experience on
Monday. The hosted SaaS tier (PropVector AI, propvectorai.com) covers
live data feeds, running it for you, and the enterprise pieces for when
you outgrow the demo.

Stack: FastAPI · Next.js 16 · React 19 · ChromaDB · PostgreSQL or SQLite ·
Docker · GitHub Actions · Uptime Kuma.

Live demo: https://realty.kittray.com/en
Browsing needs no account — the free tier covers it. Sign in with Google to
switch on the buyer memory.
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
  keeps working. The deployed chain is MiniMax → Ollama (local, on the
  server) → OpenRouter's free models, and the default per-task model is a
  free one, so a provider outage doesn't take the demo down with it.
  See `apps/api/models/provider_factory.py` for the priority cascade.

- **Isn't this just a chatbot with a filter bolted on?**
  The part that isn't: the buyer memory. Every turn, the same model that
  answered it reads the conversation back and writes down the facts it
  learned — a budget, an area ruled out, a listing liked or disliked — into
  a per-buyer table. The next search reads that table back. A ruled-out area
  and a disliked listing are *filters* (removed from the result set), not
  down-ranked ones. It only applies to a signed-in buyer — an anonymous
  request reads no memory and writes none, and is rate-limited instead.
  See `apps/api/services/buyer_memory_service.py` and
  `apps/api/api/routers/chat.py`.

- **ChromaDB vs Pinecone vs pgvector?** ChromaDB is the right call for
  a single-developer project — embedded mode runs in-process for
  demo, scales to a small VPS for production, no external service to
  bill. MMR reranking is what makes the hybrid retrieval work.

- **Why MIT if you're building a hosted business?** Open-core. The
  engine stays free; commercial features (live data, accounts, AI CRM)
  gate the hosted tier. The repo is the marketing surface — it's how
  developers discover PropVector AI.

---

## Assets checklist before posting

Re-verified on 2026-11-16 against the live deployment, which now runs the
**v5.3.8** build:

- [x] Live demo URL responds 200: `https://realty.kittray.com/en` — the bare
      root 307-redirects to `/pl`, so the English path is the one to publish
- [x] GitHub repo link works
- [x] og:image renders: `https://realty.kittray.com/og-image.png` answers 200 with
      a PNG of 1200×630 (the card a Twitter validator asks for)
- [x] One good demo GIF or screenshot linked in post — the six-second dark demo
      is at `assets/clips/demo-6s.gif` (and `assets/clips/demo-6s.mp4` for the
      video), and the dark screenshot set is at `assets/screenshots/`
- [x] The sign-in screen, for the buyer-memory claim —
      `assets/screenshots/login-dark.png`
- [x] Title under 80 chars — the title above is 75; the one it replaced was 94
- [x] Body under 400 words — 367
- [x] First comment drafted and ready to paste immediately — 320 words
- [x] The claims the body makes, read off the running deployment
      (`GET /api/v1/capabilities`): `auth.jwt_enabled: true`,
      `auth.oauth.google: true`, `auth.demo_user_bypass: false` — so "browsing
      needs no account, sign in with Google to switch on the buyer memory" is
      the truth; the provider the demo answers with is `minimax` /
      `MiniMax-M3.1-Flash`; the codebase carries 17 provider modules and nine
      locales (`apps/web/src/i18n/config.ts`: pl, en, ru, de, es, it, pt, tr,
      uk), English and Polish maintained and the rest frozen onto English
- [x] The buyer memory is in the running build: `111441521` descends from the
      commits that wrote `buyer_memory_service.py` and the `chat.py` filters

Everything below needs the operator: the posting, the account, the voice.

## Posting day-of checklist

- [ ] Post early UTC (HN peak: 8-10am UTC = 4-6am EST = 1-3am PST)
- [ ] Stay online for the first 2-3 hours to respond to comments
- [ ] Upvote substantive comments, not just "great post" ones
- [ ] Do NOT use HN-bait ("AMA", "I quit my job", etc.)
- [ ] Tag accurately: include "open source", "AI", "real estate"
