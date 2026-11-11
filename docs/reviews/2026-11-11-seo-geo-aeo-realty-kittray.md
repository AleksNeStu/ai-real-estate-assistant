# SEO / AEO / GEO audit — realty.kittray.com

**Date:** 2026-11-11 · **Target:** `https://realty.kittray.com` (the public demo of
`AleksNeStu/ai-real-estate-assistant`) · **Task:** TaskMaster #74 · **Method:** live
requests against the deployed domain + a read of the repository's own SEO surface.

> **The demo is deliberately `noindex`.** Every finding below is about a domain that
> answers `X-Robots-Tag: noindex, nofollow` and serves a Disallow-all `robots.txt`.
> That is the operator's decision (Rule 306 gate 4) and it is correct while the product
> is unfinished. This audit therefore prepares the surface and leaves the switch to the
> operator — see "The switch" at the end.

---

## 1. What was measured

Live requests, 2026-11-11 21:30–22:20 UTC, against the running deployment
(`build.sha = e4bafb25e`, tag `v5.3.1`):

| Probe | Result |
|---|---|
| `GET /en` | 200 · `x-robots-tag: noindex, nofollow` · `cache-control: private, no-cache, no-store, max-age=0, must-revalidate` |
| `GET /en/search` | 200 · same headers |
| `GET /en/property/prop-0166` | 200 · **no `<h1>` in the HTML** — the page is a client-rendered shell |
| `GET /robots.txt` | 200 · the deployment's Disallow-all override (the image's own file is allow-all) |
| `GET /sitemap.xml` | 200 · 144 URLs = 9 locales × 16 routes · **no listing pages** |
| `GET /llms.txt` | 200 · a static document, no routes, no catalogue |
| `GET /api/v1/capabilities` | 200 · `llm.provider = minimax`, `lead_capture.waitlist_enabled = false` |
| `POST /api/v1/analytics/outbound` | 204 — the outbound click is recorded |
| `POST /api/v1/leads/visitor` | 201 — a lead is captured (`source: organic`, `consent_given: false`) |
| LHCI (CI run `43103039957`, job `lighthouse`) | passed — `/en/search` and `/en/chat` against the budgets in `apps/web/lighthouserc.js` |

**The budgets the CI enforces** (`apps/web/lighthouserc.js`): performance ≥ 0.9,
accessibility ≥ 0.9, best-practices ≥ 0.9 *(warning)*, **SEO ≥ 0.8 *(warning)***, FCP
≤ 2000 ms, LCP ≤ 2500 ms, CLS ≤ 0.1, TBT ≤ 300 ms, Speed Index ≤ 3000 ms. The SEO
category is only a warning — and the demo's own marketing page measured **63** on
2026-11-11 (`docs/marketing/README.md`), the single failing audit being
`is-crawlable` (the noindex). Every other SEO audit passed.

---

## 2. The gaps, with the evidence

### G1 — Fourteen routes shared one title and one description *(fixed)*

