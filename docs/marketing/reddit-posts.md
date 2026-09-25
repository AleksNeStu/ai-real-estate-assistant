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
last year and just hit v5.1 with multi-year property valuation and
neighborhood AI summaries.

The stack is intentionally boring:
- Backend: FastAPI + Python 3.12
- Frontend: Next.js 16 + React 19
- Vector store: ChromaDB (embedded mode for demo, scales to small VPS)
- Six LLM providers with automatic fallback chain
- MIT license

What makes it interesting technically:
- Hybrid semantic + keyword retrieval with MMR reranking (30-40%
  relevance lift in internal evals)
- Per-task and per-user LLM provider selection with priority cascade
- Environment-conditional lazy provider loading (stays under Render's
  512 MB free-tier cap without sacrificing full DX on a VPS)
- 9 languages with EU AI Act compliance labels built in

The codebase is open-core: the engine stays free, commercial features
live in the hosted tier ([propvectorai.com](https://propvectorai.com)).

Live demo (no signup): https://realestate-web-dz1y.onrender.com/

Architecture write-up if you want to skip the code:
[large-saas-overview.md](https://github.com/AleksNeStu/ai-real-estate-assistant/blob/dev/docs/architecture/large-saas-overview.md)

Happy to answer questions about RAG, ChromaDB tuning, or the multi-
provider routing logic.

---

## Post 2: r/sideproject (story-driven)

**Title:** Built a conversational AI property search over 6 months —
here's what I learned shipping it as a solo developer

**Body:**

Six months ago I started [AI Real Estate Assistant](https://github.com/AleksNeStu/ai-real-estate-assistant)
because every "AI for X" tool I tried for real estate either cost
$200/month or hallucinated square footage.

Today it's an open-source conversational property search platform with
~50k monthly demo visitors and a hosted SaaS tier ([propvectorai.com](https://propvectorai.com)).

Things I learned the hard way:

1. **Multi-provider LLM routing isn't optional.** When OpenAI rate-limits
   you at 2am on a Saturday and your entire demo dies, you learn fast.
   The fallback chain lives in
   `apps/api/models/provider_factory.py`.

2. **Render free tier + 512 MB is brutal.** Solved with environment-
   conditional lazy provider loading — only the active `DEFAULT_PROVIDER`
   is imported at startup; the rest load on first use. Full DX on a
   VPS, Render-friendly on free.

3. **9 languages took longer than the RAG pipeline.** Translation keys,
   locale-aware date / currency / number formatting, hreflang SEO,
   per-language LLM prompts. Worth it — DACH and LatAm markets are
   materially different from the English-first default.

4. **ChromaDB with MMR reranking was a 30-40% relevance lift.** Started
   with pure vector search; reranker changed everything. See
   `apps/api/vector_store/reranker.py`.

The most fun part: v5.1 added AI property valuation with a 10-year
forecast. Property detail pages show a neighborhood one-liner too.

Live demo: https://realestate-web-dz1y.onrender.com/

If you're working on a side project with LLM routing, RAG, or
multi-language UX, happy to share more code snippets in the comments.

---

## Post 3: r/programming (technical deep-dive)

**Title:** Lessons from building a RAG-powered property search with
ChromaDB and multi-provider LLM fallback

**Body:**

We just shipped v5.1 of [AI Real Estate Assistant](https://github.com/AleksNeStu/ai-real-estate-assistant)
and I want to share the architectural decisions that mattered.

**Hybrid retrieval is non-negotiable for property search.** Pure
vector search misses exact-match queries ("2-bedroom", "Kraków",
price ceilings under 500k). Pure keyword misses semantic intent
("family-friendly neighborhood near good schools"). ChromaDB with
MMR reranking gave us a 30-40% relevance lift in internal evals.

**Multi-provider LLM routing isn't a luxury.** Per-task priority
cascade in `apps/api/models/provider_factory.py`:
- chat → primary provider (configurable per-user)
- property valuation → premium model (e.g., Opus, Sonnet)
- neighborhood one-liner → cheap model (e.g., Haiku, DeepSeek)
- embeddings → dedicated embedding provider

When one provider rate-limits, the demo keeps working. This is the
difference between "AI demo" and "AI product."

**Environment-conditional lazy loading is the difference between
free-tier Render and a $50/month VPS.** On Render (512 MB cap), only
the active `DEFAULT_PROVIDER` is imported at startup. On a VPS, all
13 providers load eagerly. One code path, two memory profiles.

**LangChain vs raw SDKs.** We started with LangChain for tools,
switched to raw `openai` / `anthropic` SDKs for production. The
abstraction cost wasn't worth it for our use case.

Architecture docs: [large-saas-overview.md](https://github.com/AleksNeStu/ai-real-estate-assistant/blob/dev/docs/architecture/large-saas-overview.md)

What's your take on hybrid retrieval vs pure vector for property-style
queries? Curious about other RAG stacks in production.

---

## Post 4: r/ChatGPT or r/LocalLLaMA (LLM-architecture angle)

**Title:** How we route 6 LLM providers (OpenAI, Anthropic, Google,
Grok, DeepSeek, Ollama) in a self-hostable property search demo

**Body:**

Sharing the LLM routing logic from
[AI Real Estate Assistant](https://github.com/AleksNeStu/ai-real-estate-assistant)
— an open-source conversational property search platform with v5.1
shipping property valuation and neighborhood AI summaries.

The trick: per-task priority cascade, not just a single
`DEFAULT_PROVIDER`.

```
CHAT                → configurable (default: GPT-4o-mini or local Ollama)
PROPERTY_VALUATION  → premium (Opus, Sonnet, GPT-4o)
NEIGHBORHOOD_SUMMARY→ cheap (Haiku, DeepSeek-Chat, local Qwen)
EMBEDDINGS          → dedicated embedding model (text-embedding-3-small
                      or local bge-small)
```

When OpenAI rate-limits during a Saturday demo, Anthropic picks up the
chat. When Anthropic has an outage, Google picks up. Local Ollama is
the always-on fallback for chat and embeddings.

The provider factory (`apps/api/models/provider_factory.py`) returns
a `(provider_name, model_name)` tuple per task. Lazy import on Render
free tier (stays under 512 MB), eager import on VPS.

What surprised me:
- **DeepSeek-Chat is shockingly good for cheap tasks** — neighborhood
  summaries and short chat responses land within 5-10% of Claude
  Haiku at 1/10th the cost.
- **Local Ollama is a real fallback, not a gimmick.** Qwen2.5-7B-Instruct
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