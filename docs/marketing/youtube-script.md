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

1. (5s) Open https://realty.kittray.com/en
2. (10s) Click "Start Searching"
3. (15s) Type "2-bedroom apartment in Kraków under 500k, family-friendly"
4. (20s) Show results appearing — filters extracted, listings matched
5. (25s) Click a listing → show property detail page with neighborhood
   one-liner
6. (35s) Click "Valuation" tab → show multi-year forecast
7. (45s) Switch language to Polish → show localized UI

**The beat that makes it (50-72s):** sign in with Google, then run two
turns —

1. ask "2-bedroom apartment in Kraków" → results include Kazimierz
2. say "actually, nothing in Kazimierz" → the assistant acknowledges
3. ask the same thing again → **Kazimierz is gone from the result set**

Say the line: *"It remembered."* The third turn is the proof, and the
catalogue really does carry Kazimierz — this is not staged. This is the
part a competitor demo cannot copy in a weekend.

**Tagline (72-84s):**

> "Open-source, MIT-licensed, self-hostable. 17 LLM providers with
> automatic fallback. It remembers your budget and what you ruled out.
> FastAPI + Next.js + ChromaDB. Live demo at realty.kittray.com/en.
> Source on GitHub: AleksNeStu / ai-real-estate-assistant. Hosted tier at
> propvectorai.com."

**CTA (84-90s):**

> "Star the repo if you find it useful. We have financial tools, AI
> valuation, a map with clustered markers, and an assistant that
> remembers you. Thanks for watching."

---

## Video 2: 8-minute architecture deep-dive (landscape)

**Title:** Building a self-hostable AI property search — architecture deep-dive

**Hook (0-15s):**

> "Three years ago I moved to Poland and tried to find an apartment.
> Every portal was filter-first. So I built this. Today it's an
> open-source AI property search with multi-provider LLM fallback,
> hybrid retrieval, and an assistant that remembers what you told it.
> Here's the architecture."

**Section 1: The stack (15-60s)**

- Backend: FastAPI + Python 3.12
- Frontend: Next.js 16 + React 19
- Vector store: ChromaDB (embedded mode for demo, scales to VPS)
- 17 LLM providers with priority cascade
- UI in 9 languages — English and Polish maintained, the rest frozen and
  falling back to English
- Why this stack: boring tech, no-GPL, 1-year-old libs

**Section 2: Hybrid retrieval (60-150s)**

- Pure vector search misses exact matches ("2-bedroom", "Kraków",
  price ceilings under 500k)
- Pure keyword misses semantic intent ("family-friendly neighborhood
  near good schools")
- Hybrid with MMR reranking over the ChromaDB index
- Show code: `apps/api/vector_store/reranker.py`
- Show ChromaDB query construction with semantic + keyword weights

**Section 3: Multi-provider LLM routing (150-270s)**

- Per-task priority cascade in `apps/api/models/provider_factory.py`
- Chat → primary provider (configurable)
- Search / tools / analysis → the default per-task model, a free one
- Embeddings → dedicated embedding model
- The deployed chain: MiniMax → Ollama (local, on our own server) →
  OpenRouter free models
- When one provider rate-limits, the demo keeps working — automatic
  fallback chain
- Show code: provider factory + lazy import logic

**Section 4: The buyer memory (270-360s)**

- The problem: growing the context window re-bills the whole history
  every turn and still forgets by turn ten
- The approach: after each turn, the same model that answered it extracts
  what it learned — a budget, an area ruled out, a listing liked or
  disliked — into a per-buyer table
- The next turn recalls only the facts relevant to the query, and a
  compact block goes into the prompt
- Steering vs filtering: a budget narrows the price range, a ruled-out
  area removes a place, a disliked listing is *removed from the result
  set* — not ranked lower
- Anonymous means anonymous: with no session, the memory is neither read
  nor written
- Show code: `apps/api/services/buyer_memory_service.py` and
  `apps/api/api/routers/chat.py`

**Section 5: Nine languages, two maintained (360-405s)**

- Translation keys: `messages/{locale}.json`
- Locale-aware date / currency / number formatting
- Hreflang SEO across 9 locales
- Per-language LLM prompts
- The honest split: the interface ships in 9 locales, English and Polish
  are maintained, the other seven are frozen and fall back to English —
  a translation spent before the traffic arrives is a session spent for
  nothing
- Show code: `apps/web/src/i18n/policy.ts` and `merge.ts`

**Section 6: Lazy loading and the host (405-450s)**

- The provider factory knows 17 providers; importing all of them costs
  real memory
- A memory-capped host asks for the lazy path — the factory reads the
  `RENDER` env var and imports only the active provider at startup, the
  rest on first use
- Everywhere else — local dev, CI, our own VPS — all 17 load eagerly, so
  nothing surprises you in development
- One code path, two memory profiles
- Show code: the `RENDER` check in `provider_factory.py`

**Section 7: Open-core model + hosted tier (450-480s)**

- Engine stays MIT-licensed and free
- Live data feeds, accounts, AI CRM gate the hosted tier
- propvectorai.com covers live MLS / portal feeds
- This repo is the marketing surface for developers

**CTA (480-500s):**

> "Live demo at realty.kittray.com/en. Source on GitHub.
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
- [ ] The sign-in screen — `assets/screenshots/login-dark.png`
- [ ] GitHub repo with stars, README

**Animated shots (record live):**

- [ ] Typing query in search bar
- [ ] Signing in with Google
- [ ] The second chat turn — the one where the memory applies (say "nothing
      in Kazimierz", show the next result set without it)
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
| Day +14 | 8min deep-dive | YouTube main only | Longer audience, evergreen |
| Day +30 | 30s vertical repost | TikTok + Reels | Algorithm boost from engagement on first |

## Thumbnail A/B variants (test 2-3 per video)

- Variant 1: dark theme + property screenshot + "AI" red callout
- Variant 2: code snippet overlay + "open-source" tag
- Variant 3: before/after filter UI vs. natural-language query
