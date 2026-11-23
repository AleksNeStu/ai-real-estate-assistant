# SEO Indexing Setup — Google Search Console & Bing Webmaster Tools

**Target:** `https://realty.kittray.com/`
**Scope:** Public procedure only. No tokens, API keys, or credentials anywhere in this guide.
**Evidence storage:** `docs/community/private-evidence/` (gitignored — never commit screenshots or exports).

> **The demo IS indexed now (2026-11-16).** The operator lifted the
> deliberate `noindex`: the deployment no longer sets `SEARCH_INDEXING=false`
> and no longer mounts a Disallow-all `robots.txt` over the product's own
> file, so the pages answer `200` with no `X-Robots-Tag`, and the product's
> own robots.txt — which explicitly invites the AI crawlers — is what a
> crawler reads. The switch and its undo are in §4.
>
> **The canonical host is `realty.kittray.com`.** The apex `kittray.com` is
> the operator's own domain and carries the index of what is on it
> (`kittray.com/` lists the subdomains); the product keeps its own address,
> and its canonical URLs, sitemap and `hreflang` cluster all name it. A
> `workers.dev` host cannot be verified as a search-console property, because
> verification needs a DNS record on a domain you control — `kittray.com` is
> that domain, so the property is the DOMAIN property
> `sc-domain:kittray.com`, which covers `realty.kittray.com` as well.
>
> **The property is verified and the account reads it (2026-11-17).** The
> property `sc-domain:kittray.com` is verified by DNS, the service account
> `gsc-nestlab-tech@nestlab-gmail-mcp.iam.gserviceaccount.com` holds **FULL**
> permission on it (the API answers `200` and the account's permission level
> reads `siteFullUser`), and both sitemaps are submitted —
> `https://realty.kittray.com/sitemap.xml` and `https://kittray.com/sitemap.xml`.
> The numbers below are read with that account, not by hand.
>
> **How it was done, for the next time.** The Search Console API has no
> `users` resource — adding a user to a property is a console action. The
> property's owner is `devs.scaler@gmail.com` (the account that holds the
> `kittray.com` zone and its DNS), and the verification token was written to
> the zone with that account's own Cloudflare API key rather than by
> authorizing Google over the DNS account — no new third-party grant was
> created for it. The procedure and the exact dialog controls are in the
> private operations repository, under `infra/cloudflare/kittray-hub/`.

---

## Overview

This guide walks through adding the demo to Google Search Console (GSC) and Bing Webmaster Tools so that:

- Both engines discover and crawl the sitemap.
- Submitted URLs are tracked for indexing coverage.
- Excluded or errored pages are surfaced before they become long-term gaps.

All steps use the public UI of each tool. No API calls are required.

---

## 1. Google Search Console — the DOMAIN property

### 1.1 The property that exists

The domain `kittray.com` is delegated to Cloudflare and the **domain property
`sc-domain:kittray.com`** is verified on it (the `google-site-verification`
TXT records are on the zone). A domain property covers every subdomain, so it
covers `realty.kittray.com` — the product — and the apex, which carries the
index of the domain.

**The property to work in is `sc-domain:kittray.com`.** Its "Page with
redirect" report was the reason the apex existed only as a redirect to the
studio; the apex is a page now, so that report has something real to say.

A **URL-prefix** property (`https://realty.kittray.com/`) is the alternative if
you want the product's coverage in isolation of the rest of the domain. It is
not needed here.

To add the property from scratch (a fork, a customer, a teammate):

