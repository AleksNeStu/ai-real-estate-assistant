# YouTube Demo — Scripts

> **Status:** Drafts. Operator to record and publish manually per Rule 1.
> **Suggested title pattern:** "AI Real Estate Assistant — <angle>"
> **Thumbnail:** dark theme with property screenshot + "AI" callout

---

## Video 1: 90-second hero demo (vertical + landscape)

**Title:** AI Real Estate Assistant — search with natural language

**Hook (0-5s):**

> "Tired of clicking through 14 dropdowns just to find an apartment?
> Watch me search for one in plain English — and watch it actually
> work."

**Demo (5-50s):**

1. (5s) Open https://realestate-web-dz1y.onrender.com/
2. (10s) Click "Start Searching"
3. (15s) Type "2-bedroom apartment in Kraków under 500k, family-friendly"
4. (20s) Show results appearing — filters extracted, listings matched
5. (25s) Click a listing → show property detail page with neighborhood
   one-liner
6. (35s) Click "Valuation" tab → show multi-year forecast
7. (45s) Switch language to Polish → show localized UI

**Tagline (50-70s):**

> "Open-source, MIT-licensed, self-hostable. Six LLM providers with
> automatic fallback. FastAPI + Next.js + ChromaDB. Live demo at
> realestate-web-dz1y.onrender.com. Source on GitHub: AleksNeStu /
> ai-real-estate-assistant. Hosted tier at propvectorai.com."

**CTA (70-90s):**

> "Star the repo if you find it useful. We have 9 languages, financial
> tools, AI valuation, and an interactive map with clustered markers.
> Thanks for watching."

---

## Video 2: 5-minute architecture deep-dive (landscape)

**Title:** Building a self-hostable AI property search — architecture deep-dive

**Hook (0-15s):**

> "Three years ago I moved to Poland and tried to find an apartment.
> Every portal was filter-first. So I built this. Today it's an
> open-source AI property search with multi-provider LLM fallback,
> hybrid retrieval, and 9 languages. Here's the architecture."

**Section 1: The stack (15-60s)**

- Backend: FastAPI + Python 3.12
- Frontend: Next.js 16 + React 19
- Vector store: ChromaDB (embedded mode for demo, scales to VPS)
- 6 LLM providers with priority cascade
- 9 languages with EU AI Act compliance labels
- Why this stack: boring tech, no-GPL, 1-year-old libs

**Section 2: Hybrid retrieval (60-150s)**

- Pure vector search misses exact matches ("2-bedroom", "Kraków",
  price ceilings under 500k)
- Pure keyword misses semantic intent ("family-friendly neighborhood
  near good schools")
- Hybrid with MMR reranking: 30-40% relevance lift in internal evals
- Show code: `apps/api/vector_store/reranker.py`
- Show ChromaDB query construction with semantic + keyword weights

**Section 3: Multi-provider LLM routing (150-270s)**

- Per-task priority cascade in `apps/api/models/provider_factory.py`
- Chat → primary provider (configurable)
- Property valuation → premium model (Opus, Sonnet, GPT-4o)
- Neighborhood one-liner → cheap model (Haiku, DeepSeek)
- Embeddings → dedicated embedding model
- When one provider rate-limits, the demo keeps working — automatic
  fallback chain
- Local Ollama as always-on fallback for chat
- Show code: provider factory + lazy import logic

**Section 4: 9 languages, EU AI Act (270-330s)**

- Translation keys: `messages/{locale}.json`
- Locale-aware date / currency / number formatting
- Hreflang SEO across 9 locales
- Per-language LLM prompts
- EU AI Act compliance labels in every locale
- Why: DACH and LatAm markets are materially different from
  English-first default

**Section 5: Render free-tier memory trick (330-390s)**

- Render free tier: 512 MB RAM cap
- 13 LLM providers × eager import = 530 MB → over the cap
- Environment-conditional lazy loading: only active `DEFAULT_PROVIDER`
  imports at startup on Render
- Full eager loading on VPS / Docker (no memory constraint)
- One code path, two memory profiles
- Show code: `RENDER` env var check in provider_factory.py

**Section 6: Open-core model + hosted tier (390-450s)**

- Engine stays MIT-licensed and free
- Live data feeds, accounts, AI CRM gate the hosted tier
- propvectorai.com covers live MLS / portal feeds
- This repo is the marketing surface for developers

**CTA (450-480s):**

> "Live demo at realestate-web-dz1y.onrender.com. Source on GitHub.
> Self-hostable with Docker. Hosted tier at propvectorai.com. Thanks
> for watching."

---

## Video 3: 30-second vertical (TikTok / Reels / Shorts)

**Hook (0-3s):**

> "I built an AI that searches real estate in plain English."

**Demo (3-22s):**

1. (3s) Type query
2. (8s) Show results
3. (12s) Show property detail
4. (16s) Switch language
5. (20s) Show map

**CTA (22-30s):**

> "Open-source. Link in bio."

---

## Shot list for recording

**Static shots (pre-record):**

- [ ] Landing page on dark theme (1280×800)
- [ ] Search bar with query typed
- [ ] Search results page with filters
- [ ] Property detail page with neighborhood one-liner highlighted
- [ ] Valuation page with multi-year forecast chart
- [ ] Map view with clustered markers
- [ ] Language switcher dropdown (open)
- [ ] Polish-language UI (after switching)
- [ ] GitHub repo with stars, README

**Animated shots (record live):**

- [ ] Typing query in search bar
- [ ] Switching languages
- [ ] Scrolling results
- [ ] Hover effects on property cards
- [ ] Onboarding tour steps (B1 — new component)
- [ ] Try-these chips click (B2 — new component)

**Screen recording tools:**

- macOS: built-in QuickTime Player + iPhone Mirroring, or ScreenFlow
- Windows: OBS Studio (free), or built-in Xbox Game Bar
- Browser: Chrome DevTools > More Tools > Recorder (great for web)

**Post-production:**

- [ ] Subtitles (auto-generated, then hand-corrected)
- [ ] Background music (royalty-free, low volume)
- [ ] Zoom-ins on key UI moments
- [ ] B-roll of architecture diagrams during deep-dive video

---

## Publishing cadence

| Day | Video | Channel | Notes |
|---|---|---|---|
| Day 0 | 90s hero | YouTube main + TikTok + Shorts | Reach across platforms |
| Day +14 | 5min deep-dive | YouTube main only | Longer audience, evergreen |
| Day +30 | 30s vertical repost | TikTok + Reels | Algorithm boost from engagement on first |

## Thumbnail A/B variants (test 2-3 per video)

- Variant 1: dark theme + property screenshot + "AI" red callout
- Variant 2: code snippet overlay + "open-source" tag
- Variant 3: before/after filter UI vs. natural-language query