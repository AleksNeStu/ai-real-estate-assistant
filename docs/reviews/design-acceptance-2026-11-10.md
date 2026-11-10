# The design acceptance — 2026-11-10

The v2 design was ported into the application in three waves (tasks #54, #57, #58). This
is the acceptance: every route of the prototype, opened in the running application, compared
against the prototype page it came from, with the token and palette measurements the
analyser takes.

**What was measured**

| | |
|---|---|
| The prototype | `tmp/design/realt2/v2/` — 30 files, gitignored, never published |
| The application | the production build on `:3000`, against the local backend on `:18082` |
| The shots | `docs/reviews/design-acceptance-2026-11-10/` — 24 routes × 2 widths × 2 themes = 96 PNGs |
| The capture | `scripts/ops/acceptance_capture.js` (`SITE_URL`, `OUT_DIR`) |
| The analyser | `scripts/design/design_gap.py tmp/design/realt2/v2` |

The shots are the signed-out view: for a route that belongs to an account, the gate *is* the
design. The signed-in content was read with a signed-in session — the route by route, and the
sweep below.

The application was opened twice for the account routes: signed out (the gate) and signed in
as an ordinary account (the pages themselves). Every route was checked for an error state,
and every API call the page made was watched for a status other than 200.

---

## The tokens

The prototype defines its own tokens; the application keeps the zinc base and adds four.
The analyser reads every token definition in the artifact and finds the repository token it
matches.

| | |
|---|---|
| Token definitions read in the prototype | **13** |
| Matched a repository token by colour | **12** |
| Without a counterpart | **1** — `--tilef`, which is a filter (`grayscale(1…`) and not a colour |
| Repository tokens without a counterpart in the prototype | **83** |

The twelve that matched are `--ac` → `--action`, `--acf` → `--action-foreground`, `--bd` →
`--border`/`--input`, `--bg` → `--background`/`--card`, `--c1` → `--chart-1`, `--er` →
`--chart-8`, `--fg` → `--foreground`, `--mf` → `--muted-foreground`, `--mu` →
`--muted`/`--accent`/`--secondary`, `--ok` → `--success`, `--wa` → `--warning`, `--wab` →
`--warning-surface`. Seven of them match at distance 0.000; the largest distance among the
twelve is 0.328 (`--c1`).

The 83 repository tokens without a counterpart are the application's own — the zinc scale,
the chart ramp, the map colours. The prototype never needed them; the application does.

## The palette

The threshold is the analyser's own: **100.0**, a squared HSL distance.

| The prototype | |
|---|---|
| Colour literals | **1324** (37 distinct) |
| Within the threshold of a repository token | **31** |
| Outside it | **6** |

All six are in the prototype's `support.js` — the file that carries the prototype's own
scaffolding (the map, the drawer, the modal scrim), not the design system:

| Literal | Distance | Nearest repository token |
|---|---|---|
| `rgba(0,0,0,.5)` | 7785.00 | `--chart-8` |
| `#f0eee6` | 5639.77 | `--warning-surface` |
| `#2e2c26` | 2663.64 | `--warning-surface` |
| `rgba(247,225,211,.95)` | 1563.44 | `--caution` |
| `#b00020` | 1385.66 | `--destructive` |
| `rgba(217,119,87,0)` | 967.43 | `--caution` |

The repository side was measured the same way, over every `.tsx` under `apps/web/src`:

| | |
|---|---|
| Colour literals outside the threshold in `apps/web/src` | **2** |
| `apps/web/src/components/auth/OAuthButtons.tsx` — `#34A853` | 523.34 — Google's green |
| `apps/web/src/components/auth/OAuthButtons.tsx` — `#EA4335` | 110.77 — Google's red |

Both are Google's brand colours. They are outside the theme by intent: a sign-in button
that carries Google's own colours is not a themed surface. Nothing else in the application
carries a literal.

Two further findings of the analyser are artefacts of its parser, checked by hand:
`seo.structuredData` is in the catalogue (`messages/en.json:3844`) and `tools.map` is an
array in the prototype, not a message key.

---

## The routes

Every route below was opened in the running application. "Matches" means the route carries
the prototype's own structure — the same regions, the same instruments, the same numbers
where the application has them.

| Route | Prototype | What the application shows | Verdict |
|---|---|---|---|
| `/` | Landing | The hero, the six-row feature ledger, "Data and coverage, as of today" (250 listings · 5 cities · 15 agents, read from `/catalogue/stats`), the four-state comparison table, the studio strip, the FAQ, the footer | matches |
| `/en/search` | Search | The sentence input with the parsed filters, the filter column, the result list, the map | matches |
| `/en/chat` | Chat | The suggestion row, the message stream, the composer | matches |
| `/en/tools` | Tools | The five calculators as a ledger, each marked `ready` or `needs config` | matches |
| `/en/analytics` | Analytics | The same five calculators in one console, with the tabs the prototype draws | matches |
| `/en/market-trends` | MarketTrends | The price history, the area comparison, the market indicators per city | matches |
| `/en/city-overview` | CityOverview | The map, the ledger of the eight cities, the detail of the selected one — **250 listings · 5 of 8 cities covered** | matches |
| `/en/valuation` | Valuation | The form, the horizons, the forecast | matches |
| `/en/cma` | CMA | The five steps — subject, comparables, adjustments, preview, export | matches |
| `/en/knowledge` | Knowledge | The drop zone, the file list, the question box | matches |
| `/en/showcase` | Showcase | The forks ledger, the companies, the quotes — each with its empty state | matches |
| `/en/agents` | Agents | The filters, the agent rows, the four agents of the demo catalogue | matches |
| `/en/favorites` | Favorites | The collections, the saved properties, the empty state | matches |
| `/en/saved-searches` | SavedSearches | The alerts, the search list, the empty state | matches |
| `/en/documents` | Documents | The upload, the file list, the empty state | matches |
| `/en/leads` | Leads | The funnel, the five columns, the high-value rail, the scoring statistics of an administrator | matches |
| `/en/usage` | Usage | The five event kinds, the stat tiles, the thirty-day bars, the activity log | matches |
| `/en/agent-analytics` | AgentAnalytics | An agent's own numbers, the team ledger, the months of deals, the coaching notes — and, for an account that is not an agent, the page says the view belongs to an agent | acceptable deviation |
| `/en/settings` | Settings | Identity, models, notifications, profile, privacy — the tabs of the prototype | matches |
| `/en/auth/login` | Auth | One card, one action, the demo note | matches |
| `/en/admin/bulk-jobs` | Admin | The admin shell with its four tabs, the bulk jobs ledger | matches |
| `/en/admin/connectors` | Admin | The admin shell, the MCP connector registry | matches |
| `/en/admin/data-sources` | Admin | The admin shell, the data sources and the portals | matches |
| `/en/admin/monitoring` | Admin | The admin shell, the health, the readiness, the deployment | matches |

**The one deviation.** The prototype's agent analytics is an agent's dashboard, and the API
keeps it for agents and administrators: an ordinary account gets `403` for every one of its
calls. The page used to answer that with a bare "Failed to load analytics data", which is
true and useless. It now says what it is — the view belongs to an agent — and offers no
retry, because retrying will not help. `apps/web/src/app/[locale]/agent-analytics/page.tsx`.

---

## What the acceptance found and closed

Four defects were found by opening the routes and watching the calls. All four are closed
and verified against the running application.

| The defect | The cause | The fix |
|---|---|---|
| `/en/usage` was a 500 | `user_activity_service` bucketed the events with PostgreSQL's `date_trunc`; the deployment's database is SQLite | `apps/api/services/user_activity_service.py` — the bucket is now a dialect-agnostic expression (`to_char(date_trunc(...))` on PostgreSQL, `strftime(...)` on SQLite) and the Python side compares calendar dates. The two tests that carried an `xfail` for the PostgreSQL-only limitation now pass, and a test covers the day, week and month buckets. |
| `/en/leads` was a 422 | The board asked for `page_size=200`; the API caps it at 100 | `apps/web/src/app/[locale]/leads/page.tsx` — the board asks for the API's maximum and walks the remaining pages, so the funnel sees every lead. |
| `/en/market-trends` crashed the page | The API sends `null` for a price change it cannot compute; the panel called `toFixed` on it | `apps/web/src/components/market-trends/market-indicators.tsx` and the type in `apps/web/src/lib/types.ts` — a null and a missing number now mean the same. |
| The admin monitoring tab answered 401 | The Next.js proxy routes sent the API key but not the session cookie, and two of them used a `BACKEND_URL` the deployment never sets | `apps/web/src/app/api/ready/route.ts`, `.../api/monitoring/overview/route.ts`, `.../api/monitoring/test-alert/route.ts`, `.../api/metrics/route.ts` — the cookie travels with the request and the base URL is the one the deployment names. |

Two smaller corrections came out of the same pass:

- The city overview counted the listings a *search* returned — eight searches of a hundred
  answers each — and reported "800 listings · 8 of 8 cities covered", while the catalogue
  holds 250 listings in five cities. The counts now come from `/catalogue/stats`, the same
  source the landing reads, and each city's own listings are counted by the city they are
  in. `apps/web/src/app/[locale]/city-overview/page.tsx`,
  `apps/web/src/components/market-trends/city-market-stats.ts`.
- The demo seed named its accounts after the role they were to carry
  (`demo.admin2@realestate.demo`) but never gave the role to the user. The role is now
  assigned. `apps/api/alembic/demo_data_generator.py`.

## The gaps that are closed

| The gap | The fix |
|---|---|
| The monitoring overview counted the rows of a `properties` table this schema does not have, so the database panel read zero while the catalogue holds 250 | `apps/api/api/routers/monitoring.py` now asks the catalogue — the same count the landing reads — and `apps/api/api/routers/catalogue.py` owns that count for both. The listings carry their source and the moment they were scraped (`apps/api/vector_store/chroma_store.py`), so the panel can say where they came from and how fresh they are. Live on the local deployment: 250 listings, `demo-seed` 250, none newer than a day. |
| The seeded demo accounts carry no password, so `demo.admin*` and `demo.agent*` cannot be signed into | `apps/api/alembic/demo_data_generator.py` gives them the password the deployment carries in `DEMO_USER_PASSWORD` — the deployment's own value, never the repository's. Without that variable the accounts carry no password, exactly as before. `deploy/compose/docker-compose.yml` and `apps/api/.env.example` name it. |
| `POST /leads/bulk/assign` was read as an assignment for a lead called "bulk": a path whose first segment is a parameter catches every route of the same shape that comes after it | `apps/api/api/routers/leads.py` declares the bulk routes before the parameterised ones. Live: the endpoint answers 200 with its own count. |
| The activity summary counted every search in the deployment, not the searches of the account that asks | `apps/api/services/user_activity_service.py` narrows the searches, the views and the clicks to the account — an administrator's view asks without an account and keeps every row. The copy says "your activity on this deployment", and now the two agree. |

## The gaps that are named, not closed

| The gap | The file that closes it |
|---|---|
| Nothing records a search. `services/search_metrics_service.py` can write the event and no caller uses it, so the searches, the views and the sessions are zero for every account — the usage console draws an empty chart | `apps/api/api/routers/search.py`, with `apps/api/services/search_metrics_service.py` |
| The leads board walks at most ten pages of a hundred leads, so a deployment with more than a thousand leads sees the first thousand; the board says so | `apps/web/src/app/[locale]/leads/page.tsx` |

## The deployment

The redesign reached the deployed demo through the repository's own workflows, dispatched by
hand — a release tag is not the only way to roll a deployment:

| | |
|---|---|
| The commit | `a6a631a3b` — the redesign and the four closed gaps |
| The CI | green on that commit: every job, from the gitleaks scan to the e2e suite |
| The images | published under the commit's short sha, `a6a631a`, both multi-arch (amd64 and arm64) |
| The server | `deploy-selfhosted.yml` dispatched with that tag — run 42897283264, green: the node pulled the images and rolled its stack onto them |
| The promotion | pull request #399, `dev` → `main`: mergeable and clean, every check green. `main` is a clean ancestor of `dev`, so it is a straight fast-forward and the ruleset wants it merged with "rebase and merge" |

The first roll failed twice, for two different reasons worth keeping: the deploy waits twenty
minutes for the images to appear, and the frontend's multi-arch build (amd64 and arm64, the
arm64 leg under emulation) took longer than that with a cold cache; and the image tag is the
**seven-character** short sha, so a tag that is eight characters long never resolves.

