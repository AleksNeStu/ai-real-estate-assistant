# Marketing — Drafts Index

> **Audience:** Operator (AleksNeStu). All drafts ready for review and
> manual publishing per Rule 1 (no agent-side publishing).
> **Phase:** C of the growth plan.

---

## Drafts

| File | Purpose | Channel | Cadence |
|---|---|---|---|
| [show-hn.md](./show-hn.md) | Show HN post + first comment + day-of checklist | Hacker News | Tue/Wed 8-10am UTC |
| [reddit-posts.md](./reddit-posts.md) | 4 calibrated posts (r/opensource, r/sideproject, r/programming, r/ChatGPT or r/LocalLLaMA) | Reddit | One subreddit every 3-5 days |
| [product-hunt.md](./product-hunt.md) | Tagline, description, maker-comment, asset checklist, day-of checklist | Product Hunt | Tue/Wed 12:01am PT |
| [youtube-script.md](./youtube-script.md) | 90s hero, 5min architecture deep-dive, 30s vertical; shot list | YouTube + TikTok + Shorts | Sequential over 30 days |
| [directory-submissions.md](./directory-submissions.md) | Tier 1-4 directory list with copy templates, etiquette, tracking | There's An AI For That, FutureTools, AIcyclopedia, BetaList, awesome-* PRs | One per day |

---

## Recommended launch sequence

```
Day 0  (Tue/Wed) → Show HN (HN peak hours UTC)
Day +3           → There's An AI For That
Day +5           → FutureTools.io
Day +7           → AIcyclopedia
Day +8           → r/opensource (Reddit)
Day +10          → BetaList
Day +12          → r/sideproject (Reddit)
Day +14          → 5min YouTube architecture deep-dive
Day +16          → r/programming (Reddit)
Day +20          → r/ChatGPT or r/LocalLLaMA
Day +21          → 90s YouTube hero + TikTok + Shorts cross-post
Day +30          → Product Hunt (after audiences warmed up)
```

**Why this order:**
- Show HN first because HN drives the highest-quality developer traffic
  and the fastest signal on whether the demo holds up.
- Directory submissions in parallel — they're slow but cumulative SEO.
- Reddit posts spread out to avoid cross-subreddit flagging.
- YouTube hero + shorts ready by Day +14, deep-dive on Day +14.
- Product Hunt last — momentum from HN + Reddit + YouTube + directories
  compounds. PH algorithm rewards first-4-hour engagement, easier to
  drive when you already have an audience.

---

## Pre-launch blockers (resolve before Day 0)

- [x] The current `dev` branch is published to
      `AleksNeStu/ai-real-estate-assistant` (and to the two private mirrors)
- [x] The images are rebuilt and the demo stack is redeployed, so the live
      site carries the lead capture (footer email form) and the lead-redaction
      fix. **Until that happens the demo still exposes every captured lead's
      name, email and phone number to an anonymous visitor.**
- [ ] Live demo: tour appears on first visit, dismissable
- [ ] Live demo: try-these chips appear on landing, navigate to /search
- [ ] Live demo: the footer email field posts and the lead appears in
      `/leads` — masked for the anonymous viewer
- [ ] og:image renders in Twitter Card Validator
- [ ] Lighthouse SEO ≥ 95 on demo URL
- [ ] Lighthouse Performance ≥ 85 on demo URL
- [x] The social-preview card is a designed 1200×630 card (it was a cropped
      screenshot of the application)

## The demo is deliberately not indexed

The product is not finished, and it is not being released in this state. The
demo deployment therefore answers `X-Robots-Tag: noindex, nofollow` on every
page and serves a `robots.txt` that disallows everything, so the site stays
reachable for a test but stays out of the index — the drafts can link to it
without the unfinished pages entering a search index.

**Before the first post, decide:** either keep it that way, or release it (see
the release step in the deployment notes). If the demo is released, the
`SEARCH_INDEXING` flag comes off and the product's own `robots.txt` comes back
with the image.

## During-launch blockers (resolve during each post)

- [ ] Stay online 2-3 hours after Show HN
- [ ] Day-of PH launch: notify 5-10 colleagues for first-4-hour upvotes
- [ ] After each approval: add directory link to README + tracking sheet

---

## Tracking

Each draft file contains:
- Asset checklists
- Day-of checklists
- Reply templates for common comments
- Posting cadence
- Tracking sheet (for directories)

Update `directory-submissions.md`'s tracking sheet as submissions go
live. Cross-link approvals back to the README's Project Growth
section.

---

## Out of scope (intentional, deferred)

- Marketing site at `marketing.ai-real-estate-assistant.com` (separate
  Next.js project)
- Paid acquisition (per Rule 285 GTM Artefact Floor — manifest,
  pricing, financial-plan must exist first; tracked in `propvectorai`
  product, not this repo)
- Newsletter / email sequence (separate `nest-email-sequence` skill
  applies; out of session scope)
- Localization of marketing drafts into Polish / Russian / German
  (drafts are English-first; operator can translate before posting)