Every public route except `/showcase` inherited the locale layout's title
("AI Real Estate Assistant") and description ("Next-gen real estate search and
analytics"). Measured across all 17 English routes:

```
/            200  AI Real Estate Assistant  Next-gen real estate search and analytics  canonical: NO
/search      200  AI Real Estate Assistant  Next-gen real estate search and analytics  canonical: NO
/chat        200  AI Real Estate Assistant  Next-gen real estate search and analytics  canonical: NO
/market-trends … /valuation … /cma … /documents … /analytics … /leads … /usage
             200  AI Real Estate Assistant  Next-gen real estate search and analytics  canonical: NO
/showcase    200  Showcase — Forks & Built With  Forks, real-world deployments…      canonical: yes
/property/prop-0166
             200  AI Real Estate Assistant  Next-gen real estate search and analytics  canonical: NO
```

Fourteen pages claiming to be about the same thing, and one page (`/showcase`)
proving the codebase already had the answer: a route that declares its own
metadata.

The copy was already in the repository — `messages/*.json` carries a `pages`
namespace with a title and a description per route, in nine languages. It was
never wired into the metadata.

### G2 — The hreflang cluster pointed at the internal origin *(fixed)*

Two hreflang clusters existed, and they disagreed:

* the page's own `<link rel="alternate">` — `https://realty.kittray.com/pl` ✔
* the HTTP `Link` header — `http://141.147.62.106.sslip.io:3100/pl` ✘

The header came from next-intl's middleware, which resolves its alternates
against the **request's** host — and behind the Cloudflare Worker the request's
host is the origin's internal name. A crawler that reads the HTTP `Link` header
(a supported hreflang source) therefore saw a second cluster on an address
nobody should see.

Both clusters also pointed at the **home pages** of every locale: the
`languageAlternates()` helper took no path, so `/en/market-trends` claimed the
nine home pages as its translations.

### G3 — The listing page was invisible to anything that does not run JavaScript *(fixed)*

`/en/property/{id}` is the page a buyer searches for ("two-room apartment in
Kraków, Old Town"). It was a client component that fetched the listing after
load: no `<h1>` in the HTML, no canonical, no structured data, no entry in the
sitemap. The repository had **no `schema.org/Property` anywhere**.

### G4 — The sitemap listed the account areas and no listings *(fixed)*

144 URLs: 9 locales × 16 routes, of which five (`/leads`, `/usage`, `/documents`,
`/analytics`, `/agent-analytics`) are behind the account gate — a sitemap is a
list of pages to index, and those pages cannot be fetched. And **not one
listing** was in it.

There was also no endpoint that could enumerate the catalogue: the properties
router had only `/properties/{id}`, `/related` and `/price-history`, so nothing
outside the backend process could name the listings.

### G5 — The waitlist promised an e-mail the deployment cannot send *(fixed)*

`lead_capture.waitlist_enabled` is `false` on the demo (no mail sender is
configured) and the form's idle line says so honestly ("the address is stored
on this deployment; no e-mail is sent from here"). The **success** line did
not: it answered "One e-mail at launch. Never sold, never shared." — the
promise, printed at the exact moment the visitor is most likely to believe it.

The lead itself is captured correctly (`POST /api/v1/leads/visitor` → 201, the
lead lands in the agent board with `source: organic`).

### G6 — The llms.txt could not name the instance *(fixed)*

`public/llms.txt` is a hand-written static file: 162 lines describing the
product well, but a static file cannot name the routes that are live or the
catalogue the deployment holds.

### G7 — The visible FAQ and the structured FAQ were different FAQs *(not changed)*

The landing page renders six questions (`landing.faq.q1..q6`); the site's
JSON-LD `FAQPage` carries eight (`seo.structuredData.faq.q1..q8`). They are
different sets, and they disagree about the number of LLM providers.

Left alone deliberately: the `FAQPage` block is site-wide (it lives in the
layout's `<head>`), while the visible FAQ belongs to the landing page. Aligning
them means either narrowing the JSON-LD to the landing page's six questions —
which loses the richer document on every other route — or adding the visible
FAQ to every route. This is a product-copy decision, not a technical one, and it
is listed under "Still open" below.

---

## 3. What was implemented

| # | Change | Where |
|---|---|---|
| 1 | The middleware's hreflang header is off; the page's own absolute cluster is the single source | `apps/web/src/i18n/routing.ts` (`alternateLinks: false`) |
| 2 | The hreflang cluster carries the **page's** path, so a route's translations are that route in every language | `apps/web/src/lib/metadata.ts` (`languageAlternates(path)`) |
| 3 | Ten public routes declare their own title, description, canonical and cluster, from the catalogue's existing `pages` copy | `apps/web/src/app/[locale]/{search,chat,market-trends,city-overview,agents,tools,knowledge,valuation,cma,analytics}/layout.tsx` |
| 4 | The landing page declares its own canonical and cluster | `apps/web/src/app/[locale]/page.tsx` (`generateMetadata`) |
| 5 | The listing page is a **server** component: the listing is read on the server, the page arrives with its content, its title and its canonical | `apps/web/src/app/[locale]/property/[id]/page.tsx` (+ `property-view.tsx`) |
| 6 | The listing page carries `schema.org/Property` (address, geo, rooms, floor size, year, offer) and a `BreadcrumbList` | `apps/web/src/lib/structured-data.ts` (`buildPropertyStructuredData`) |
| 7 | A public catalogue endpoint, so anything outside the backend can enumerate the listings | `GET /api/v1/properties` (`apps/api/api/routers/properties.py`) |
| 8 | The sitemap lists the public routes and the listings, one entry per page with its translation cluster | `apps/web/src/app/sitemap.ts` |
| 9 | llms.txt names the live routes, the languages and the catalogue of the running instance | `apps/web/src/app/llms.txt/route.ts` (+ `apps/web/src/lib/llms-txt.ts`) |
| 10 | The waitlist's success line matches what the deployment can keep | `apps/web/src/components/landing/waitlist-form.tsx` |

**The GTM doctrine this rests on** — GTM-21 ("search first if people search": the
listing pages are the queries people actually type) and GTM-22 ("SEO + GEO from
day one", with the llms.txt and the structured data as the GEO half). The
deviation is stated out loud: **the organic funnel stays switched off** until the
operator decides, because GTM-21's payoff needs indexing and the demo's own
state does not earn it yet. The measurement target stays the content wave's
(10/20/50 stars per day) — `docs/community/GROWTH_EXPERIMENTS.md`.

---

## 4. Still open

1. **The indexing decision (the operator's).** Two mechanisms, both runtime, both
   reversible without a rebuild: unset `SEARCH_INDEXING=false` in the frontend's
   environment, and drop the Disallow-all `robots.txt` mount over the image's own
   `public/robots.txt`. The procedure and the one-command revert are written up
   in `docs/community/SEO_INDEXING_SETUP.md`.
2. **The FAQ split** (G7) — a copy decision: one FAQ or two.
3. **The cache header.** Every page answers `private, no-cache, no-store` — the
   pages are rendered per request, so nothing is cached at the edge. It costs
   Core Web Vitals on a cold visitor and it is the reason the CI's LHCI numbers
   (measured against a local build) and the live numbers differ. Making the
   public pages cacheable is a rendering decision (static export vs. ISR), not a
   header change.
4. **The off-site citation stack.** The on-site GEO layer is in place; making
   the model engines *cite* the project rather than a competitor needs the
   off-site work (directories, Show HN, Reddit) that `docs/marketing/` already
   plans and that only the operator can publish under their own name
   (Rule 306 gate 4).
5. **The measurement.** The deployment's own metrics are the source: organic
   sessions and captured leads, per the targets in
   `docs/community/GROWTH_EXPERIMENTS.md`. While the demo is noindex, the
   organic column reads zero — that is the switch, not a failure.

---

## 5. The catalogue this deployment holds

Read from the deployment itself (`GET /api/v1/catalogue/stats`, 2026-11-11):

| | |
|---|---|
| listings | **250** |
| agents | 15 |
| cities | Wrocław 55 · Gdańsk 52 · Poznań 51 · Warsaw 47 · Kraków 45 |
| currency | PLN |

These are the numbers the sitemap and the llms.txt now carry, and they are the
numbers a claim about the catalogue may be made from: the deployment says
250, so the deployment says 250.

## 6. How the funnel is measured

The source is the deployment's own data, not an estimate:

* **the catalogue** — `GET /api/v1/catalogue/stats` (public): the listings, the
  cities, the agents.
* **the leads** — `POST /api/v1/leads/visitor` writes a lead with its source
  (`organic`, `referral`, `social`, …) and its consent; they are read in the
  agent board, behind an account.
* **the outbound clicks** — `POST /api/v1/analytics/outbound` (204) records
  the tagged click of a landing link, with its UTM.
* **the targets** — `docs/community/GROWTH_EXPERIMENTS.md`: the content wave's
  10/20/50 stars per day.

**The organic column reads zero today, and that is the switch, not a
failure.** The demo is noindex and its robots.txt disallows everything, so no
crawler can reach it. The first honest number after the operator flips the
switch is the one this audit is preparing for.

## 7. The live evidence of this audit

* The live demo answered `build.sha = e4bafb25e` (`v5.3.1`) throughout.
* A test lead was created by walking the public lead path: id
  `3b943296-427d-4925-8530-0a0eb2bc3422`, e-mail `seo.audit.check@example.com`,
  source `organic`. It can be deleted from the agent board.
* The LHCI budgets are in `apps/web/lighthouserc.js`; the run that passed them
  is CI `43103039957`, job `lighthouse`.
