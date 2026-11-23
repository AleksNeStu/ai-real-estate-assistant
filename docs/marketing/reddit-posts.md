# Reddit Posts — Drafts

> **Status:** Drafts. Operator to publish manually per Rule 1.
> **Calendar:** Space posts 3-5 days apart to avoid cross-subreddit
> flagging as spam. Lead with `r/opensource`, end with `r/programming`.

---

## Post 1: r/opensource (lead)

**Title:** I built an open-source property valuation on Poland's official
notarial prices — it shows you the comparable sales

**Body:**

I built [AI Real Estate Assistant](https://github.com/AleksNeStu/ai-real-estate-assistant)
and the part I am proudest of answers one question honestly: *what is this
flat worth, and what is that number made of?*

Give it a flat — city, street, area, rooms — and it answers with a price, the
band it is confident in, the median price per square metre, **how many
registered sales the comparison stands on, the period those sales cover**, and
the comparable sales themselves: address, area, price, date, floor and the
notary's deed reference.

The prices come from the *Rejestr Cen Nieruchomości* — the official register
of notarial transactions, published weekly by the state mapping office as open
GeoParquet. No key, no licence, no terms. The engine ingests the sales per
voivodeship and compares your address with the ones people actually paid for.
If the comparison is too thin to price anything, it says so instead of
inventing a number.

The stack is intentionally boring:
- Backend: FastAPI + Python 3.12
- Frontend: Next.js 16 + React 19
- Vector store: ChromaDB (embedded mode for demo, scales to small VPS)
- 17 LLM providers with automatic fallback chain
- MIT license

What makes it interesting technically:
- The valuation is a median over comparable registered sales, and every
  answer carries the evidence — the sample, the comparison area, the period
  and the sales themselves
- A buyer memory: every turn, the same model that answered the turn reads
  the conversation back and writes down what it learned — a budget, an area
  ruled out, a listing liked or disliked — into a per-buyer table. The next
  search reads that table back, and a ruled-out area or a disliked listing
  is filtered out of the results rather than down-ranked.
- Hybrid semantic + keyword retrieval with MMR reranking
- Per-task and per-user LLM provider selection with priority cascade
- Environment-conditional lazy provider loading (a memory-capped host
  imports one provider at startup; a VPS imports all 17)
- A neighbourhood index measured from OpenStreetMap features, where every
  score names the map features it was computed from
- UI in 9 languages — English and Polish maintained, the rest fall back to
  English

The codebase is open-core: the engine stays free, and the hosted tier sells
the listing feeds, running it for you, and the enterprise pieces
([propvectorai.com](https://propvectorai.com)).

Live demo: https://realty.kittray.com/en
Browsing and the valuation need no account; sign in with Google to switch on
the memory.

Architecture write-up if you want to skip the code:
[large-saas-overview.md](https://github.com/AleksNeStu/ai-real-estate-assistant/blob/dev/docs/architecture/large-saas-overview.md)

Happy to answer questions about the register, RAG, ChromaDB tuning, or the
multi-provider routing logic.

---

## Post 2: r/sideproject (story-driven)

**Title:** Built a conversational AI property search over two years —
here's what I learned shipping it as a solo developer

**Body:**

Two years ago I started [AI Real Estate Assistant](https://github.com/AleksNeStu/ai-real-estate-assistant)
because every "AI for X" tool I tried for real estate either cost
$200/month or hallucinated square footage.

Today it's an open-source property search and valuation platform with a
hosted SaaS tier ([propvectorai.com](https://propvectorai.com)). The demo
gets a few hundred unique visitors a fortnight — small, but the traffic that
arrives is developers, which is the point.

Things I learned the hard way:

1. **The price has to come from somewhere real.** The first version valued a
   flat by multiplying its area by the catalogue's own price per square
   metre — a number that came from nowhere and looked like an answer. The
   version that shipped values it against the *notarial register*: the
   official weekly publication of what people actually paid for flats, as
   open data. The answer now says how many sales it used, over which period,
   and lists them. Showing the evidence turned out to be the whole product.

2. **Multi-provider LLM routing isn't optional.** When OpenAI rate-limits
   you at 2am on a Saturday and your entire demo dies, you learn fast.
   The fallback chain lives in
   `apps/api/utils/free_tier.py`.

3. **512 MB of RAM is brutal.** Solved with environment-conditional
   lazy provider loading — on a memory-capped host only the active
   `DEFAULT_PROVIDER` is imported at startup, the rest load on first use;
   everywhere else all 17 load eagerly, so local dev and CI behave
   exactly as they always did. Full DX on a VPS, and the demo still fits
   on a small host.

4. **9 languages took longer than the RAG pipeline.** Translation keys,
   locale-aware date / currency / number formatting, hreflang SEO,
   per-language LLM prompts. Worth it — DACH and LatAm markets are
   materially different from the English-first default. Today the interface
   ships in 9 locales, with English and Polish maintained and the other
   seven frozen, falling back to English rather than rotting.

5. **ChromaDB with MMR reranking changed the result set.** Started
   with pure vector search; reranker changed everything. See
   `apps/api/vector_store/reranker.py`.

6. **Making the assistant remember is harder than making it answer.** The
   extraction is one model call per turn, and it has to share the model that
   answered the turn — a second provider would mean a second bill and a
   second thing to fail. The part that surprised me: a disliked listing and
   a ruled-out area are *filters*, not down-ranked results. Ranking a
   rejected listing lower still shows it; removing it is what the buyer
   actually asked for.

The most fun part: the valuation now prices a flat from the notarial
register, the current build added the buyer memory, and property detail
pages show a neighbourhood one-liner measured from the map.

Live demo: https://realty.kittray.com/en

If you're working on a side project with LLM routing, RAG, or
multi-language UX, happy to share more code snippets in the comments.

---

## Post 3: r/programming (technical deep-dive)

**Title:** Lessons from pricing a flat against a government register of
notarial sales

**Body:**

We just shipped v5.5 of [AI Real Estate Assistant](https://github.com/AleksNeStu/ai-real-estate-assistant)
and I want to share the architectural decisions that mattered.

**A valuation is a measurement with a sample, so it has to carry the
sample.** The register of notarial transactions is published weekly, per
voivodeship, as open GeoParquet — no key, no licence. We ingest the sales
and compare an address with the comparable ones. Every answer states the
median price per square metre, **the number of registered sales it stands
on, the period those sales cover and the comparison area**, and lists the
sales themselves with their deed references. When the street has too few
sales, the comparison widens to the city — and says that it did. The part
that matters: the code path that finds no sales returns no number, so an
answer can never be a number with nothing under it.

**Hybrid retrieval is non-negotiable for property search.** Pure
vector search misses exact-match queries ("2-bedroom", "Kraków",
price ceilings under 500k). Pure keyword misses semantic intent
("family-friendly neighborhood near good schools"). ChromaDB with
MMR reranking is what makes the hybrid work.

**A buyer memory is a different problem from a bigger context window.**
The obvious design — keep the conversation and re-send it — doesn't work
past a few turns, and it re-bills the whole history on every turn. So the
facts are extracted instead: after each turn, the same model that
answered it reads the conversation back and writes down what it learned
into a per-buyer table (a budget, an area ruled out, a listing liked or
disliked). The next turn recalls only the facts relevant to the query,
and a compact block of them goes into the prompt.

Three decisions in that loop worth stealing:
- **One model, never two.** The extractor reuses the model that answered
  the turn, so there is no second provider to configure, bill, or fail.
  See `apps/api/services/buyer_memory_service.py`.
- **Steering and filtering are different operations.** A budget narrows
  the price range and a ruled-out area removes a place — but a disliked
  listing is *removed from the result set*, not ranked lower. Ranking a
  rejected listing lower still shows it; the buyer asked for it to be
  gone. See `_without_excluded` in `apps/api/api/routers/chat.py`.
- **Anonymous means anonymous.** With no session, the memory is neither
  read nor written — the prompt is byte-for-byte the prompt of before the
  memory existed.

**Multi-provider LLM routing isn't a luxury.** The provider chain lives in
`apps/api/api/dependencies.py`:
- chat → the visitor's provider if they picked one, otherwise the
  deployment's default, and then the local Ollama
- search / tools / analysis → the model the agent already holds, otherwise
  the deployment's default model
- embeddings → a dedicated local embedding model

When one provider rate-limits, the demo keeps working. This is the
difference between "AI demo" and "AI product."

**Environment-conditional lazy loading is the difference between
a 512 MB host and a $50/month VPS.** The factory knows 17 providers and
importing all of them costs real memory. On a memory-capped host it
reads the `RENDER` env var and imports only the active `DEFAULT_PROVIDER`
at startup, the rest on first use. Everywhere else — local dev, CI, our
own VPS — all 17 load eagerly, so nothing surprises you in development.
One code path, two memory profiles.

**LangChain vs raw SDKs.** We started with LangChain for tools,
switched to raw `openai` / `anthropic` SDKs for production. The
abstraction cost wasn't worth it for our use case.

Architecture docs: [large-saas-overview.md](https://github.com/AleksNeStu/ai-real-estate-assistant/blob/dev/docs/architecture/large-saas-overview.md)

What's your take on hybrid retrieval vs pure vector for property-style
queries? And on extracting facts into a side table instead of growing the
context?

---

## Post 4: r/ChatGPT or r/LocalLLaMA (LLM-architecture angle)

**Title:** How we route 17 LLM providers (OpenAI, Anthropic, Google,
Grok, DeepSeek, MiniMax, Ollama) in a self-hostable property search demo

**Body:**

Sharing the LLM routing logic from
[AI Real Estate Assistant](https://github.com/AleksNeStu/ai-real-estate-assistant)
— an open-source property search and valuation platform, v5.5, shipping a
valuation against the official notarial register, neighbourhood summaries and
a buyer memory.

The trick: a provider chain, not just a single `DEFAULT_PROVIDER`.

```
CHAT          → the visitor's pick, else the deployment's provider, else Ollama
SEARCH        → the agent's model, else the deployment's default
TOOLS         → the agent's model, else the deployment's default
ANALYSIS      → the agent's model, else the deployment's default
EMBEDDINGS    → a dedicated local embedding model
```

The free-tier cascade (`POST /api/v1/chat/free`, the endpoint that needs
no account) is a deployment variable: the repository default is MiniMax →
Ollama (local, on the server) → OpenRouter's free models → Google's free
Flash. The public demo runs MiniMax first — the provider the deployment
already pays for — with Google's free Flash behind it. The demo's own
chat has its own chain — the configured provider, then the default one,
then Ollama — so an outage upstream costs the demo nothing.

When the primary provider rate-limits during a Saturday demo, the next one
in the chain picks up the chat — the primary provider, then the default
one, then Ollama. Local Ollama is the always-on fallback for the chat; the
embeddings are local too, but they are a small local embedding model rather
than Ollama.

The provider factory (`apps/api/models/provider_factory.py`) builds the
provider; the provider and model the request runs with are resolved in
`apps/api/api/dependencies.py`. Lazy import on a memory-constrained host,
eager import on a VPS and in local dev.

What surprised me:
- **The deployment's default model carries the structured work** —
  the search and tool paths run on the model the agent already holds, and the
  expensive model is the one that writes prose.
- **Local Ollama is a real fallback, not a gimmick.** A 7B instruct model
  handles chat and neighborhood summaries surprisingly well. The valuation is
  arithmetic over registered sales rather than prose, which is exactly why it
  can run without a model at all.
- **Embeddings via local bge-small are fine for demo, but production
  wants text-embedding-3-small.** Retrieval quality matters more than
  inference cost for embeddings.

Full code:
[apps/api/api/dependencies.py](https://github.com/AleksNeStu/ai-real-estate-assistant/blob/dev/apps/api/api/dependencies.py)

Curious: how are others handling multi-provider fallback in production
LLM apps? Anyone running local Ollama as a real production fallback?

---

## Subreddit-specific posting etiquette

| Subreddit | Title tone | Avoid |
|---|---|---|
| r/opensource | Direct, technical, link to architecture | Marketing copy, "we built this", emojis |
| r/sideproject | Story-first, personal lessons | Pure feature lists, screenshots only |
| r/programming | Technical deep-dive, code-level | Product positioning, hosted SaaS pitch |
| r/ChatGPT | LLM-routing specific, focused | Generic "AI for X" framing |

## Posting cadence

| Day | Subreddit | Why |
|---|---|---|
| Day 0 (Tue) | r/opensource | Reach developers first; HN-style audience |
| Day +4 (Sat) | r/sideproject | Story-driven; weekend readers |
| Day +8 (Wed) | r/programming | Technical audience; needs spacing from r/opensource |
| Day +12 (Sun) | r/ChatGPT or r/LocalLLaMA | LLM-specific audience; longest cooldown |