1. Go to [Google Search Console](https://search.google.com/search-console) and sign in with your Google account.
2. Click **Add property**.
3. Select **Domain** (it needs a DNS record at the registrar level and covers
   all subdomains).
4. Enter the domain:

```
kittray.com
```

Click **Continue**.

### 1.2 Verify ownership (DNS TXT — recommended)

The domain uses Cloudflare, so the **DNS TXT record** method is available and is
the recommended path. Add a TXT record at your DNS provider:

| Type | Name | Value |
|------|------|-------|
| TXT | `kittray.com` | `google-site-verification=<paste token here>` |

The `<paste token here>` value is the long verification token Google shows on the GSC screen. Store it in your password manager or CI secret store — never commit it.

### 1.3 Submit the sitemap

1. In GSC, select the property.
2. Navigate to **Sitemaps** in the left sidebar.
3. In the **Add a sitemap** field, enter the path:

```
https://realty.kittray.com/sitemap.xml
```

With a domain property GSC expects the **full URL** — the domain is not
guessed from the path. The product's own robots.txt names the same sitemap,
and the apex serves one of its own (`https://kittray.com/sitemap.xml`) that
lists the hub and the product.

4. Click **Submit**.

**Done on 2026-11-17.** Both sitemaps are submitted to the property:

| Sitemap | Submitted |
|---|---|
| `https://realty.kittray.com/sitemap.xml` | 2026-11-17T10:35:11Z |
| `https://kittray.com/sitemap.xml` | 2026-11-17T10:35:11Z |

**With the service account, the same thing is one API call** — the endpoint is
`PUT webmasters/v3/sites/{siteUrl}/sitemaps/{sitemapUrl}` (the site URL is
part of the path; the collection endpoint answers 404 for a POST):

```bash
PUT https://www.googleapis.com/webmasters/v3/sites/sc-domain:kittray.com/sitemaps/https%3A%2F%2Frealty.kittray.com%2Fsitemap.xml
```

The account that carries it is the service account named in the note above —
`sc-domain:kittray.com` reads back with the permission level
`siteFullUser`.

**The verification record stays.** The TXT record the property was verified
with is what keeps the property verified — GSC's own words on the ownership
page are *"To stay verified, don't remove the DNS record."* It is a
`google-site-verification` value in the zone's DNS, and it is never a
credential: it grants no access to anything, and the property's users are
managed in the console, not by DNS.

### 1.4 The first readings (2026-11-17)

The property was verified and the sitemaps submitted on 2026-11-17, so the
numbers start empty. What the API said the same day, through the service
account:

| Reading | Value |
|---|---|
| Clicks / impressions, 28 days | 0 / 0 — the property had no history before it was verified |
| `inspect_url` on `https://realty.kittray.com/en` | **"URL is unknown to Google"**, with `crawlAllowed: true`, `indexingAllowed: true`, `canonicalMatch: true` |
| Sitemaps | both listed; `isPending` until the first fetch |

**"Unknown to Google" is the expected state, not an exclusion.** The URL was
discovered that day; the exclusion reasons to worry about are *"blocked by
robots.txt"* and *"marked as noindex"*, and neither applies — the robots.txt
allows crawling and no page carries `X-Robots-Tag`. The first fetch takes
days; the sitemap's `lastDownloaded` is the receipt.

**The same property through the MCP.** The `cloud-gsc-suganthan-kittray`
server (`suganthan-gsc-mcp@2.5.1`, one instance per property, the property
read from `GSC_SITE_URL`) carries the same service account, so its 29 tools
read the same property — `list_sitemaps`, `submit_sitemap`, `inspect_url`,
`site_snapshot`, `advanced_search_analytics` and the rest.

### 1.5 What to monitor after submission

Once the sitemap is accepted, GSC will begin crawling submitted URLs. Check these sections weekly:

| Section | What to look for |
|---------|-----------------|
| **Coverage** | Split as **Valid** (Indexed), **Valid with warnings**, **Excluded**, **Error**. Aim for 0 Errors. |
| **Excluded** tab | Look for **Submitted URL blocked by robots.txt** (should be 0 since `robots.txt` allows all), **Submitted URL marked as `noindex`**, and **Crawl anomaly**. |
| **Enhancements** | **Core Web Vitals** — LCP, INP, CLS. |
| **Links** | GSC lists external pages that link to your site. No action needed; for awareness only. |

### 1.6 URL Inspection tool

Paste any public URL from the site into the GSC search bar to see:

- Whether Google has crawled it.
- The last crawl time.
- Any indexing or rendering issues.
- A **Request Indexing** button to priority-crawl a changed URL immediately.

Use this for any page you update and want recrawled faster than the next sitemap refresh cycle.

### 1.7 The 261 sitemap warnings, and the `/tr/` canonical

**The two findings this section answers** (read-only diagnosis, 2026-11-21):
`https://realty.kittray.com/sitemap.xml` reports **261 warnings**, and the URL
inspection of `https://realty.kittray.com/tr/` reports *"Google chose
`…/tr/`, you declared `…/tr`"*.

**The count.** The sitemap carries 2349 `<url>` entries = 261 paths × 9 locales.
261 warnings is exactly one per **path-group** — and also exactly one per
**path** (one locale each) — not one per URL. The Search Console API exposes the
warning *count* per sitemap but not the warning *text*, so the API cannot say
which of the two it is. That single fact is the whole limit of the API.

**Everything the API can see is sound.** Each check was made against the live
site and the live API:

| Check | Result |
|-------|--------|
| All 2349 sitemap URLs | answer 200, `index, follow`, a self-referencing canonical |
| The hreflang clusters | every cluster lists its 9 locales plus `x-default` → `/pl`; every alternate points at a URL that is itself in the file |
| The locales | carry genuinely translated content — the `/ru` page renders Russian, and the per-locale content differs |
| URL inspection, sampled across the locales | *"Submitted and indexed"*, `canonicalMatch: true`, `issues: []` |
| A page Google has not crawled yet (`/ru/valuation`) | *"URL is unknown to Google"* — yet it answers 200 with the right canonical, and `robots.txt` allows `/` |
| Googlebot, bingbot and a browser UA | the same 200, the same bytes and the same canonical — no bot-blocking, no challenge |

**The one URL that differs.** `https://realty.kittray.com/tr/` — the
trailing-slash variant. The site serves `/tr` with 200 and a self-referencing
canonical and 308-redirects `/tr/` → `/tr`; the sitemap lists no trailing-slash
locale root, and neither does the page: the homepage's hreflang cluster and its
canonical are slashless (`https://realty.kittray.com/tr`), and the page carries
no `"/xx/"` locale link at all. Google still indexed the redirecting variant
and chose it as its own canonical. That is Google's choice, not a defect in the
file: the redirect resolves and the canonical converges on the URL the site
serves.

### 1.7.1 The warning text, read in the Search Console UI (2026-11-21)

The warning text was read in the Search Console UI — through the NestLab
Automation Chrome over CDP, signed in as `nestlab.micro@gmail.com` (the
account that owns `sc-domain:kittray.com`; the Automation Chrome's `Default`
profile carries `auto.tester.py@gmail.com`, which answers *"Oops, you don't
have access to this property"*). **The UI does not show a warning text, and it
does not show a warning at all:**

| Surface | What it says |
|---|---|
| Sitemaps list | both sitemaps **Status: Success** — realty 1,899 discovered pages (last read Nov 21), kittray.com 2 (last read Nov 19) |
| realty drilldown | **"Sitemap processed successfully"** — no Warnings card, no Errors card |
| kittray.com drilldown | the same — **"Sitemap processed successfully"** |
| Pages report (whole property) | 3 indexed pages; **one** exclusion reason — **"Page with redirect", 3 pages**, Source: Website, Validation: Not Started, first detected 11/14/26, last update 11/16/26, trend 6 -> 4 -> 2 -> 0 |
| Pages report **filtered by the realty sitemap** | **"Processing data, please check again in a day or so"** |

The API's counter (`warnings: 261` and `warnings: 1`) therefore has **no
counterpart in the UI today**, and the UI itself says the per-URL data is still
being computed. The warning text cannot be read until that processing finishes
— the re-check is TaskMaster **#107**, and the release numbers it waits on
arrive with the +24h datapoint (TaskMaster #14).

**The re-read, 2026-11-21T21:10Z — nothing moved.** The API still answers
`warnings: 261` and `warnings: 1` (`errors: 0`; realty `lastDownloaded
2026-11-21T06:42Z`), both sitemaps are still `Status: Success`, the realty
drilldown still answers *"Sitemap processed successfully"*, and the Pages report
filtered by the realty sitemap still answers *"Processing data, please check
again in a day or so"* with an **empty** exclusion table — the header row and
nothing else. The per-URL data is still being computed, so the warning text
does not exist yet, and nothing is claimed about it.

**And the re-read is now automatic.** The detached collector that takes the
release-wave numbers also reads both surfaces over CDP at every due point and
then polls every 15 minutes from that point until the data arrives, writing
`sitemap-reread-<label>.json` (the structured read, with a `closed` flag) and
`sitemap-reread-<label>.txt` (the verbatim UI text of both surfaces) into
`docs/community/private-evidence/` — the gitignored evidence directory. TaskMaster
#107 closes on the first file that carries `closed: true`, or on the API counter
falling to 0.

**The re-read, 2026-11-22T17:07Z — still open, and the false close is
retracted.** The collector's first attempt on the +24h point wrote a file that
carried `closed: true` **with every reading empty** (`drilldown_status_line:
""`, `warning_text: null`, `pages_report_reason_rows: []`). That file was a
false close and it is not evidence: the read had not happened. The Automation
Chrome was signed in as `auto.tester.py@gmail.com`, whose account answers
*"Oops, you don't have access to this property"* — and a page that says the
account has no access is the **absence** of a reading, not a reading. The
collector's close rule read *"the Pages report does not say 'Processing data'"*
— which is also what an unreadable Pages report looks like — and closed the
measurement on it. The file was removed (the copy is kept beside it as
`*.false-read-*.bak`) and the rule was changed: **a close now requires a
positive reading** — a non-empty exclusion table, a warning text, or the API
counter falling to 0 — and a read that cannot run writes no file at all.

The collector was also repaired where it actually failed to read: the
Automation Chrome's `Default` profile carries the wrong Google account, and
switching the profile was not enough, because the scratch tab is **reused** and
the reused tab belongs to the profile that was active when it was created. The
tab is now closed and opened again, which lands it in the now-active profile.
The collector also reads the **API counter itself** (`sitemaps.list` through
the nestlab.tech service account), so the closing criterion no longer depends on
a browser being signed in.

**The reading itself, 2026-11-22T17:07:57Z — nothing moved.** The realty
drilldown answers *"Sitemap processed successfully"*; the Pages report filtered
by the realty sitemap still answers *"Processing data, please check again in a
day or so"* with an **empty** exclusion table; the API still answers
`warnings: 261` for the realty sitemap and `warnings: 1` for kittray.com
(`errors: 0`, `isPending: false`, realty `submitted: 1899`, `indexed: 0`,
last submitted 2026-11-17T10:35Z). **The warning text still does not exist**,
so nothing is claimed about it, and TaskMaster #107 stays open — its next due
point is the weekly one, **2026-11-23T01:05Z**.

**The three redirecting URLs, named.** The "Page with redirect" drilldown
lists them: `https://kittray.com/` (crawled Nov 11), `http://www.kittray.com/`
(Nov 11) and `https://www.kittray.com/` (Nov 10). All three are the studio
landing page's host variants — and **`https://kittray.com/` is one of the two
URLs in the kittray.com sitemap**. That is the whole content of that
sitemap's single warning: a listed URL that was a redirect when Google last
crawled it. It answers 200 today. The sitemap's other URL,
`https://realty.kittray.com/pl`, is on a **second host** — a cross-domain
entry in a sitemap submitted for `kittray.com` — which is the only other
candidate for that warning, and the reason that sitemap carries two URLs at
all.

**The 261, measured at full scale.** Every one of the 2349 URLs in
`realty.kittray.com/sitemap.xml` was probed for redirects: **2349 x 200, zero
redirects, zero errors.** The file is also structurally clean — 2349 unique
`<loc>` values, no duplicates, no trailing-slash variants, and every entry
carrying exactly 10 hreflang links (9 locales + `x-default`) that all point at
the **same path** in that locale, `x-default` at the same path in Polish.
Every `lastmod` is the same valid W3C datetime shape. The generator
(`apps/web/src/app/sitemap.ts` -> `languageAlternates(path)` in
`apps/web/src/lib/metadata.ts`) is right, and its own test
(`apps/web/src/app/__tests__/sitemap.test.ts`) asserts the `x-default` shape.

**What that leaves.** By the same mechanism as the kittray.com warning, the
261 are one per path-group of a URL that **was** a redirect when Google crawled
it — the Pages report's trend (6 -> 4 -> 2 -> 0, last update 11/16/26) says
the redirects were fixed on 2026-11-16, the day the demo was made indexable.
The count fits: the URL every cluster points at as `x-default` is the `/pl`
variant, and there are exactly 261 of those. **That is a hypothesis, not a
measurement** — the Pages report for that sitemap says the data is still
processing, and no crawl data exists for 261 of these URLs (Google has
crawled 6 of the property's pages). The prediction is falsifiable: after the
next processing, either the warning count drops to 0, or the drilldown names
the type and the URLs, and either outcome belongs in this section.

**What is left to close this.** The warning text, once Google finishes
processing — the drilldown itself says *"check again in a day or so"*. Until
then this section carries the measurement, the two named candidates and the
falsifiable prediction, and nothing more.

**The reading that closed the +24h point — 2026-11-23T02:16:03Z.** The Pages
report stopped answering *"Processing data, please check again in a day or so"*:
it rendered, and it lists exactly **one** exclusion row — **"Page with redirect"**,
Source: Website, Validation: Not Started, **3 pages** — with 3 pages not indexed
and 1 indexed (last update 11/16/26). That is the row the property-level reading
named on 2026-11-21: the studio landing's three host variants —
`https://kittray.com/`, `http://www.kittray.com/`, `https://www.kittray.com/` —
which answer 301 to the canonical host today (`https://kittray.com/` answers
200). So the warning type the UI names is **"Page with redirect"**, and it is the
type of the **kittray.com** sitemap's single warning — the one whose listed URL
was a redirect when Google last crawled it — and not a measurement of the 261.

**The 261 are still unnamed.** At that reading the realty drilldown answered a
malformed-request error ("400. That's an error."), so its status line is empty;
at the weekly point, read 28 seconds later, it answers *"Sitemap processed
successfully"* and names no warning. The API still answers `warnings: 261` for
the realty sitemap and `warnings: 1` for kittray.com (`errors: 0`,
`isPending: false`). The exclusion row the Pages report names counts **3**
pages, not 261, and those three are the studio landing's host variants — so the
261 keep the status the paragraph above gives them: a hypothesis, not a
measurement. The collector keeps polling every 15 minutes; the next reading that
names a type for the realty sitemap belongs here.

**The collector had stopped, and was started again.** It logged its last attempt
at 2026-11-22T17:38:54Z and the process was gone — the weekly point came due at
2026-11-23T01:05Z with nobody reading it. The collector was started again at
2026-11-23T02:15:19Z: it read the +24h point (closed, the row above) and the
weekly point (`sitemap-reread-weekly-2026-W50.json`, `closed: false` — the
drilldown says *"Sitemap processed successfully"*, the Pages report still says
*"Processing data"*, the counter has not moved).

---

## 2. Bing Webmaster Tools

### 2.1 Add your site

1. Go to [Bing Webmaster Tools](https://www.bing.com/webmasters) and sign in with a Microsoft account.
2. Click **Add Site**.
3. Enter the URL:

```
https://realty.kittray.com/
```

### 2.2 Verify ownership

**Option A — DNS CNAME (recommended for a custom domain)**

Add a CNAME record at your DNS provider:

| Type | Host | Value |
|------|------|-------|
| CNAME | `www` | `realty.kittray.com` |

Then in Bing Webmaster Tools, choose **CNAME** verification and follow the on-screen prompt.

**Option B — BingSiteAuth.xml upload**

1. In Bing Webmaster Tools, select **Verify using a file** (the default offer).
2. Download the `BingSiteAuth.xml` file they provide.
3. Place it in `apps/web/public/` in your project.
4. Deploy.
5. Click **Verify** in Bing Webmaster Tools once the deploy has picked it up.

```xml
<!-- apps/web/public/BingSiteAuth.xml — do NOT commit this file anywhere -->
<?xml version="1.0"?>
<users>
  <user>...</user>
</users>
```

> The file content is provided by Bing during the verification step. Download it from Bing's UI — never generate it from memory or paste a sample.

After verification, **remove `BingSiteAuth.xml` from the project** (it was only needed for the one-time verification step).

### 2.3 Submit the sitemap

1. After verification, go to the site dashboard.
2. Navigate to **Sitemaps** (left sidebar).
3. Paste the full sitemap URL:

```
https://realty.kittray.com/sitemap.xml
```

4. Click **Submit**.

Bing caches sitemaps for 24–48 hours before re-fetching. Use the **URL Inspection** tool (top bar) to request immediate crawling of any specific page.

---

## 3. Availability

The demo runs on a single shared host. It is a demo, not a production SLA — occasional
`503` responses during a restart or a deploy are possible, and both Google and Bing treat
frequent 503s as a crawl-quality signal.

### Symptoms you may see

- GSC Coverage shows **Excluded → Crawl anomaly** for submitted URLs.
- Bing Webmaster Tools shows **HTTP 503** on sitemap fetch.
- Sitemap submission itself fails with "Couldn't fetch".

### Keeping the demo warm

Add a lightweight uptime monitor that pings the site periodically:

| Tool | Setup |
|------|-------|
| **Uptime Kuma** (recommended — self-hosted) | Create an `HTTP` monitor for `https://realty.kittray.com/` with a 10-minute interval. |
| **cron-job.org** (free, no server needed) | Create a cron job hitting `https://realty.kittray.com/` every 10 minutes. |
| **GitHub Actions** (simple schedule) | Add a workflow that curls the URL on a `schedule: cron: '*/10 * * * *'`. |

The goal is to keep the site warm so crawlers rarely hit a cold instance.

---

## 4. robots.txt — Two Files, and Which One the Demo Serves

There are two `robots.txt` files in play, and they say opposite things:

| File | Where it lives | What it says |
|------|-----------------|--------------|
| **The product's own** | `apps/web/public/robots.txt`, baked into the image | Allows crawling, allows the AI crawlers explicitly, points at the sitemap, blocks the private paths |
| **The demo override** | a `robots.txt` mounted into the demo deployment | `User-agent: *` / `Disallow: /` — nothing is crawlable |

The demo served the **override** until 2026-11-16, and every page also
answered `X-Robots-Tag: noindex, nofollow`. The override existed so the links
in the marketing drafts did not release unfinished pages into a search index.
**Both mechanisms were switched off on 2026-11-16** (operator's decision), so
the demo now serves the product's own robots.txt and answers `200` with no
`X-Robots-Tag` on any page.

Two things produced that state, and the switch had to undo both:

| Knob | Where | State until 2026-11-16 | State now |
|------|-------|------------------------|-----------|
| `SEARCH_INDEXING` | the deployment's runtime environment | `false` | unset — the guard in `apps/web/src/lib/indexing.ts` only adds `X-Robots-Tag` when it is exactly `false` |
| `robots.txt` | mounted into the demo deployment | the Disallow-all override | the mount is dropped and the product's own file comes back with the image |

For a future indexed release, this is the file that comes back with the image —
`apps/web/public/robots.txt`:

```
User-agent: *
Allow: /

# AI / LLM bots — explicit allow for citation and training
User-agent: GPTBot
Allow: /
... (Claude-Web, ClaudeBot, anthropic-ai, PerplexityBot, Google-Extended,
     CCBot, Bytespider, Applebot-Extended)

Sitemap: https://realty.kittray.com/sitemap.xml

# Private areas — noindex for all bots
Disallow: /api/
Disallow: /admin/
Disallow: /*/auth/
Disallow: /*/settings/
Disallow: /*/favorites/
Disallow: /*/saved-searches/
```

| Decision | Rationale |
|----------|-----------|
| `User-agent: *` + `Allow: /` | All compliant crawlers may crawl all public routes. |
| Private path `Disallow` blocks | Prevents `/api/`, `/admin/`, auth flows, and user-specific pages from being crawled. |
| **Explicit AI-bot `Allow` rules** | We want the demo to be discoverable and citable by AI assistants, so the major crawlers are allowed explicitly. |

With that file in place, the GSC "Excluded" tab in section 1.5 should show **no**
"Submitted URL blocked by robots.txt" entries — and if it does, the deployment
is still serving the override, not the product's own file.

---

## 4a. The Switch — and the Switch Back

The two knobs above are the whole switch, and both are runtime: no rebuild, no
new image, no release. The procedure is written so that it can be undone by
one command, because an indexing switch that cannot be undone is a switch
nobody will ever pull.

### The switch ON (the operator's decision) — DONE, 2026-11-16

The demo deployment runs its stack from `/opt/app/aire-demo`, with the compose
file that names the image and the environment.

```bash
# 1. The header: the guard only adds X-Robots-Tag when the variable is
#    exactly "false". Unset it, or set it to "true".
cd /opt/app/aire-demo
sed -i 's/^      - SEARCH_INDEXING=false$/      - SEARCH_INDEXING=true/' docker-compose.yml

# 2. The robots.txt: the Disallow-all override is a MOUNT over the product's
#    own file. Drop the mount and the file comes back with the image.
#    (The product's own file allows crawling, allows the AI crawlers
#    explicitly, points at the sitemap and blocks the private paths.)

# 3. Recreate the frontend so it picks the environment up.
export AIRE_IMAGE_TAG=<the running tag>
set -a && . "$HOME/.aire-build.env" && set +a
docker compose up -d --force-recreate frontend
```

**What actually ran on 2026-11-16** (the operator's decision to lift the
`noindex`), on the node, with a timestamped backup of every file it touched
(`docker-compose.yml.bak.<ts>`, `.env.bak.<ts>`, `robots.txt.bak.<ts>`):

1. the `SEARCH_INDEXING=false` line was deleted from the frontend service;
2. the `./robots.txt:/app/apps/web/public/robots.txt:ro` mount was deleted,
   and the `volumes:` key it left empty was removed with it — an empty
   `volumes:` is invalid compose and the stack refuses to start;
3. the override file itself was moved aside;
4. the version pin in `.env` was corrected — it named `5.3.6` while the
   running stack was `5.3.7`, so a `docker compose up` would have rolled the
   public demo back a version. **A stale pin is not cosmetic: it is an older
   build in public.** Check it after every release;
5. the frontend was recreated on the running tag.

### The switch BACK — one command

```bash
cd /opt/app/aire-demo &&   sed -i 's/^      - SEARCH_INDEXING=true$/      - SEARCH_INDEXING=false/' docker-compose.yml &&   export AIRE_IMAGE_TAG=<the running tag> && set -a && . "$HOME/.aire-build.env" && set +a &&   docker compose up -d --force-recreate frontend
```

The `robots.txt` mount is not restored by that command, because it was never
removed by the script: drop the mount by hand when switching on, and put it
back by hand when switching off. The override file lives beside the compose
file on the node.

### How to tell which state the demo is in

```bash
curl -sI https://realty.kittray.com/en | grep -i x-robots-tag   # noindex, nofollow => OFF
curl -s  https://realty.kittray.com/robots.txt | head -3        # "Disallow: /" => OFF
curl -s  https://realty.kittray.com/sitemap.xml | grep -c "<url>" # the routes + the listings => ON
```

**What is prepared, and what the operator decides.** The on-site surface -
per-route metadata, canonicals, the hreflang clusters, the `schema.org/Property`
of a listing, the sitemap and the llms.txt - is in place (see
`docs/reviews/2026-11-11-seo-geo-aeo-realty-kittray.md`). The decision to
index the demo is the operator's: an agent publishes nothing under their name
(Rule 306 gate 4), and a half-finished product in a search index is far harder
to take out than to keep out.

## 5. Evidence Collection (Never Commit)

Store all verification screenshots and export files in:

```
docs/community/private-evidence/
```

This directory is gitignored. The structure is:

```
docs/community/private-evidence/
├── .gitignore                    # contains: private-evidence/
├── gsc-verification-*.png        # GSC property verified screen
├── gsc-sitemap-submitted-*.png   # GSC sitemap accepted
├── gsc-coverage-*.png            # GSC Coverage summary
├── bing-verification-*.png       # Bing site verified screen
├── bing-sitemap-*.png            # Bing sitemap submitted
└── robots-txt-*.png              # robots.txt as rendered
```

Name files descriptively with the date: `gsc-verification-2026-07-21.png`.

**Never** commit these files. If you accidentally `git add` them, run `git restore --staged docs/community/private-evidence/` immediately.

---

## 6. 7-Day GSC Checklist

Use this checklist during the first week after adding the site to GSC. Perform each step and save evidence to `docs/community/private-evidence/`.

| Day | Task | Pass criteria |
|-----|------|---------------|
| **Day 1** | Add property in GSC | URL Prefix property created |
| **Day 1** | Verify ownership (DNS TXT) | Green "Verified" badge in GSC |
| **Day 1** | Submit sitemap | GSC shows sitemap as "Submitted" with a fetch date |
| **Day 1** | Inspect a public URL manually | GSC URL Inspection shows "URL is on Google" |
| **Day 2** | Check Coverage — Errors | 0 Errors reported |
| **Day 2** | Check Excluded tab | No "Submitted URL blocked by robots.txt" |
| **Day 3** | Check Coverage — Valid | At least the homepage + 1–2 landing pages appear as Indexed |
| **Day 3** | Ping the demo URL manually (browse) | Returns 200, not 503 |
| **Day 4** | Check Enhancements → Core Web Vitals | LCP < 2.5s, CLS < 0.1, INP < 200ms (approximate) |
| **Day 4** | Set up uptime monitor (Uptime Kuma or cron-job.org) | Monitor shows "Up" continuously |
| **Day 5** | Check Excluded tab for "Discovered — currently not indexed" | Investigate any unexpectedly excluded pages |
| **Day 6** | Submit 1–2 recently updated pages via URL Inspection → Request Indexing | GSC accepts the request |
| **Day 7** | Review Coverage summary | Majority of submitted URLs in "Valid → Indexed" |
| **Day 7** | Add site to Bing Webmaster Tools | Site verified |
| **Day 7** | Submit sitemap in Bing | Sitemap accepted |
| **Day 7** | Archive all evidence screenshots | Saved in `docs/community/private-evidence/` |

---

## Quick Reference

| Resource | URL |
|----------|-----|
| Google Search Console | https://search.google.com/search-console |
| Bing Webmaster Tools | https://www.bing.com/webmasters |
| robots.txt (live) | https://realty.kittray.com/robots.txt |
| Sitemap (live) | https://realty.kittray.com/sitemap.xml |
| GSC URL Inspection | Paste any `realty.kittray.com/*` URL into the GSC search bar |
| Evidence folder | `docs/community/private-evidence/` (gitignored) |
