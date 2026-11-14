# Reddit Posts — Drafts

> **Status:** Drafts. Operator to publish manually per Rule 1.
> **Calendar:** Space posts 3-5 days apart to avoid cross-subreddit
> flagging as spam. Lead with `r/opensource`, end with `r/programming`.

---

## Post 1: r/opensource (lead)

**Title:** I built an open-source conversational AI property search
because Zillow's API died years ago and I'm tired of filter-first portals

**Body:**

I shipped [AI Real Estate Assistant](https://github.com/AleksNeStu/ai-real-estate-assistant)
two years ago and just hit v5.3.5 with multi-year property valuation,
neighborhood AI summaries, and a buyer memory that learns what you told it.

The stack is intentionally boring:
- Backend: FastAPI + Python 3.12
- Frontend: Next.js 16 + React 19
- Vector store: ChromaDB (embedded mode for demo, scales to small VPS)
- 17 LLM providers with automatic fallback chain
- MIT license

What makes it interesting technically:
- A buyer memory: every turn, the same model that answered the turn reads
  the conversation back and writes down what it learned — a budget, an area
  ruled out, a listing liked or disliked — into a per-buyer table. The next
  search reads that table back, and a ruled-out area or a disliked listing
  is filtered out of the results rather than down-ranked.
- Hybrid semantic + keyword retrieval with MMR reranking
- Per-task and per-user LLM provider selection with priority cascade
- Environment-conditional lazy provider loading (a memory-capped host
  imports one provider at startup; a VPS imports all 17)
- UI in 9 languages — English and Polish maintained, the rest fall back to
  English

The codebase is open-core: the engine stays free, and the hosted tier
sells the live data feeds, running it for you, and the enterprise pieces
([propvectorai.com](https://propvectorai.com)).

Live demo: https://realty.kittray.com/en
Browsing needs no account; sign in with Google to switch on the memory.

Architecture write-up if you want to skip the code:
[large-saas-overview.md](https://github.com/AleksNeStu/ai-real-estate-assistant/blob/dev/docs/architecture/large-saas-overview.md)

Happy to answer questions about RAG, ChromaDB tuning, or the multi-
provider routing logic.

---

## Post 2: r/sideproject (story-driven)

**Title:** Built a conversational AI property search over two years —
here's what I learned shipping it as a solo developer

**Body:**

Two years ago I started [AI Real Estate Assistant](https://github.com/AleksNeStu/ai-real-estate-assistant)
because every "AI for X" tool I tried for real estate either cost
$200/month or hallucinated square footage.

Today it's an open-source conversational property search platform with a
hosted SaaS tier ([propvectorai.com](https://propvectorai.com)). The demo
gets a few hundred unique visitors a fortnight — small, but the traffic that
arrives is developers, which is the point.

Things I learned the hard way:

1. **Multi-provider LLM routing isn't optional.** When OpenAI rate-limits
   you at 2am on a Saturday and your entire demo dies, you learn fast.
   The fallback chain lives in
   `apps/api/models/provider_factory.py`.

2. **512 MB of RAM is brutal.** Solved with environment-conditional
   lazy provider loading — on a memory-capped host only the active
   `DEFAULT_PROVIDER` is imported at startup, the rest load on first use;
   everywhere else all 17 load eagerly, so local dev and CI behave
   exactly as they always did. Full DX on a VPS, and the demo still fits
   on a small host.

3. **9 languages took longer than the RAG pipeline.** Translation keys,
   locale-aware date / currency / number formatting, hreflang SEO,
   per-language LLM prompts. Worth it — DACH and LatAm markets are
   materially different from the English-first default. Today the interface
   ships in 9 locales, with English and Polish maintained and the other
   seven frozen, falling back to English rather than rotting.

4. **ChromaDB with MMR reranking changed the result set.** Started
   with pure vector search; reranker changed everything. See
   `apps/api/vector_store/reranker.py`.

5. **Making the assistant remember is harder than making it answer.** The
   extraction is one model call per turn, and it has to share the model that
   answered the turn — a second provider would mean a second bill and a
   second thing to fail. The part that surprised me: a disliked listing and
   a ruled-out area are *filters*, not down-ranked results. Ranking a
   rejected listing lower still shows it; removing it is what the buyer
   actually asked for.

The most fun part: v5.2 added AI property valuation with a 10-year
forecast, and the current build added the buyer memory. Property detail
pages show a neighborhood one-liner too.

Live demo: https://realty.kittray.com/en

If you're working on a side project with LLM routing, RAG, or
multi-language UX, happy to share more code snippets in the comments.

---

## Post 3: r/programming (technical deep-dive)

**Title:** Lessons from building a RAG-powered property search with
ChromaDB and multi-provider LLM fallback

**Body:**

We just shipped v5.3 of [AI Real Estate Assistant](https://github.com/AleksNeStu/ai-real-estate-assistant)
and I want to share the architectural decisions that mattered.

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

**Multi-provider LLM routing isn't a luxury.** Per-task priority
cascade in `apps/api/models/provider_factory.py`, with the default
per-task model a free one (`SYSTEM_DEFAULTS` in
`apps/api/services/model_preference_service.py`):
- chat → the primary provider (configurable per-user)
- search / tools / analysis → the same default, a free model
- embeddings → a dedicated embedding provider

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
Grok, DeepSeek, Ollama) in a self-hostable property search demo

**Body:**

Sharing the LLM routing logic from
[AI Real Estate Assistant](https://github.com/AleksNeStu/ai-real-estate-assistant)
— an open-source conversational property search platform, v5.3, shipping
property valuation, neighborhood AI summaries and a buyer memory.

The trick: per-task priority cascade, not just a single
`DEFAULT_PROVIDER`.

```
CHAT          → configurable (default: the deployment's provider)
SEARCH        → the default per-task model — a free one
TOOLS         → the default per-task model — a free one
ANALYSIS      → the default per-task model — a free one
EMBEDDINGS    → a dedicated embedding provider
```

The deployed chain for an anonymous visitor is MiniMax → Ollama (local,
on the server) → OpenRouter's free models, so an outage upstream costs
the demo nothing.

When the primary provider rate-limits during a Saturday demo, the next
one in the chain picks up the chat. When that one has an outage, the
third does. Local Ollama is the always-on fallback for chat and
embeddings.

The provider factory (`apps/api/models/provider_factory.py`) returns
a `(provider_name, model_name)` tuple per task. Lazy import on a
memory-constrained host, eager import on a VPS and in local dev.

What surprised me:
- **A free model as the default per-task model is not a compromise** —
  the search and tool paths carry the structured work, and a free model
  handles them. The expensive model is the one that writes prose.
- **Local Ollama is a real fallback, not a gimmick.** A 7B instruct model
  handles chat and neighborhood summaries surprisingly well. Property
  valuation is too nuanced for it though.
- **Embeddings via local bge-small are fine for demo, but production
  wants text-embedding-3-small.** Retrieval quality matters more than
  inference cost for embeddings.

Full code:
[apps/api/models/provider_factory.py](https://github.com/AleksNeStu/ai-real-estate-assistant/blob/dev/apps/api/models/provider_factory.py)

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
