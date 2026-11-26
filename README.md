<div align="center">
  <img src="apps/web/public/logo.svg" width="96" alt="AI Real Estate Assistant" />
</div>

# AI Real Estate Assistant

**Ask in natural language. Get matched listings.**

An open-source conversational assistant for property search, financial analysis
and market insight. Ask for *"2-bedroom apartment in Kraków under 500k"* and it
answers from a semantic index over your own catalogue — with 17 LLM providers,
a toolbelt behind the chat (mortgage, comparison, ROI, valuation) and nine
languages.

MIT licensed, an open landing page and a free account for the app itself, and
it runs on your own server as happily as it runs on a managed platform.

[![Python](https://img.shields.io/badge/Python-3.12+-blue?style=flat&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/API-FastAPI-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Web-Next.js_16-000000?style=flat&logo=next.js&logoColor=white)](https://nextjs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.x-3178C6?style=flat&logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![CI](https://github.com/AleksNeStu/ai-real-estate-assistant/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/AleksNeStu/ai-real-estate-assistant/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Live Demo](https://img.shields.io/badge/Demo-Live-success?style=flat)](https://realty.kittray.com/)
[![Latest Release](https://img.shields.io/github/v/release/AleksNeStu/ai-real-estate-assistant?style=flat&color=2ea44f)](https://github.com/AleksNeStu/ai-real-estate-assistant/releases)

<!-- markdownlint-disable MD051 -->
## Table of Contents

- [Live demo](#live-demo)
- [The design](#the-design)
- [Deploy it your way](#deploy-it-your-way)
- [What's new](#whats-new)
- [What it does](#what-it-does)
- [Why developers pick this](#why-developers-pick-this)
- [Tech stack](#tech-stack)
- [Architecture](#architecture)
- [Quick start](#quick-start)
- [The sample sheet](#the-sample-sheet)
- [The hosted version, and what comes next](#the-hosted-version-and-what-comes-next)
- [Questions people actually ask](#questions-people-actually-ask)
- [Documentation](#documentation)
- [Testing](#testing)
- [Contributing](#contributing)
- [License](#license)
- [Support](#support)
<!-- markdownlint-restore -->

## Live demo

<div align="center">

### [**Try the live demo →**](https://realty.kittray.com/)

**The landing page is open — the app asks for a free account**

</div>

![The landing page at realty.kittray.com](assets/screenshots/home-dark.png)

**Six seconds of the demo** — the landing, the search with its results, the
assistant answering with its sources:

![Six seconds of the demo](assets/clips/demo-6s.gif)

The master is [`assets/clips/demo-6s.mp4`](assets/clips/demo-6s.mp4) — the same
six seconds in the form a landing page can play.

Everything is live — no keys, no setup, and the account is free:

- **Natural-language search** — ask *"2-bedroom apartment in Kraków under 500k"* and get matched listings
- **A real toolbelt behind the chat** — mortgage calculator, rent-vs-buy, ROI, TCO, valuation with a multi-year price forecast
- **Interactive maps** — clustered markers with area analytics
- **`9` languages** — English, Polish, Russian, German, Spanish, Italian, Portuguese, Turkish, Ukrainian
- **Honest about its limits** — the demo answers with a model we pay for, so it costs nothing to explore, and falls back to a local one if the hosted one is unreachable; a real deployment uses the provider key you bring

The assistant answers with the catalogue in front of it, and shows where every
number came from:

![The assistant answering at realty.kittray.com](assets/screenshots/chat-dark.png)

**And the application behind it** — the same design system, the same tokens,
the same ledger:

| | |
|---|---|
| ![The search with its filters and map](assets/screenshots/search-dark.png) | ![The market trends with its indicators](assets/screenshots/market-trends-dark.png) |
| **Search** — the query, the filters and the map in one screen, the results as a ledger of prices | **Market trends** — the indicators, the price curve and the districts that moved |
| ![The sign-in wall in front of the account routes](assets/screenshots/favorites-dark.png) | ![The tools of the assistant](assets/screenshots/tools-dark.png) |
| **The gate** — the eight account routes ask for an account, and say what the account is for | **Tools** — the mortgage, the comparison, the valuation and the neighbourhood, in the chat |

**And the rest of it** — the directory of the agents, the market of a city, the
wizard of the comparative analysis, the knowledge base, the analytics of the
usage:

| | |
|---|---|
| ![The agent directory](assets/screenshots/agents-dark.png) | ![The market of a city](assets/screenshots/city-overview-dark.png) |
| **Agents** — the directory of the agents and their listings | **City overview** — the market of a city, district by district |
| ![The wizard of the comparative market analysis](assets/screenshots/cma-dark.png) | ![The knowledge base](assets/screenshots/knowledge-dark.png) |
| **CMA** — the wizard of the comparative market analysis, step by step | **Knowledge** — the documents the assistant reads, and what it found in them |

**Go straight to a part of it:**

| Route | What it does |
|---|---|
| [`/en/search`](https://realty.kittray.com/en/search) | Semantic search over the demo catalogue, with filters and a map |
| [`/en/chat`](https://realty.kittray.com/en/chat) | The chat and its tools — mortgage, ROI, comparison |
| [`/en/city-overview`](https://realty.kittray.com/en/city-overview) | Per-city market analytics |
| [`/en/documents`](https://realty.kittray.com/en/documents) | Upload and query your own files |
| [`/en/agents`](https://realty.kittray.com/en/agents) | The agent directory and their listings |

## The design

**The interface this project is being ported to — the design, not the product.**

The screens below are the design reference: a static prototype of the next
version of the interface, with no live data, no account and no model behind
it. **They are not screenshots of the running application** — the screens in
[Live demo](#live-demo) are, and those are the ones that show the product as
it runs today.

What the two share is the palette: the same tokens, out of
[`apps/web/src/app/globals.css`](apps/web/src/app/globals.css), in the light
theme and in the dark one. The comparison between them is therefore between
two renderings of one design, and not between two designs.

| | |
|---|---|
| ![The landing of the design](assets/design/Landing-dark.png) | ![The search of the design](assets/design/Search-dark.png) |
| **Landing** — the working tool: a parsed query, a map and three priced rows | **Search** — the query, the filters and the map in one screen |
| ![The assistant of the design](assets/design/Chat-dark.png) | ![The tools of the design](assets/design/Tools-dark.png) |
| **Assistant** — the conversation, its tool calls and the ledger of the matches | **Tools** — the mortgage, the comparison, the valuation and the neighbourhood |
| ![The analytics of the design](assets/design/Analytics-dark.png) | ![The market trends of the design](assets/design/MarketTrends-dark.png) |
| **Analytics** — the calculators, the inputs on the left and the numbers on the right | **Market trends** — the indicators, the price curve and the districts that moved |
| ![The market of a city in the design](assets/design/CityOverview-dark.png) | ![The valuation of the design](assets/design/Valuation-dark.png) |
| **City overview** — the market of a city, district by district | **Valuation** — the price forecast of one listing, year by year |
| ![The comparative analysis of the design](assets/design/CMA-dark.png) | ![The knowledge base of the design](assets/design/Knowledge-dark.png) |
| **CMA** — the wizard of the comparative market analysis, step by step | **Knowledge** — the documents the assistant reads, and what it found in them |
| ![The favorites of the design](assets/design/Favorites-dark.png) | ![The sign-in of the design](assets/design/Auth-dark.png) |
| **Favorites** — the saved listings and the saved searches | **Sign in** — the wall in front of the account routes, and what an account is for |
| ![The top bar of the design](assets/design/TopBar-dark.png) | ![The mobile screens of the design](assets/design/Mobile-dark.png) |
| **Top bar** — the navigation, the language and the theme switch | **Mobile** — the key screens at 390 |

Both sets of images come out of one capture pipeline —
`node scripts/utils/take_screenshots.js <page> dark <folder> -dark` — so the
live screens and the reference are captured the same way.

## Deploy it your way

There is a live deployment of this project — the demo above runs the release
images, with a seeded catalogue and a model the studio pays for, on a server
its maintainer controls. You do not have to stop there: the same images are
published on every release, and three ways to run them are supported today.

| | A hosted platform | Your own VPS | The published images |
|---|---|---|---|
| **What you need** | an account on the platform | a machine with Docker and a spare gigabyte of RAM | a machine with Docker |
| **What you do** | one click, the platform builds and serves it | copy one compose file, `docker compose up -d` | pull two images, point them at your own secrets |
| **Who builds it** | the platform | you — or CI, on every release tag | you, or CI |
| **Your data** | on the platform | on your disk, in your country | on your disk, in your country |
| **Best for** | a demo, a trial, a first look | production, on your own terms | an existing setup that already runs containers |

### On a hosted platform, one click

[![Deploy to Render](https://img.shields.io/badge/Deploy%20to%20Render-46b3a0?style=for-the-badge&logo=render&logoColor=white)](https://render.com/deploy?repo=https://github.com/AleksNeStu/ai-real-estate-assistant)

The blueprint in [`render.yaml`](render.yaml) declares the web service and the
API, the build steps and the health check. The platform builds the images,
serves them and restarts them on every release.

### On your own VPS server

[`deploy/docker-compose.selfhosted.yml`](deploy/docker-compose.selfhosted.yml)
is the whole stack: a FastAPI backend and a Next.js frontend, one persistent
volume, one published port. It needs no paid model key to answer.

```bash
curl -O https://raw.githubusercontent.com/AleksNeStu/ai-real-estate-assistant/main/deploy/docker-compose.selfhosted.yml
cat > .env <<'ENV'
API_ACCESS_KEY=change-me
JWT_SECRET_KEY=change-me
SECURITY_PEPPER=change-me
ENV
docker compose -f docker-compose.selfhosted.yml up -d
```

Put a TLS terminator in front of it — a reverse proxy, a load balancer, a
tunnel — and never expose the port raw.

### With CI instead of a terminal

This repository also ships a
[self-host deploy workflow](.github/workflows/deploy-selfhosted.yml). Give it a
deploy key and the address of your server as repository secrets, and every
release tag rolls your machine onto the new images by itself. Nothing about
your host is stored in this repository — the host, the user, the port and the
path are all secrets you set yourself.

### Or just pull the images

Every release publishes both images to GitHub Container Registry, multi-arch
(amd64 and arm64):

```bash
docker pull ghcr.io/aleksnestu/ai-real-estate-assistant/backend:5.7.1
docker pull ghcr.io/aleksnestu/ai-real-estate-assistant/frontend:5.7.1
```

The full guide — the memory footprint per setup, the published tags and the
Kubernetes variant — is in the [deployment guide](docs/deployment/DEPLOYMENT.md).

## What's new

**`v5.7.1`** — the panel tells the truth about the source it holds.

- **A source that recovered is healthy again** — the health of a data source
  is computed from the failures it has had, and a successful sync clears the
  counter and the message of the failure it recovered from.

**`v5.7.0`** — the demo is a product, not a screenshot.

- **The catalogue is built from the official register** — the register of
  notarial deeds is open data, free by law and needs no key, so the demo
  answers with real flats that really changed hands; the panel registers the
  register itself.
- **The demo answers without a login** — every route on the public journey
  is proved by a test that carries no token, so the promise the landing page
  makes cannot regress.
- **An uploaded file becomes a source you can sync again** — the sheet you
  hand the admin panel is kept where the sync can read it, and the panel
  names the source it created.
- **The calls to action are measurable** — every outbound link on the
  landing page and in the footer reports the click it caused, so the funnel
  is read from the same numbers the product writes.
- **The deployment says what it can do** — the capabilities endpoint tells
  the truth about the model and the data, and the panel offers exactly the
  formats the deployment can read.
- **The login flow is proved against the running deployment** — register,
  login, refresh, rotation and logout, checked against the live address by a
  script that prints no credential.

**`v5.6.0`** — the answers the product gives are the ones it measured.

- **The neighbourhood index is measured, not invented** — a factor the map
  cannot measure carries no score, and the card shows a dash for it — never a
  zero, which would say the neighbourhood is bad.
- **The official registers answer first** — the noise level comes from the
  state register and the air quality from the state monitoring network, both
  as open data with no key; the estimates that stood in for them stay as the
  fallback and are named as estimates.
- **A valuation answer is a link** — shareable and indexable, with the
  comparable sales, the period they cover and the JSON-LD on the page itself.
- **The Russian interface is complete** — English, Polish and Russian are the
  three languages the product is written for, and the key-parity test holds
  them to it.
- **The app can be installed** — the install is offered exactly where the
  browser can perform it, and an update is announced rather than applied
  silently.
- **One command from nothing to a running demo**, and **an open command for
  the public API** — a command-line client for the three public operations,
  with the types generated from the published contract.

**`v5.5.0`** — the demo keeps the promises it makes about itself.

- **The waitlist form reaches the operator** — a capture used to end at a row
  in a table only the operator could open, so a launch had to be followed by a
  human reading the board. The row now renders the high-value-lead template
  and the mail goes to the address the deployment names
  (`LEAD_ALERT_EMAIL_TO`) — never to one written in the source. The row is
  written first and the mail is best-effort, so a mail failure cannot show a
  visitor a failure for an address that was in fact saved.
- **The flat is valued from the register of notarial prices** — "what is my
  flat worth" was answered from one seeded listing's asking price. It is
  answered now from the prices people actually paid: the Rejestr Cen
  Nieruchomości, free by law since February 2026, read from the weekly
  export and kept in a table of its own. The comparables are the street first
  and the city when the street is thin, and the forecast degrades to the
  measured movement of the transactions instead of a flat 3 %.
- **The launch drafts name the build the demo actually runs** — five of them
  named a build that is not the one the demo serves.
- **The site's first click is recorded** — the weekly snapshot carries it now,
  and four records the earlier snapshots got wrong are corrected.

**`v5.4.0`** — the demo measures itself, and the pipeline holds the line.

- **The demo's real-model answer is proven by a test** — the headline claim
  of this README is checked by the suite instead of asserted.
- **The backend suites run in the pipeline, and a breaking change to the
  public API fails it** — the pipeline runs the backend suites and the
  contract diff, so a change that breaks the committed baseline cannot reach
  a release.
- **The site measures itself** — Cloudflare Web Analytics, cookieless, and
  the tracked interaction carries the locale it happened on.
- **The buyer memory can be seen and deleted in the account** — the memory
  the buyer builds is readable and removable, which is what the legal wording
  promises.
- **The demo is indexed, and the documents say so** — the deployment stopped
  answering `noindex`, and the documents follow the state.

**`v5.3.4`** — the demo can be signed into, and the pages say what they are.

- **The demo signs in with Google** — the deployment hands the browser to
  Google and takes the account back: the state, the PKCE verifier and the
  session live in httpOnly cookies, the account is created or linked by
  e-mail, and the flow ends on the interface's own page. The button appears
  only where a deployment carries a client. The privacy policy and the terms
  of use are pages of the deployment now, and they say what a sign-in stores.
- **Every public route says what it is** — fourteen routes answered with the
  same title and the same description. Each one now declares its own, in the
  language of the route, with its own canonical address and its own cluster
  of translations.
- **A listing is a page a crawler can read** — the page of a single property
  was rendered in the browser, so a crawler received an empty shell. It is
  read on the server now: the page carries the listing, its title, its
  address and a `schema.org/Property` block with its position, its rooms and
  its offer.
- **The catalogue can be enumerated, and it is** — `GET /api/v1/properties`
  answers with a page of the listings, the sitemap carries all of them, and
  the llms.txt names the routes, the languages and the size of the catalogue.

**`v5.3.1`** — the property page answers.

- **The page's data arrives** — the endpoints behind the property page asked
  the application state for the catalogue, and the application never puts one
  there, so every request answered `503` even with a full catalogue behind it.
  The endpoints read the catalogue the way the rest of the API does, and the
  page shows its listing.

**`v5.3.0`** — a property has a page of its own.

- **The property page** — the search answered with listings and the card
  showed them, but a reader who picked one had nowhere to go. The page shows
  the listing itself: the price, the numbers, the description, the amenities,
  the AI one-liner of its neighbourhood, and the comparable listings of the
  same city and type. It is public — a visitor who clicks a listing is nobody
  until they sign in, so the data it reads does not ask for a session. The
  title of a search result and a marker on the map both open it.

**`v5.1.20`** — the model thinks as hard as the deployment asks it to.

- **The cheapest way to answer** — M3.1 Flash always reasons, and it reasons at
  `max` when the parameter is missing. The effort is a setting of the
  deployment now (`MINIMAX_REASONING_EFFORT`), because the bill belongs to the
  operator who pays it and not to the code. The same request costs `350`
  output tokens at `max` and `304` at `low`, the input of a demo request is
  `99.9%` a cache hit, and the ceiling of one answer is a token cap — so a
  request of the public demo costs about a tenth of a cent.

**`v5.1.19`** — the demo answers.

- **The public demo answers with a real model** — the conversation buffer that
  holds the history of a conversation knew one name for the question and
  refused the other, so every question came back as an error. The retrieval
  chain and the agent executor keep one conversation now, and the factory that
  builds the model follows the flag of the model instead of the flag of the
  demo. The answer is grounded in the catalogue and cites it.
- **The landing page is the front door** (`v5.1.18`) — the root of the public
  address carries the design system of the project: zinc chrome, one teal
  action, Geist for every number. The hero asks for a property, the catalogue
  counts itself, the features are a ledger, the data coverage is honest about
  what it does not have, the product is compared in four states, and the
  waitlist catches the address of a visitor before the account exists.
- **Sign-in is real** — the registration writes the consent of the GDPR into
  the account, the token is read before the demo user is invented, and the
  copy of the `9` locales follows the state of the deployment instead of
  promising a local model the deployment does not run.

**`v5.1.10`** — the demo lives on a domain of its own.

- **A public address that can be printed on a business card** — the demo moved
  from a platform subdomain to `https://realty.kittray.com`, on a domain
  delegated to Cloudflare. The Worker that fronts the deployment keeps its
  custom domain, so the front door did not change — only the name on it.
- **One address in the tree** — the README badge, the live-demo link, the
  `package.json` homepage, `robots.txt`, the sitemap line, `llms.txt`, the
  launch copy and the canonical URL all follow the same value. The public
  address of a deployment is a build argument (`SITE_URL`), so changing it is
  one setting and one release.
- **A mark, a card and half the README** (`v5.1.9`) — the icon is now a roof
  over a point, in the monochrome the design system asks for; the social
  preview says what the project is; the README is the short version.
- **A second deployment target** (`v5.1.8`) — the release pipeline now rolls a
  server you own, not only the managed platform. One compose file, one
  workflow, no credentials in the tree.
- **AI property valuation** — paste a property id, get an estimate of the
  current value plus a projection for `1`, `3`, `5` and `10` years, with a confidence
  band and the key drivers. Try it at `/valuation`.
- **An AI neighbourhood summary** on every property page — what the district
  feels like, what is around it, how easy it is to move around. It falls back
  silently when the model is unavailable.
- **The monthly payment on the card** — every listing shows its estimated
  monthly cost next to the title (20 % down, 30 years, 6.5 % APR by default;
  not a lending offer).
- **A first-visit tour** — five steps from the landing page to the features
  that matter, shown once and remembered locally.
- **A citation layer for AI search** — an expanded `llms.txt`, a `robots.txt`
  that names the AI crawlers it wants, `FAQPage` JSON-LD next to the existing
  schemas, a social preview image, and complete metadata in nine locales.
- **335 dependency alerts closed** — every critical and high advisory resolved,
  the floors pinned in both the lock file and the project file.

Full notes: [v5.7.1 release](https://github.com/AleksNeStu/ai-real-estate-assistant/releases/tag/v5.7.1) ·
[changelog](CHANGELOG.md).

## What it does

| | |
|---|---|
| **Conversational search** | Natural-language queries with automatic filter extraction; hybrid semantic + keyword retrieval over ChromaDB with MMR reranking |
| **Financial tools** | Mortgage calculator, rent-vs-buy, ROI, TCO, comparative market analysis, AI valuation with a multi-year forecast |
| **Neighbourhood one-liner** | An AI summary of a district's character, lifestyle and accessibility, on every property page |
| **Maps** | Clustered markers, area comparisons, city-overview analytics |
| **Localisation** | `9` languages with EU AI Act compliance labels on AI output |
| **Security** | OWASP-hardened: rate limiting, audit logging, SSRF protection, dual-mode auth (API key + JWT), progressive security pipeline in CI |

## Why developers pick this

1. **Multi-provider LLM routing** — `17` providers with an automatic fallback
   chain; a per-request provider selection by header or parameter, no code
   change to switch models.
2. **Hybrid RAG + vector search** — a query-complexity classifier routes
   between RAG-only, hybrid RAG with enhancement, and agent-with-tools;
   ChromaDB with MMR reranking for the retrieval.
3. **A complete reference stack** — FastAPI + Next.js `16` + ChromaDB, Docker
   Compose and Kubernetes, CI that ships the images, and a self-host deploy
   path you can point at your own server.

## Tech stack

| Layer | Technology |
|---|---|
| Backend API | FastAPI (Python `3.12+`) |
| Frontend | Next.js `16` + React `19` |
| Vector DB | ChromaDB (semantic search + MMR reranking) |
| Relational DB | PostgreSQL / SQLite |
| LLM providers | OpenAI, Anthropic, Google, Grok, DeepSeek, MiniMax, OpenRouter, Together AI, Fireworks AI, HuggingFace, Groq, Mistral, Qwen, ZAI, Moonshot, OpenCode, local Ollama |
| Container | Docker / Docker Compose |
| CI/CD | GitHub Actions (CI, GHCR images, deploy) |
| Monitoring | Uptime Kuma + structured logs |

## Architecture

```mermaid
graph LR
    UI["Next.js Frontend"] --> Proxy["API Proxy"]
    Proxy --> API["FastAPI Backend"]
    API --> QA["Query Analyzer"]
    QA -->|Simple| RAG["RAG Engine"]
    QA -->|Complex| Agent["Hybrid Agent"]
    Agent --> Tools["Tools"]
    RAG --> VDB[("ChromaDB")]
    Tools --> LLM["AI Providers"]
    API --> DB[("PostgreSQL / SQLite")]
```

Full system design: [docs/architecture/large-saas-overview.md](docs/architecture/large-saas-overview.md).

## Quick start

One command, no API key:

```bash
curl -fsSL https://raw.githubusercontent.com/AleksNeStu/ai-real-estate-assistant/main/scripts/install/install.sh | sh
```

On Windows, in PowerShell:

```powershell
irm https://raw.githubusercontent.com/AleksNeStu/ai-real-estate-assistant/main/scripts/install/install.ps1 | iex
```

The installer clones the repository, writes the `.env` with a generated API key
and database password, creates the state directories, starts the stack, waits
for the health check and prints the URL it started. The assistant answers with
the built-in demo model; put a provider key in `deploy/compose/.env` and set
`DEMO_LLM_MODE=false` to use a real one.

Doing it by hand is eight lines:

```bash
git clone https://github.com/AleksNeStu/ai-real-estate-assistant.git
cd ai-real-estate-assistant

# Docker, demo mode, no API keys required
cp deploy/compose/.env.example deploy/compose/.env
# The backend runs as uid 999 and writes its state into these directories.
# On Linux Docker creates them as root, so they need write access for that
# user; on macOS and Windows Docker's own permissions already allow it.
mkdir -p deploy/compose/{chroma_db,data/audit,.preferences,.notifications,.sessions}
chmod -R a+rwX deploy/compose/{chroma_db,data/audit,.preferences,.notifications,.sessions}
docker compose -f deploy/compose/docker-compose.yml up --build
# Frontend: http://localhost:3082 · API: http://localhost:8082/docs
```

On Windows, `.\scripts\docker\start.ps1` does the same thing with the ports
assigned for you. For the manual path (uv + npm), the API reference and the
verification scripts, see the [5-minute quickstart](docs/development/QUICKSTART_5MIN.md).

## The sample sheet

Fourteen invented listings — Polish cities, prices in PLN, addresses on a
street that does not exist — ship with the repository, so the import chain has
something to read before you have a feed of your own.

| File | What it is |
|---|---|
| [`samples/properties-sample.xlsx`](samples/properties-sample.xlsx) | the workbook, one sheet named `Listings` |
| [`samples/properties-sample.csv`](samples/properties-sample.csv) | the same fourteen rows as text |

Import it through the admin panel: **Admin → Data sources → Import Data →
Upload File**, pick the file, and the panel names the source. On a deployment
that has accounts, the admin screen asks for one first. The backend reads
`.xlsx`, `.xls`, `.ods` and `.csv`; a deployment that can read fewer of them
says so on the same panel.

Or over the API:

```bash
curl -X POST "http://localhost:8082/api/v1/admin/ingest/upload" \
  -H "X-API-Key: $API_ACCESS_KEY" \
  -F "file=@samples/properties-sample.xlsx" \
  -F "sheet_name=Listings" \
  -F "source_name=sample sheet"
```

The upload is the creation of a data source: the deployment keeps the file it
read under `uploads/sources/`, and the ledger carries a source that reads it —
so the same sheet can be synced again later. A second upload of the same name
replaces that source's file rather than piling up another one. A deployment
whose uploads directory does not outlive its container loses the file, and the
source says so instead of failing quietly.

The header names the schema fields, so the loader maps them without guessing:

| Column | Meaning |
|---|---|
| `title`, `description` | the headline and the text the listing carries |
| `city`, `district`, `neighborhood` | where it is — `city` is the one that has to be there |
| `address` | the street line |
| `latitude`, `longitude` | the map pin; without them the loader derives it from the city |
| `property_type` | `apartment`, `house`, `studio`, `loft`, `townhouse`, `other` |
| `listing_type` | `rent`, `sale`, `room`, `sublease` |
| `rooms`, `bathrooms` | how many |
| `area_sqm` | the area in square meters |
| `floor`, `total_floors` | the floor, and the number of floors |
| `year_built` | the year of construction |
| `energy_rating` | `A` to `G` |
| `price`, `currency` | the rent per month or the asking price, and its currency |
| `deposit` | the deposit on a rental; `0` where there is none |
| `has_parking`, `has_garage`, `has_garden`, `has_pool`, `has_bike_room`, `is_furnished`, `pets_allowed`, `has_balcony`, `has_elevator` | the amenities, `yes` or `no` |
| `distance_to_school`, `distance_to_transport` | distances in meters |

Two rules the loader does not make obvious. A cell left empty arrives as a
missing number, and a missing number in a money field drops the listing —
write `0` where there is no deposit. And a column the schema does not know is
kept as an extra field and ignored, so a sheet with a column of your own still
loads.

The file is regenerated by one command:

```bash
python scripts/utils/generate_sample_spreadsheet.py
```

<!-- HOSTED-FUNNEL-START -->
## The hosted version, and what comes next

This repository is the free, open-source version of the product. It is complete
enough to run, to read, to extend and to put in front of your own users — and
it stays that way.

The paid version is being built right now on top of the same engine, as
**PropVector AI**. The split is deliberate and it does not change with the
roadmap. The left column is what this repository does **today** — every row is
a thing in the tree you can run today, not a promise; the right column is what
the hosted tier adds on top:

| Capability | Open source (this repo) | Hosted (PropVector AI) |
|---|---|---|
| Conversational property Q&A over your own data | Free | Included |
| **Official notarial transaction prices** (Rejestr Cen Nieruchomości) | Free | Included |
| Valuation with its evidence — comparables, sample size, period | Free | Included |
| Bring your own LLM keys (`17` providers), local Ollama | Free | Included |
| Hybrid vector + keyword search (ChromaDB) with MMR reranking | Free | Included |
| Buyer memory — budget, ruled-out areas, liked listings | Free | Included |
| Accounts, favourites, saved searches | Free | Included |
| Price-drop and new-match alerts on saved searches | Free | Included |
| Neighbourhood index measured from OpenStreetMap features | Free | Included |
| Lead scoring, agent board and funnel | Free | Included |
| Enrichment pipeline and data adapters | Free | Included |
| Live listing feeds (a real feed, not the register) | — | Pro |
| More countries | — | Pro |
| Alerts against the live feeds, at scale | — | Pro |
| AI CRM with bi-directional sync | — | Pro / Enterprise |
| CRM connectors (HubSpot, Pipedrive) | — | Enterprise |
| SSO, MFA | — | Enterprise |
| White-label, self-host support contract, SLAs | — | Enterprise (custom) |

The register is the free tier's substance: it is published weekly by the state
mapping office and, since 13 February 2026, it is free of charge for everyone —
so charging for it would be selling a public record behind a paywall. What the
hosted tier sells is what the register is not: live listing feeds, in more
countries, with the CRM around them.

**Free `$0`** · **Pro `$29/mo`** · **Enterprise (custom)** — the tiers reflect the
public roadmap and may move before launch.

[PropVector AI](https://propvectorai.com) is launching soon; the landing
page ships alongside billing. The fastest way to reach the maintainer today
is to [open a Discussion](https://github.com/AleksNeStu/ai-real-estate-assistant/discussions)
with the `[Commercial]` prefix.

### More from the studio

The same team builds these.

| | |
|---|---|
| **[PropVector AI](https://propvectorai.com)** | The hosted version of this project — live data, accounts, AI CRM, enterprise tiers. |
| **[EU AIGap](https://euaigap.co)** | EU AI Act self-assessment for teams that ship AI: classify a system, find the gaps, export the documents. |
| **[NestLab Tech](https://nestlab.tech)** | The studio itself — workflow automation, custom AI software and EU AI Act readiness for clients. |
| **[CheckCV](https://checkcv.co)** · **[TuneCV](https://tunecv.co)** | AI resume analysis and ATS optimisation. |
| **[PoznajSiebie](https://poznajsiebie.pl)** | Self-knowledge through attachment styles — in Polish. |

### Ideas, forks, and other ways to work with us

The backlog of this repository is written in the open, and suggestions are read
and used — a feature request, a provider we do not support yet, a language we
have not translated, a bug you hit while running it on your own server. All of
it is welcome, and none of it needs to be filed as a formal proposal first.

- **Suggest something** — [open an issue](https://github.com/AleksNeStu/ai-real-estate-assistant/issues).
  Ideas, use cases, "I wish it did X" are all legitimate issues.
- **Build on top of it** — fork it, change it, ship it under your own name. The
  licence is MIT; you do not need to ask.
- **Talk to us first** — a [Discussion](https://github.com/AleksNeStu/ai-real-estate-assistant/discussions)
  is the right place for a feature you would like to shape, a deployment you
  would like help with, or a partnership.
- **Work with the studio** — NestLab Tech builds products like this one for
  clients: [workflow automation, custom AI software, EU AI Act readiness](https://nestlab.tech/services?utm_source=github&utm_medium=referral&utm_campaign=product_showcase&utm_content=readme).
<!-- HOSTED-FUNNEL-END -->

## Questions people actually ask

**Can I run it on my own server?**
Yes — that is what the project is for. One compose file, or let this
repository's CI do it: give the [self-host deploy workflow](.github/workflows/deploy-selfhosted.yml)
a key and an address as repository secrets, and every release tag rolls your
machine onto the new images. See [Deploy it your way](#deploy-it-your-way).

**Do I need a paid API key?**
Not to look around. The demo answers with a model we pay for, so it costs
nothing to explore, and a local model takes over when the hosted one is
unreachable. For real answers you bring your own key — any of `17` providers, or
a local Ollama — and the app falls back to the next one when a provider fails.

**What is the difference to the hosted version?**
The engine is the same. The hosted tier adds live listing feeds, in more
countries, and the CRM around them — bi-directional sync, connectors, SSO/MFA,
white-label and SLAs — see [PropVector AI](https://propvectorai.com).

**Which languages?**
Nine in the interface: English, Polish, Russian, German, Spanish, Italian,
Portuguese, Turkish and Ukrainian. The documentation is English-first.

**Is the data mine?**
Yes, for anything you run yourself: SQLite plus a ChromaDB index on a volume
you own, in your country, behind your own authentication.

**Can I use it commercially?**
MIT. Fork it, change it, ship it. The hosted version is the commercial path
for teams that want the managed pieces instead of running the stack.

## Documentation

| Doc | Description |
|---|---|
| [5-minute quickstart](docs/development/QUICKSTART_5MIN.md) | The shortest path from a clone to a running app |
| [Deployment guide](docs/deployment/DEPLOYMENT.md) | Docker, Kubernetes, the self-host stack and the CI deploy |
| [Architecture](docs/architecture/large-saas-overview.md) | System design, data flow, deployment |
| [API reference](docs/api/API_REFERENCE.md) | All endpoints with examples |
| [User guide](docs/user/USER_GUIDE.md) | How to use the assistant |
| [Testing guide](docs/testing/TESTING_GUIDE.md) | Writing and running tests |
| [Contributing](CONTRIBUTING.md) | Development workflow |
| [Security policy](SECURITY.md) | Reporting and hardening |
| [Changelog](CHANGELOG.md) | Version history |

## Testing

```powershell
.\scripts\testing\test-fast.ps1     # quick test (3-5 min), during development
.\scripts\testing\test-ci.ps1       # full CI (8-12 min), before a commit
```

```bash
./scripts/testing/test-fast.sh      # the same, on Linux and macOS
./scripts/testing/test-ci.sh
```

Backend: pytest with xdist and a coverage gate that can fail — 84 % for the
unit suite, 50 % for the integration suite, and the coverage of the files a
change touches on top of that. Frontend: Jest, with a coverage gate over the
whole frontend — the library layers, the components and the pages — and a
separate floor for each of them. Security: Gitleaks, Semgrep, Bandit,
Trivy, CodeQL. Full details in the
[testing guide](docs/testing/TESTING_GUIDE.md).

### What the pipeline runs

| Suite | Where it runs | What it proves |
|---|---|---|
| `backend-e2e` | every push and pull request | the backend's end-to-end suite: the real application, the real middleware stack, the API-key contract |
| `compose-stack` | every push and pull request | the same suite against the stack the pipeline builds — the seeded catalogue and the local mock provider (so no key and no answer leaves the runner): it proves the transport and the app's behaviour, not the provider |
| `backend-resilience` | every push and pull request | the fallback chain and the degradation answer, proved with a provider that fails locally — no outage, no key |

### What the pipeline proves about the model

**A green pull request says nothing about which provider answers.** The
pull-request suite mocks the provider, so it proves the transport, the
middleware and the app's behaviour — not the model behind them. No job in
the pull-request pipeline carries a provider key, so a key that no longer
authenticates does not turn the pipeline red.

**The demo's real-model claim has its own proof.**
`apps/api/tests/e2e_backend/test_real_provider.py` asks the stack a
question the mock cannot answer and asserts three things: the answer is
not one of the mock's four canned sentences, the answer is not empty, and
the arithmetic result is in it. It also reads
`GET /api/v1/capabilities` and asserts that the deployment reports a
provider and not the mock. `MockLLM` picks a random line out of four
fixed strings and ignores the question, so it cannot pass those
assertions by construction — and the spec proves that as a property, in
its own negative control, without a second stack and without swapping
anything.

**The proof is opt-in, so the pull-request job stays green.** It runs
only where two things are true: a backend is named
(`E2E_BASE_URL`) and that backend promises a real model
(`E2E_REQUIRE_REAL_PROVIDER=1`). The `compose-stack` job names a
backend but runs the mock, so the proof skips there rather than failing
the pipeline.

**Running it costs nothing and needs no secret.** The proof runs against
the compose stack with a real provider configured — a local Ollama by
default, which is a real model with no key and no bill:

```bash
make e2e-real-provider
```

**The paid nightly job is not built.** A scheduled CI run against a hosted
provider would be the strongest proof, but it spends the studio's key and
needs a repository secret. That is the operator's call, not the
repository's, so the spec is written to run there when that job exists —
and the local run above needs neither.

### What the pipeline does not run

The p95 and the load suites are **not** in the pull-request path, and that is a
decision rather than an omission: a percentile measured on a shared runner is a
measurement of the runner, not of the product, and a suite that fails on the
runner's load is a suite nobody reads.

They run on demand, against a backend you name:

```bash
make perf-budget          # the budget the product is measured against
make benchmark-search     # the search p95
make benchmark-chat       # the chat p95
make load-test            # the concurrent load
```

`PERF_BASE_URL` says which backend to measure
(`make benchmark-search PERF_BASE_URL=http://localhost:8082` for the compose
stack). The budget is **search p95 ≤ 2.0 s, chat p95 ≤ 8.0 s, health p95 ≤
0.1 s, success rate ≥ 99 %**. The backend under measurement needs its rate
limit above the suite's request count (`API_RATE_LIMIT_RPM`) — otherwise the
suite measures the limiter, and says so.

## Contributing

Contributions are welcome — see [CONTRIBUTING.md](CONTRIBUTING.md) for the
workflow, and the [code of conduct](.github/CODE_OF_CONDUCT.md) for the terms.

1. Fork → `git checkout -b feature/short-description`
2. Run the checks locally (`make ci`)
3. Commit: `type(scope): message`
4. Open a PR against `dev`

`dev` is the working branch, `main` is the stable one.

## License

MIT — see [LICENSE](LICENSE).

## Support

If this project saved you a weekend, you can say so here:

[![GitHub Sponsors](https://img.shields.io/badge/GitHub%20Sponsors-Sponsor-ea4aaa?style=for-the-badge&logo=githubsponsors&logoColor=white)](https://github.com/sponsors/AleksNeStu)
[![Buy Me a Coffee](https://img.shields.io/badge/Buy%20Me%20a%20Coffee-Support-ffdd00?style=for-the-badge&logo=buymeacoffee&logoColor=000000)](https://www.buymeacoffee.com/AleksNeStu)
[![Ko-fi](https://img.shields.io/badge/Ko--fi-Support-ff5f5f?style=for-the-badge&logo=kofi&logoColor=white)](https://ko-fi.com/AleksNeStu)

**Commercial and partnership work** — deployment help, customisation, CRM
integration, or building the next version together — goes through the studio
that maintains this project:

<div align="center">

**[NestLab Tech](https://nestlab.tech?utm_source=github&utm_medium=readme&utm_campaign=support&utm_content=readme)** ·
[Services](https://nestlab.tech/services?utm_source=github&utm_medium=readme&utm_campaign=support&utm_content=readme) ·
[PropVector AI](https://propvectorai.com?utm_source=github&utm_medium=readme&utm_campaign=support&utm_content=readme)

</div>

Or open a [Discussion](https://github.com/AleksNeStu/ai-real-estate-assistant/discussions)
with the `[Commercial]` prefix and it reaches the same team.

---

<div align="center">

**Star this repo if you find it helpful — it is what makes the next version possible.**

Made with Python, FastAPI and Next.js.

Copyright © 2025-2026 [Alex Nesterovich](https://github.com/AleksNeStu)

</div>
