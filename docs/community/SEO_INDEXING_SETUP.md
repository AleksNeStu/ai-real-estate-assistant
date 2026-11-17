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

### 1.4 What to monitor after submission

Once the sitemap is accepted, GSC will begin crawling submitted URLs. Check these sections weekly:

| Section | What to look for |
|---------|-----------------|
| **Coverage** | Split as **Valid** (Indexed), **Valid with warnings**, **Excluded**, **Error**. Aim for 0 Errors. |
| **Excluded** tab | Look for **Submitted URL blocked by robots.txt** (should be 0 since `robots.txt` allows all), **Submitted URL marked as `noindex`**, and **Crawl anomaly**. |
| **Enhancements** | **Core Web Vitals** — LCP, INP, CLS. |
| **Links** | GSC lists external pages that link to your site. No action needed; for awareness only. |

### 1.5 URL Inspection tool

Paste any public URL from the site into the GSC search bar to see:

- Whether Google has crawled it.
- The last crawl time.
- Any indexing or rendering issues.
- A **Request Indexing** button to priority-crawl a changed URL immediately.

Use this for any page you update and want recrawled faster than the next sitemap refresh cycle.

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

With that file in place, the GSC "Excluded" tab in section 1.4 should show **no**
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
