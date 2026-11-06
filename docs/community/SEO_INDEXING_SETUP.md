# SEO Indexing Setup — Google Search Console & Bing Webmaster Tools

**Target:** `https://realestate.nestlab.tech/`
**Scope:** Public procedure only. No tokens, API keys, or credentials anywhere in this guide.
**Evidence storage:** `docs/community/private-evidence/` (gitignored — never commit screenshots or exports).

---

## Overview

This guide walks through adding the demo to Google Search Console (GSC) and Bing Webmaster Tools so that:

- Both engines discover and crawl the sitemap.
- Submitted URLs are tracked for indexing coverage.
- Excluded or errored pages are surfaced before they become long-term gaps.

All steps use the public UI of each tool. No API calls are required.

---

## 1. Google Search Console — URL Prefix Property

### 1.1 Create or select the property

1. Go to [Google Search Console](https://search.google.com/search-console) and sign in with your Google account.
2. Click **Add property**.
3. Select **URL prefix** (not Domain — Domain requires DNS at the registrar level and covers all subdomains; URL Prefix is sufficient for a single deployment).
4. Enter the exact URL:

```
https://realestate.nestlab.tech/
```

Click **Continue**.

### 1.2 Verify ownership (DNS TXT — recommended)

The demo uses a custom domain, so the **DNS TXT record** method is available and is the
recommended path. Add a TXT record at your DNS provider:

| Type | Name | Value |
|------|------|-------|
| TXT | `realestate` | `google-site-verification=<paste token here>` |

The `<paste token here>` value is the long verification token Google shows on the GSC screen. Store it in your password manager or CI secret store — never commit it.

### 1.3 Submit the sitemap

1. In GSC, select the newly verified property.
2. Navigate to **Sitemaps** in the left sidebar.
3. In the **Add a sitemap** field, enter just the path:

```
sitemap.xml
```

GSC already knows the site URL from the property, so the full submitted URL will be `https://realestate.nestlab.tech/sitemap.xml` (matches the `Sitemap:` directive in `public/robots.txt`).

4. Click **Submit**.

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
https://realestate.nestlab.tech/
```

### 2.2 Verify ownership

**Option A — DNS CNAME (recommended for a custom domain)**

Add a CNAME record at your DNS provider:

| Type | Host | Value |
|------|------|-------|
| CNAME | `www` | `realestate.nestlab.tech` |

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
https://realestate.nestlab.tech/sitemap.xml
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
| **Uptime Kuma** (recommended — self-hosted) | Create an `HTTP` monitor for `https://realestate.nestlab.tech/` with a 10-minute interval. |
| **cron-job.org** (free, no server needed) | Create a cron job hitting `https://realestate.nestlab.tech/` every 10 minutes. |
| **GitHub Actions** (simple schedule) | Add a workflow that curls the URL on a `schedule: cron: '*/10 * * * *'`. |

The goal is to keep the site warm so crawlers rarely hit a cold instance.

---

## 4. robots.txt — Current State and AI-Bot Policy

The current `apps/web/public/robots.txt` reads:

```
User-agent: *
Allow: /

# AI / LLM bots — explicit allow for citation and training
User-agent: GPTBot
Allow: /
... (Claude-Web, ClaudeBot, anthropic-ai, PerplexityBot, Google-Extended,
     CCBot, Bytespider, Applebot-Extended)

Sitemap: https://realestate.nestlab.tech/sitemap.xml

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

---

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
| robots.txt (live) | https://realestate.nestlab.tech/robots.txt |
| Sitemap (live) | https://realestate.nestlab.tech/sitemap.xml |
| GSC URL Inspection | Paste any `realestate.nestlab.tech/*` URL into the GSC search bar |
| Evidence folder | `docs/community/private-evidence/` (gitignored) |