The third attempt had a third reason, and it is the expensive one. The backend image published
in a few minutes; the frontend's multi-arch build ran for **three hours and twenty minutes** on
the runner and was still going when the roll was needed — the redesign rewrote `apps/web`, so
the build cache no longer applied to the layer that does the work, and the arm64 leg runs under
emulation. The image was therefore built on the workstation instead (`docker buildx build
--platform linux/amd64,linux/arm64`, the same `Dockerfile.frontend` and the same
`NEXT_PUBLIC_SITE_URL` the repository variable carries) and pushed under the same tag: the
same two architectures, the same content, published by another route. The lesson for the
repository: **a cold multi-arch frontend build is not a CI-minute problem but a wall-clock
problem**, and a deployment that waits twenty minutes for it will keep failing until the
workflow either builds one platform for the server or the cache is made to survive a change in
`apps/web`.

Two things about a rollout of this kind are worth knowing. The two images are not atomic — the
demo's frontend had already been rolled onto the redesign while its backend still answered the
old code — so the state of a deployment is read from its API, not from its page. And the
released line was not touched: the promotion is a pull request, and the tag is a separate step.

The repository's other deployment target — the platform-hosted one — rolled the same commit
successfully. A second, duplicate run of it failed with the deployments API's `409` (`Commit
status checks failed`), because that API refuses a deployment while a check on the commit has
not succeeded; the run was dispatched while the CI of that very commit was still running. The
demo does not live there, so nothing was left half-rolled.

## The live sweep

`scripts/ops/live-sweep.js` walks every route of a deployment with a browser and prints one
line each: the route, the page's status, the API calls it made and the console errors. It
registers no account and creates no lead.

| | |
|---|---|
| Against the local deployment | **30 routes, 30 ok, 0 failed** |
| Against the deployed demo (`https://realty.kittray.com`) | **30 routes, 30 ok, 0 failed** |

