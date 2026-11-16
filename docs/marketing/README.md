# Marketing — Drafts Index

> **Audience:** Operator (AleksNeStu). All drafts ready for review and
> manual publishing per Rule 1 (no agent-side publishing).
> **Phase:** C of the growth plan.

---

## The house style

| File | Purpose |
|---|---|
| [materials.md](./materials.md) | The rule that every published material is **dark**, how the screenshots are made, and how the copy is written |

---

## Drafts

| File | Purpose | Channel | Cadence |
|---|---|---|---|
| [show-hn.md](./show-hn.md) | Show HN post + first comment + day-of checklist | Hacker News | Tue/Wed 8-10am UTC |
| [reddit-posts.md](./reddit-posts.md) | 4 calibrated posts (r/opensource, r/sideproject, r/programming, r/ChatGPT or r/LocalLLaMA) | Reddit | One subreddit every 3-5 days |
| [product-hunt.md](./product-hunt.md) | Tagline, description, maker-comment, asset checklist, day-of checklist | Product Hunt | Tue/Wed 12:01am PT |
| [youtube-script.md](./youtube-script.md) | 90s hero, 8min architecture deep-dive, 30s vertical; shot list | YouTube + TikTok + Shorts | Sequential over 30 days |
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
Day +14          → 8min YouTube architecture deep-dive
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
- [x] Live demo: tour appears on first visit, dismissable — checked 2026-11-08.
      `components/onboarding/Tour.tsx` shows five steps 1.5 s after mount and
      skips itself when `onboarding-tour-dismissed-v1` is set in localStorage;
      Skip and Done both dismiss it.
- [x] Live demo: try-these chips appear on landing, navigate to /search —
      checked 2026-11-08 in the browser: six chips on `/en`, each one linking
      to `/en/search?q=...`.
- [x] Live demo: the footer email field posts and the lead appears in
      `/leads` — masked for the anonymous viewer — checked 2026-11-08:
      `POST /api/v1/leads/visitor` answers 201, and the lead is listed in
      `/api/v1/leads` as `p***@invalid.example` with the name and the phone
      number masked as well.
- [x] Live demo: the capture still works — re-checked 2026-11-11:
      `POST /api/v1/leads/visitor` answers 201 and the row carries the
      address, the source, the consent and both timestamps.
- [x] Live demo: the demo can be signed into with Google — checked
      2026-11-16: `GET /api/v1/capabilities` answers `auth.jwt_enabled: true`
      and `auth.oauth.google: true`, `/en/auth/login` renders the Google
      button, and the anonymous path is still open (`demo_user_bypass:
      false`, so an anonymous visitor is not handed a synthetic user).
- [x] Live demo: the buyer memory is in the running build — the deployment
      serves `111441521c4f73eaabc2bf638d2f6e25136742f9`, and that commit
      carries the memory commits (`apps/api/services/buyer_memory_service.py`,
      the extractor, the steering and the filters). A signed-in buyer's
      budget, ruled-out areas and disliked listings survive a turn and shape
      the next one; an anonymous request reads and writes none.
- [ ] **The demo sends no e-mail, and that is what the form says.**
      `GET /api/v1/capabilities` answers `email.enabled: false`,
      `lead_capture.waitlist_enabled: false` — the deployment has no mail
      sender, so the waitlist form says "noted, no e-mail" instead of
      promising a subscription it cannot keep. The interest is recorded in the
      database and is visible on the board (`/[locale]/leads`, signed-in);
      **nobody is notified when it arrives.** The alert type for it
      (`HIGH_VALUE_LEAD`) and its template exist, but nothing produces them,
      and SMTP is unset on the node. Until that is wired, a launch has to be
      followed by a human reading the board — the email cannot be the
      mechanism that tells you a launch worked.
- [x] og:image renders in Twitter Card Validator — checked 2026-11-08:
      `https://realty.kittray.com/og-image.png` answers 200 with a PNG of
      1200×630.
