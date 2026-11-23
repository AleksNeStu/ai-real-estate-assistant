# Show HN — Draft

> **Status:** Draft. Operator (AleksNeStu) to publish manually per Rule 1
> (no push / no publish from agent identity).
> **Tag length:** title ≤ 80 chars; body ~250-400 words.

---

## Title (≤ 80 chars)

**Show HN: A free property valuation on Poland's official notarial prices (MIT)**

Alternatives:
- "Show HN: An open-source AI property search that values a flat from the notarial register"
- "Show HN: I built a property valuation that shows the comparable sales it used"

## Body

Hi HN,

I built **AI Real Estate Assistant** — an open-source property search and
valuation engine, MIT-licensed. The part I could not find anywhere else: it
values an address against **Poland's official register of notarial
transaction prices, and shows the sales it compared.**

Give it a flat — city, street, area, rooms — and it answers with a price, the
band it is confident in, the median price per square metre, **how many
registered sales the comparison stands on, the period those sales cover**, and
the comparable sales themselves: address, area, price, date, floor and the
notary's deed reference.

The register is the *Rejestr Cen Nieruchomości*, published weekly by GUGiK as
open GeoParquet — no key, no licence, no terms to accept. The engine
downloads it, stores the sales, and compares your address with the ones
people actually paid for.

Why that matters: every "AI for real estate" tool I tried either invented its
prices or asked for money before it would show its work. This one shows its
work, and the work is a government register.

What else works today:

- Conversational search with automatic filter extraction (hybrid semantic +
  keyword retrieval over ChromaDB, MMR reranking)
- A buyer memory: sign in with Google and the assistant keeps your budget, the
  areas you ruled out, the listings you liked and disliked — a ruled-out area
  is a *filter*, not a down-ranked result
- Financial tools: mortgage, rent-vs-buy, ROI, TCO — the mortgage and the TCO
  read the NBP reference rate at request time
- A neighbourhood index measured from OpenStreetMap features (schools, transit,
  amenities, safety), every score naming the map features it came from
- 9 interface languages (English and Polish maintained, the rest fall back to
  English)

The catalogue on the live demo is seeded, so a visitor can explore the
interface at once. The valuation is not seeded — it reads the register.

Stack: FastAPI · Next.js 16 · React 19 · ChromaDB · SQLite or PostgreSQL ·
Docker · GitHub Actions.

MIT and self-hostable: `docker compose up`, bring your own key (17 providers,
or a local Ollama). The hosted tier (PropVector AI) sells the listing feeds
and the managed tier.

Live demo: https://realty.kittray.com/en
Source: https://github.com/AleksNeStu/ai-real-estate-assistant

Happy to answer questions about the register, the RAG pipeline, the provider
routing, or ChromaDB tuning.

---

## First comment (operator to post immediately after submission)

Thanks for the questions — happy to dig into anything.

Quick answers to the inevitable ones:

- **Where do the prices come from?** The notarial register. GUGiK publishes one
  open GeoParquet file per voivodeship, every week; the engine ingests the
  sales it holds and compares an address with the comparable ones. The answer
  names the sample size, the comparison area and the period — and lists the
  sales, with their deed references, so you can check the arithmetic.
  `apps/api/data/rcn/`.

- **What is not there?** Live portal feeds (Otodom, Idealista, MLS) — that is
  the hosted tier's job. Listing the comparables is the free part, and it is
  the part that was missing everywhere else.

- **Multi-provider LLM routing isn't just a config flag — why bother?**
  Reliability. When one provider rate-limits or has an outage, the chat speaks
  with the provider the visitor — or the deployment — picked, falls back to the
  deployment's default provider, and then to Ollama on the server. The
  free-tier cascade (`POST /api/v1/chat/free`) is a deployment variable: the
  repository default is MiniMax → Ollama (local, on the server) → OpenRouter's
  free models → Google's free Flash. See `apps/api/api/dependencies.py` for
  the chat's chain, `apps/api/utils/free_tier.py` for the free-tier one and
  `apps/api/config/settings.py` for the order it starts in.