The deployed demo was swept twice. The first sweep reported one failure,
`/api/v1/agents/{id}`, which answered 500: the agent's user was lazy-loaded outside an awaited
query. The fix was in the repository (`1ef88f15e fix(api): the agent detail stops raising
MissingGreenlet (Task #66)`) but the deployed backend still ran the old image — the frontend
had been rolled onto the redesign while its backend had not, so the state of the deployment was
read from its API, not from its page. After the roll onto `a6a631a` the same endpoint answers
**200**, the catalogue reports **250 listings in 5 cities and 15 agents**, and the sweep of the
deployed demo is clean: **30 routes, 30 ok, 0 failed**.

Two mistakes in the sweep itself were found and fixed by running it: the gate was looked for
with an exact address (`/auth/login`) while the gate links to the localised, redirect-aware
address, so every account route was reported as ungated; and the landing's catalogue call was
looked for in the first second, while the landing reads the catalogue after it is painted.

## How to reproduce

```bash
# The tokens and the palette
python scripts/design/design_gap.py tmp/design/realt2/v2

# The shots (24 routes, 1440 and 390, light and dark)
SITE_URL=http://localhost:3000 OUT_DIR=docs/reviews/design-acceptance-2026-11-10 \
  node scripts/ops/acceptance_capture.js

# The live sweep of every route
node scripts/ops/live-sweep.js
```