- [ ] Lighthouse SEO ≥ 95 on demo URL — **not reachable while the demo stays
      `noindex`**. Measured 2026-11-08 with Lighthouse 12.6.1 against the live
      demo: SEO 63 on `/en` and on `/en/search`, and the only failing SEO
      audit is `is-crawlable` ("Page is blocked from indexing"). Every other
      SEO audit passes, so releasing the demo (see the note below) turns this
      into 100. The CI gate on the built application is stricter still
      (performance ≥ 0.9, accessibility ≥ 0.9, LCP ≤ 2500 ms, TBT ≤ 300 ms).
- [x] Lighthouse Performance ≥ 85 on demo URL — measured 2026-11-08 against
      the live demo: 87 on `/en` (83 on `/en/search`). The remaining cost is
      total blocking time (440 ms on `/en`), which the demo pays for hosting
      outside the city.
- [x] The social-preview card is a designed image (it was a cropped
      screenshot of the application) — `.github/social-preview.png`,
      1280×640, which is GitHub's own social-preview canvas. The 1200×630
      image is a different asset: the Open Graph card at
      `apps/web/public/og-image.png`. Every number on the card was checked
      against the repository on 2026-11-08: 8,000+ tests (7,033 backend +
      1,309 frontend Jest, 182 Playwright end-to-end), 9 languages, 80%+
      coverage (85.1% backend over the union of the unit and integration
      suites, 85.2% frontend lines), and "WCAG 2.1 AA audited" — `ACCESSIBILITY.md`
      records the audit and its three known map-component limitations, so the
      card no longer claims a blanket "AA compliant".
