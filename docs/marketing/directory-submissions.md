# Directory Submissions — Plan + Templates

> **Status:** Draft. Operator to submit manually per Rule 1.
> **Cadence:** One submission per day. Don't batch — directory editors
> notice bulk submissions and reject as spam.

---

## Tier 1 — Submit first (high-impact, AI-focused)

### There's An AI For That (theresanaiforthat.com)

- **URL:** https://theresanaiforthat.com/submit
- **Priority:** ⭐⭐⭐ (primary AI directory, SEO authority)
- **Cadence:** Submit Day +3 (after Show HN settles)
- **Eligibility:** Open to all AI tools
- **Review time:** 1-7 days

**Submission template:**

```
Name: AI Real Estate Assistant
Tagline (≤ 100 chars): Conversational AI for property search —
open-source, self-hostable, MIT
Category: Real Estate
Pricing: Free (open-source) | Paid hosted tier (propvectorai.com)
URL: https://realestate-web-dz1y.onrender.com/
GitHub: https://github.com/AleksNeStu/ai-real-estate-assistant
Description: Open-source conversational AI for property search. Ask in
natural language ("2-bedroom apartment in Kraków under 500k") and get
matched listings. Built with FastAPI + Next.js 16 + ChromaDB. Six LLM
providers with automatic fallback chain. 9 languages. MIT-licensed.
```

### FutureTools.io (futuretools.io)

- **URL:** https://www.futuretools.io/submit-a-tool
- **Priority:** ⭐⭐⭐ (high-traffic AI directory)
- **Cadence:** Submit Day +5
- **Eligibility:** Open to all AI tools
- **Review time:** 3-14 days

**Submission template:**

```
Tool name: AI Real Estate Assistant
URL: https://realestate-web-dz1y.onrender.com/
GitHub: https://github.com/AleksNeStu/ai-real-estate-assistant
Category: AI Agents / Real Estate
Pricing: Free (open-source) | Paid (hosted tier)
Description: Open-source conversational AI for property search, analytics,
and market insights. Natural language queries with automatic filter
extraction. Hybrid semantic + keyword retrieval. Multi-provider LLM
fallback. 9 languages. MIT-licensed.
```

### AIcyclopedia (aicyclopedia.com)

- **URL:** https://aicyclopedia.com/submit
- **Priority:** ⭐⭐ (growing directory, niche AI focus)
- **Cadence:** Submit Day +7
- **Eligibility:** Open
- **Review time:** 3-10 days

**Submission template:**

```
Tool: AI Real Estate Assistant
URL: https://realestate-web-dz1y.onrender.com/
Category: Real Estate / Property Tech
Short description: Conversational AI property search with natural
language queries. Open-source, MIT-licensed, self-hostable.
Tags: real-estate, AI, open-source, FastAPI, Next.js, ChromaDB,
  multi-language, property-search
```

---

## Tier 2 — Submit next (broader reach)

### Product Hunt (producthunt.com)

- **URL:** https://www.producthunt.com/posts/new
- **Priority:** ⭐⭐⭐ (highest single-day traffic source)
- **Cadence:** Tue/Wed, 12:01am PT (see `product-hunt.md`)
- **Eligibility:** Open
- **Review time:** Same-day launch

See `product-hunt.md` for full draft.

### BetaList (betalist.com)

- **URL:** https://betalist.com/submit
- **Priority:** ⭐⭐ (early-adopter audience)
- **Cadence:** Submit Day +10
- **Eligibility:** Open to all startups
- **Review time:** 1-2 weeks

**Submission template:**

```
Startup name: AI Real Estate Assistant
URL: https://realestate-web-dz1y.onrender.com/
Tagline: Conversational AI property search — open-source, MIT-licensed
Description: Open-source conversational AI platform for property
search, analytics, and market insights. Built with FastAPI + Next.js
16 + ChromaDB. Multi-provider LLM fallback chain. 9 languages.
Founders: AleksNeStu (solo developer)
```

### Hacker News — Show HN (news.ycombinator.com)

- **URL:** https://news.ycombinator.com/show
- **Priority:** ⭐⭐⭐ (highest-quality developer audience)
- **Cadence:** Tue/Wed 8-10am UTC
- **Eligibility:** Open
- **Review time:** Real-time (HN front page ranking)

See `show-hn.md` for full draft.

---

## Tier 3 — Open-source focused (low priority but signals)

### GitHub Topics Boosters

- [awesome-open-source-ai](https://github.com/topics/awesome-list) — submit via PR
- [awesome-real-estate](https://github.com/topics/awesome-list) — submit via PR
- [FastAPI Awesome](https://github.com/tiangolo/awesome-fastapi) — submit via PR
- [Next.js Examples](https://github.com/vercel/next.js/tree/canary/examples) — submit via PR

**Template for PR submission to awesome-* lists:**

```
## AI Real Estate Assistant

[AI Real Estate Assistant](https://github.com/AleksNeStu/ai-real-estate-assistant)
is an open-source conversational AI platform for property search,
analytics, and market insights. Built with FastAPI + Next.js 16 +
ChromaDB. Multi-provider LLM routing with automatic fallback chain.
9 languages with EU AI Act compliance labels. MIT-licensed.
- Live demo: https://realestate-web-dz1y.onrender.com/
- Architecture: https://github.com/AleksNeStu/ai-real-estate-assistant/blob/dev/docs/architecture/large-saas-overview.md
```

---

## Tier 4 — Skip / low value

| Directory | Skip reason |
|---|---|
| OpenAI GPT Store | Requires hosted-only product (we have demo + hosted). Could qualify via PropVector AI; not via the open-source repo. |
| AI Tool Tracker | Aggregator, low direct traffic. |
| Toolify | Aggregator, low SEO value. |
| There's An AI For That (Tier 2 submission) | Already in Tier 1. |

---

## Tracking sheet (operator's local task list)

| Directory | Submitted | Approved | Live URL | Notes |
|---|---|---|---|---|
| There's An AI For That | _ | _ | _ | |
| FutureTools.io | _ | _ | _ | |
| AIcyclopedia | _ | _ | _ | |
| Product Hunt | _ | _ | _ | See product-hunt.md |
| BetaList | _ | _ | _ | |
| Show HN | _ | _ | _ | See show-hn.md |
| awesome-open-source-ai | _ | _ | _ | PR pending |
| awesome-real-estate | _ | _ | _ | PR pending |
| FastAPI Awesome | _ | _ | _ | PR pending |
| Next.js Examples | _ | _ | _ | PR pending |

## Submission etiquette

- One submission per directory per day (don't batch)
- Read each directory's submission guidelines before submitting
- Use the templates above; don't rewrite per directory (saves time)
- Reply politely to any rejection emails — editors remember polite submitters
- If rejected: ask why, fix, resubmit 30 days later

## After each approval

- [ ] Add directory link to README's Project Growth section
- [ ] Add directory badge to og-image (if high-value)
- [ ] Track in the sheet above (Submitted → Approved → Live URL)
- [ ] Note any learnings (e.g., "AIcyclopedia wanted 3 screenshots, not 1")