- **Isn't this just a chatbot with a filter bolted on?** The part that isn't:
  the buyer memory. Every turn, the same model that answered it reads the
  conversation back and writes down the facts it learned — a budget, an area
  ruled out, a listing liked or disliked — into a per-buyer table. The next
  search reads that table back. A ruled-out area and a disliked listing are
  *filters* (removed from the result set), not down-ranked ones. It only
  applies to a signed-in buyer — an anonymous request reads no memory and
  writes none, and is rate-limited instead. See
  `apps/api/services/buyer_memory_service.py` and
  `apps/api/api/routers/chat.py`.

- **ChromaDB vs Pinecone vs pgvector?** ChromaDB is the right call for a
  single-developer project — embedded mode runs in-process for the demo, scales
  to a small VPS for production, no external service to bill. MMR reranking is
  what makes the hybrid retrieval work.

- **Why MIT if you're building a hosted business?** Open-core. The engine
  stays free; the listing feeds, the managed tier and the enterprise pieces
  gate the hosted tier. The repo is the marketing surface — it is how
  developers find the product.

---

## Assets checklist before posting

Re-verified on 2026-11-23 against the live deployment, which runs the
**v5.5.0** build (`build.sha = 4491cb799a150e60fe59cfa54612069c363514b4`):

- [x] Live demo URL responds 200: `https://realty.kittray.com/en` — the bare
      root redirects to `/pl`, so the English path is the one to publish
- [x] The valuation answers from the register on the live deployment:
      `POST /api/v1/tools/valuation` with `{"city": "Kraków", "street":
      "Myśliwska", "area_sqm": 60, "rooms": 3}` answers **959,181.85 PLN**,
      `source: rcn`, `confidence: high`, `sample_size: 24`, comparison area
      `Myśliwska, Kraków`, period `2025-06-18 → 2026-10-12`, with 20
      comparables listed (address, area, price, date, rooms, floor, deed
      reference)
- [x] The register behind it holds 826,919 registered sales, ingested on
      2026-11-23 from the open GUGiK exports
- [x] The anonymous chat answers with a real model:
      `GET /api/v1/capabilities` reports `llm.provider: minimax`,
      `llm.model: MiniMax-M3.1-Flash`; `POST /api/v1/chat/free` returns an
      answer with its sources
- [x] GitHub repo link works
- [x] og:image renders: `https://realty.kittray.com/og-image.png` answers 200 with
      a PNG of 1200×630 (the card a Twitter validator asks for)
- [x] One good demo GIF or screenshot linked in post — the six-second dark demo
      is at `assets/clips/demo-6s.gif` (and `assets/clips/demo-6s.mp4` for the
      video), and the dark screenshot set is at `assets/screenshots/`
- [x] The sign-in screen, for the buyer-memory claim —
      `assets/screenshots/login-dark.png`
- [x] Title under 80 chars — the title above is 77; the one it replaced was 94
- [x] Body under 400 words — 366
- [x] First comment drafted and ready to paste immediately — 382 words
- [x] The claims the body makes, read off the running deployment
      (`GET /api/v1/capabilities`): `auth.jwt_enabled: true`,
      `auth.oauth.google: true`, `auth.demo_user_bypass: false` — so "sign in
      with Google to switch on the buyer memory" is the truth; the provider the
      demo answers with is `minimax` / `MiniMax-M3.1-Flash`; the codebase
      carries 17 provider modules and nine locales
      (`apps/web/src/i18n/config.ts`: pl, en, ru, de, es, it, pt, tr, uk),
      English and Polish maintained and the rest frozen onto English

**What ships with the next release, not in the v5.5.0 build the demo runs
now:** the valuation page that calls the register from the browser
(`/[locale]/valuation`, the answer linkable), the NBP reference rate in the
mortgage and TCO tools, the OpenStreetMap neighbourhood index, and the
open-source CLI (`packages/cli`). They are in the repository on `dev`; the
demo is one release behind because the promotion to `main` is the operator's
click.

Everything below needs the operator: the posting, the account, the voice.

## Posting day-of checklist

- [ ] Post early UTC (HN peak: 8-10am UTC = 4-6am EST = 1-3am PST)
- [ ] Stay online for the first 2-3 hours to respond to comments
- [ ] Upvote substantive comments, not just "great post" ones
- [ ] Do NOT use HN-bait ("AMA", "I quit my job", etc.)
- [ ] Tag accurately: include "open source", "AI", "real estate"