- [x] The privileged viewer can see which build the demo is running — the
      commit, the build time and the deploy's run, in the footer
      (TaskMaster #73). The list lives in the repository's `ADMIN_EMAILS` /
      `ADMIN_IPS` variables and the deploy delivers it. Verified 2026-11-16:
      the live deployment answers `GET /api/v1/capabilities` with the build
      block — the commit, the build time and the run — for a privileged
      caller, and without it for anyone else. The demo runs that same
      commit, so the stamp is true of what the visitor is talking to.

## What changed since the drafts were written (2026-11-09 → 2026-11-16)

The five drafts were written against the deployment of 2026-11-09 and are
re-verified against the deployment of 2026-11-16 (the v5.3.9 build). Three
things moved, and every draft now carries the new truth:

1. **The demo can be signed into with Google** (`v5.3.4`). The drafts used
   to promise *"no signup"*; the honest claim is narrower — browsing needs
   no account, and signing in switches on the buyer memory.
2. **The buyer memory shipped** (`v5.3.x`, in `dev` and in the running
   build). It was in none of the drafts. It is now the headline in all
   five, because it is the thing a competitor's demo cannot copy in a
   weekend.
3. **The launch URL is `/en`.** The bare root 307-redirects to `/pl`, so an
   English-language audience was landing on a Polish page. Every link in
   every draft now carries the English path.

Also corrected, because they would not survive a reader checking them:
`v5.1.17` → the current `v5.3.9`; *"the demo uses simulated AI
responses"* → the demo answers with a real provider; *"16 supported
providers"* → 17; *"9 languages with EU AI Act compliance labels"* → nine
locales ship, English and Polish are maintained, the rest fall back to
English; and the *"~50k monthly demo visitors"* in the r/sideproject draft
→ the measured 262 unique visitors in a fortnight.

## The demo is deliberately not indexed

The product is not finished, and it is not being released in this state. The
demo deployment therefore answers `X-Robots-Tag: noindex, nofollow` on every
page and serves a `robots.txt` that disallows everything, so the site stays
reachable for a test but stays out of the index — the drafts can link to it
without the unfinished pages entering a search index.

**Before the first post, decide:** either keep it that way, or release it (see
the release step in the deployment notes). If the demo is released,
`SEARCH_INDEXING` is unset in the deployment environment (it is `false` today,
and `apps/web/src/lib/indexing.ts` only adds the header when it is exactly
`false`), and the product's own `robots.txt` comes back with the image.

## Where the audience actually comes from (measured 2026-11-15)

| Metric | Value |
|--------|-------|
| Stars | 323 (+7 in the last 30 days — 0.23 a day) |
| Forks | 119 |
| Open pull requests | 0 |
| Unique visitors, last 14 days | 262 |
| Views, last 14 days | 786 |
| Top referrers | github.com (81 unique), aocr.org (64), Google (20) |

The 10-stars-a-day target of the first wave is 43 times the current rate. At
today's traffic — 262 unique visitors in a fortnight, 7 stars over 30 days,
a 1.2 % conversion — reaching it means roughly 800 unique visitors a day at
the same conversion, or a channel of a different kind (Hacker News, Product
Hunt, a directory that converts). The full traffic snapshot lives in
`docs/community/metrics/2026-W47.md`; the repository numbers were re-read
from the stargazer edges on 2026-11-15, the traffic figures are from the W47
collection.

**The organic column is noise.** The demo is deliberately `noindex`, so the
Google traffic is a page that is not in the index. Releasing it is an operator
decision (see `docs/community/SEO_INDEXING_SETUP.md`), and it is the one lever
that does not depend on publishing anything.

## During-launch blockers (resolve during each post)

- [ ] Stay online 2-3 hours after Show HN
- [ ] Day-of PH launch: notify 5-10 colleagues for first-4-hour upvotes
- [ ] After each approval: add directory link to README + tracking sheet
- [ ] Before the first post: every draft points at the demo, so check that it
      answers, that the landing renders, and that the build stamp in the
      footer is the build you expect (TaskMaster #73)

## What went out on 2026-11-16, and what is still open

**Gone out**

- **LinkedIn** — the release announcement is published on Aleksandr Nesterovich's
  LinkedIn (the account the automation browser holds), carrying the demo and the
  repository links and nothing but the verified facts.
- **BetaList** — the submission is drafted through BetaList's own agent API
  (`https://betalist.com/agent`), which needs no account: the icon and three dark
  screenshots are attached and the API reports no warnings. It sits **unclaimed**,
  and the claim link is in the repository's gitignored `.env.local`
  (`BETALIST_CLAIM_URL`). The founder opens it, identifies with an e-mail, edits
  the text, picks a plan and pays — the agent never pays (Rule 252).

**Still open, and why**

- **Hacker News — refused by the platform, not by the draft.** The account
  `aleksnestu` exists (created for this launch; the credentials are in the
  gitignored `.env.local`), but the submission came back with HN's own notice:
  *"We're temporarily restricting Show HNs because of a massive influx, mostly by
  users who aren't yet familiar with the site or its culture... Take some time to
  get to know the community, become a good contributor, and then it will be fine
  to post an occasional Show HN."* The post is ready; the window is closed to a
  new account. The account stays for the day it opens.
- **There's An AI For That, FutureTools, AIcyclopedia** — the forms are reachable
  (the AI one at `/launch`, FutureTools at `/submit-a-tool`, AIcyclopedia at
  `/submit-your-ai-tool`, which answers 403 from this network although the
  site's own navigation links there), and the per-directory copy is in
  [directory-submissions.md](./directory-submissions.md). FutureTools accepts a
  submission without an account; the agent's pass did not get its React form to
  accept the values, so that one is a human click.
- **Reddit** — the four posts are written. Each subreddit's own rule expects the
  account to have some history, and a brand-new account posting the project's own
  launch is what the moderators remove. The posts wait for the operator's account.
- **Product Hunt** — the tagline, the description and the maker comment are
  ready; the launch needs a maker account and a Tue/Wed slot.
- **YouTube** — the scripts and the shot list are ready; the recording needs a
  channel.

---

## Tracking

Each draft file contains:
- Asset checklists
- Day-of checklists
- Reply templates for common comments
- Posting cadence
- Tracking sheet (for directories)

Update `directory-submissions.md`'s tracking sheet as submissions go
live. Cross-link approvals back to the README's "Ideas, forks, and other
ways to work with us" section — that is the repository's community-facing
list, and it is the only one it has.

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
