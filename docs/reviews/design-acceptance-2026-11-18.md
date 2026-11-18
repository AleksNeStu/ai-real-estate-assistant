# The design acceptance — 2026-11-18

The v2 design was ported into the application in three waves (tasks #54, #57, #58) and accepted on
2026-11-10. Since then the application moved: the end-to-end suite learned the new design
(waves 64–66), the phone and the tablet widths were tested and the priced row and the phone menu
were fixed (Task #91), the public map states the price on every pin (Task #95), and the Compose
stack was repaired so it starts.

This is the acceptance of that state: every route of the prototype, opened in the running
application, compared against the prototype page it came from, with the token and palette
measurements the analyser takes and the accessibility the axe-core gate now proves.

**What was measured**

| | |
|---|---|
| The prototype | `tmp/design/realt2/v2/` — 30 files, gitignored, never published |
| The application | the current `dev` commit, built and running in the repository's own Docker Compose stack |
| The shots | `docs/reviews/design-acceptance-2026-11-18/` — 24 routes × 2 widths × 2 themes = 96 PNGs |
| The capture | `scripts/ops/acceptance_capture.js` (`SITE_URL`, `OUT_DIR`) |
| The analyser | `scripts/design/design_gap.py tmp/design/realt2/v2` |
| The live sweep | `scripts/ops/live-sweep.js` — 30 routes, the API calls each made, the console errors |
| The accessibility | `e2e/accessibility/accessibility.spec.ts` — axe-core over 19 routes × 2 themes |

**How each verdict was reached.** Every route was opened in the running application and shot at
1440 and 390, in light and in dark. Each shot was then compared, pixel by pixel, with the
previous acceptance's shot of the same route: **20 of the 96 are identical to 2026-11-10**, and the
76 that changed were read against the prototype. Three things account for the change, and none of
them is a layout that moved:

| The change | Where it shows |
|---|---|
| The maps draw their tiles — on 2026-11-10 they were empty canvases | the city overview changed most (42–52 % of its pixels), the search page 14–16 %, the landing 10–12 % |
| The footer's last line changed — "The hosted version is in development by NestLab" became "in deployment by" — which shifts the waitlist block above it | the same band on every page, 2.3–2.5 % of its pixels |
| The muted text and the status colours moved to their AA shades | the rest, in the text |

A route whose shot did not change keeps the verdict it had; a route whose shot changed was judged
again.

---

## The tokens

The prototype defines its own tokens; the application keeps the zinc base and adds four. The
analyser reads every token definition in the artefact and finds the repository token it matches.

| | 2026-11-10 | 2026-11-18 |
|---|---|---|
| Token definitions read in the prototype | 13 | 13 |
| Matched a repository token by colour | 12 | 12 |
| Without a counterpart | 1 — `--tilef`, the CSS filter the prototype puts on the map tiles. It is not a colour; the repository applies the same filter in code (`components/ui/map-tile-theme.tsx`), not as a token | the same |
| Repository tokens without a counterpart in the artefact | 83 | 83 |

The twelve that matched are `--ac` → `--action`, `--acf` → `--action-foreground`, `--bd` →
`--border`/`--input`, `--bg` → `--background`/`--card`, `--c1` → `--chart-1`, `--er` →
`--chart-8`, `--fg` → `--foreground`, `--mf` → `--muted-foreground`, `--mu` →
`--accent`/`--muted`/`--secondary`, `--ok` → `--chart-2`/`--success`, `--wa` → `--warning`, `--wab`
→ `--warning-surface`. The largest distance among the twelve is 91.2 (`--ok`, the status green) and
the threshold is 100.

**Two of the tokens moved, and why.** The status colours sat at the 600 shade of their hue — the
prototype's own values — and a 600-shade green or red as small text is 3.0–3.8:1, below AA. The
acceptance's own analyser had a reason to keep them: `--er` and `--ok` are the prototype's tokens,
and a token that moves away from the prototype's colour stops matching it. Both moved inside the
threshold instead: `--success`, `--destructive` and `--caution` moved to the 700 shade of the same
hue, and the chart ramp followed the status green as it already followed `--info`. The prototype's
`--ok` and `--er` still match repository tokens by colour, inside the threshold, so the design has
not drifted — the tokens are darker, and they now read.

The contrast, measured:

| The token | On the page | On the muted panel | Before |
|---|---|---|---|
| `--muted-foreground` | 5.06:1 | 4.60:1 | 4.83 / 4.40 |
| `--success` | 5.42:1 | 4.93:1 | 3.33 / 3.03 |
| `--destructive` | 6.12:1 | 5.57:1 | 3.76 / 3.42 |
| `--caution` | 5.43:1 | 4.94:1 | 3.62 / 3.29 |
| `--warning` | 5.05:1 | 4.59:1 | unchanged |

The dark theme was measured too: its status colours run from 5.4:1 to 11.8:1 on the page and from
5.4:1 to 8.8:1 on the muted panel — no change was needed there.

## The palette

The threshold is the analyser's own: **100.0**, a squared HSL distance.

| The prototype | |
|---|---|
| Colour literals | **1305** (29 distinct) |
| Within the threshold | **27** |
| Outside it | **2** |

Both are in the prototype's own `support.js` — the file that carries the prototype's scaffolding,
not the design system. **No v2 page carries a literal outside the threshold**, which is the
criterion the acceptance uses.

The repository side was measured the same way: the literals live in `apps/web/src/lib/palette.ts`
and nowhere else, and the jest suite asserts each one equals the token it claims.

---

## The routes

Every route below was opened in the running application. "Matches" means the route carries the
prototype's own structure — the same regions, the same instruments, the same numbers where the
application has them.

| Route | Prototype | What the application shows | Verdict |
|---|---|---|---|
| `/` | Landing | The hero, the six-row feature ledger, "Data and coverage, as of today" (read from `/catalogue/stats`), the four-state comparison table, the studio strip, the FAQ, the footer — and the hero instrument, whose map now draws its tiles and states the price on every pin | matches |
| `/en/search` | Search | The sentence input with the parsed filters, the filter column, the result list, the map — with the tiles painted. The row states the listing in text where the prototype's row carries a picture | acceptable deviation |
| `/en/chat` | Chat | The suggestion row, the message stream, the composer — at 1440 and at 390 | matches |
| `/en/tools` | Tools | The five calculators as a ledger, each marked `ready` or `needs config` | matches |
| `/en/analytics` | Analytics | The same five calculators in one console, with the tabs the prototype draws | matches |
| `/en/market-trends` | MarketTrends | The price history, the area comparison, the market indicators per city | matches |
| `/en/city-overview` | CityOverview | The map — with its tiles painted — the ledger of the eight cities, the detail of the selected one | matches |
| `/en/valuation` | Valuation | The form, the horizons, the forecast — and the form's fields are named | matches |
| `/en/cma` | CMA | The five steps — subject, comparables, adjustments, preview, export | matches |
| `/en/knowledge` | Knowledge | The drop zone, the file list, the question box | matches |
| `/en/showcase` | Showcase | The forks ledger, the companies, the quotes — each with its empty state | matches |
| `/en/agents` | Agents | The filters, the agent rows, the agents of the demo catalogue | matches |
| `/en/favorites` | Favorites | The collections, the saved properties, the empty state | matches |
| `/en/saved-searches` | SavedSearches | The alerts, the search list, the empty state | matches |
| `/en/documents` | Documents | The upload, the file list, the empty state | matches |
| `/en/leads` | Leads | The funnel, the columns, the high-value rail | matches |
| `/en/usage` | Usage | The five event kinds, the stat tiles, the bars, the activity log | matches |
| `/en/agent-analytics` | AgentAnalytics | An agent's own numbers, the team ledger, the months of deals — and, for an account that is not an agent, the page says the view belongs to an agent | acceptable deviation |
| `/en/settings` | Settings | Identity, models, notifications, profile, privacy — the tabs of the prototype | matches |
| `/en/auth/login` | Auth | One card, one action, the demo note | matches |
| `/en/admin/bulk-jobs` | Admin | The admin shell with its four tabs, the bulk jobs ledger | matches |
| `/en/admin/connectors` | Admin | The admin shell, the MCP connector registry | matches |
| `/en/admin/data-sources` | Admin | The admin shell, the data sources and the portals | matches |
| `/en/admin/monitoring` | Admin | The admin shell, the health, the readiness, the deployment | matches |

**The two deviations.** The prototype's agent analytics is an agent's dashboard, and the API keeps
it for agents and administrators: an ordinary account gets `403` for every one of its calls. The
page says what it is — the view belongs to an agent — and offers no retry, because retrying will
not help. `apps/web/src/app/[locale]/agent-analytics/page.tsx`.

The prototype's search row opens with a picture of the listing. The application's row states the
listing in text — the title, the address, the facts, the price, the monthly cost and the price per
m², in mono — and the demo catalogue holds no photographs to draw. The search ledger draws no empty
cell for a picture it does not have; the agent ledger, whose catalogue entries do carry pictures,
draws the cell. This is the same deviation the acceptance of 2026-11-10 accepted, and it is
written down here rather than passed over.

---

## What the acceptance found, and closed

| The defect | The cause | The fix |
|---|---|---|
| The maps drew no tiles in the shots — the search map and the city overview were empty canvases | the capture shot the page 2.5 seconds after it loaded, and Leaflet fetches its tiles afterwards — from a tile host that answers in ten seconds or more | `scripts/ops/acceptance_capture.js` now waits for the tiles the map asked for, and reports what it found (`map:12/12 tiles`); the shots show the maps a visitor sees |
| The tiles the map asked for came back `408`, and the map painted none of them | the browser resolves IPv6 first, and this machine's IPv6 path is broken: the request to the tile host stalls and the host answers `408` instead of the tile. The same URLs answer `200` over IPv4, and `curl -6` fails to connect at all | `scripts/ops/acceptance_capture.js` — the browser is put on the address family that works here, because the shot is about the application and the network's answer is not the application's |
| The third map in a pass was refused even over IPv4 — its tiles came back `408` while the same route painted them in a browser of its own | the tile host refuses a browser session that has already asked for tiles: measured, the first map in a pass painted, the second was refused, the third was refused outright | `scripts/ops/acceptance_capture.js` — a map route gets a browser context of its own; the routes without a map still share one |
| The design analyser crashed on the prototype | the prototype's `theme.css` explains itself in a comment — "the pages keep their historical literals inside `var(--token, #hex)`" — and the analyser read the prose as a token definition, then failed on a value that is not a colour | `scripts/design/design_gap.py` strips the comments and returns nothing for a value that is not hex |
| The status colours failed AA as small text — 32 nodes | the tokens sat at the 600 shade of their hue, the prototype's own values | the tokens moved to the 700 shade of the same hue; the contrast table above is the measurement |
| The accessible names left out the text the reader sees — 37 nodes | the language switcher's name left out the code it shows, and the user menu's name left out the account it shows; the initials and the account's name were one word in the DOM | `components/ui/language-switcher.tsx`, `components/auth/UserMenu.tsx` |
| Six fields of the valuation form had no name | the `Field` component rendered a `<label>` without `htmlFor` | `app/[locale]/valuation/page.tsx` — the label is tied to the input |
| The stack could not start on a machine where a sibling product holds the ports | the Compose file hardcoded the host ports while its own `.env.example` documented `REDIS_PORT` and `POSTGRES_PORT` as variables | `deploy/compose/docker-compose.yml` — the host ports are variables now, the same way `POSTGRES_PORT` already was |
| The stack still bound a port another service held, though the file named a free one | Compose gives the shell precedence over `--env-file`, and `REDIS_PORT=6379` — the non-Docker stack's port — lives in the OS environment | `scripts/docker/start.ps1` — the ports are read from `deploy/compose/.env` and put into the process environment, so the file decides |
| The start script reported a healthy stack as still starting | its health check asked `8082` and `3082` while the stack answered on `8083` | `scripts/docker/start.ps1` — the health check probes the ports the stack published |
| The compose smoke probed a port that belonged to somebody else | it hardcoded the published ports, and it inherited the machine's `REDIS_PORT` — Compose gives the shell precedence over the file it reads | `scripts/docker/compose_smoke.py` — the URLs are built from the same variables the compose file reads, and the file's own `.env` decides the ports |

## The accessibility

The axe-core gate is new: `e2e/accessibility/accessibility.spec.ts` walks 19 routes in both
themes and holds them to WCAG 2.2 A/AA.

| | |
|---|---|
| Routes scanned | 19 × 2 themes |
| Violations found | **75** — 32 contrast, 37 name, 6 label |
| Violations left | **0** |

The gate runs inside the CI e2e job, so a violation fails the pipeline, and the job's summary
names the routes it scanned. The static half — the `jsx-a11y` rules — is on as well: it found 13
findings, all fixed. The full account is in `ACCESSIBILITY.md`.

## The contract, checked

`DESIGN.md` is the contract the code is measured against. The parts of it that a machine can read:

| The rule | The measurement |
|---|---|
| Never a raw hex, never `var(--color-*)` — the tokens have one address | the `design-tokens` ESLint rule over `src/**` — no finding; the literals live in `lib/palette.ts` alone, and a jest suite asserts each one equals its token |
| One container contract — the column measure belongs to the container, not to an ad-hoc cap | no page carries an ad-hoc `max-w-*` on its column; the `max-w-*` that remain are text blocks and the auth card, which the contract names |
| Radius 8 for panels and cards, 6 for controls, 4 for badges, 10 for the hero only | the radius tokens are the analyser's; no drift |
| The type scale as Tailwind tokens | the `--text-*` tokens are the analyser's; no drift |
| The focus ring is the accent | `--ring` is the teal of `--action`, and every interactive primitive uses it |
| The map's tiles are grey, and inverted in the dark theme | `components/ui/map-tile-theme.tsx` puts the filter on the tile pane, and the dark shots show the inverted map |

## The live sweep

`scripts/ops/live-sweep.js` walks every route of the deployment with a browser and prints one line
each: the route, the page's status, the API calls it made and the console errors. It registers no
account and creates no lead.

| | |
|---|---|
| Against the local deployment | **30 routes, 30 ok, 0 failed** |

## The gaps that are named, not closed

| The gap | Where it stands |
|---|---|
| The Mapbox path is dormant: the stack carries no `NEXT_PUBLIC_MAPBOX_TOKEN`, so the shipping map is the Leaflet one and the district choropleth (`components/search/district-boundary-layer.tsx`, `lib/district-aggregation.ts` — five hardcoded Warsaw rectangles) never draws | named, not built: the plan never had a token, and a feature the plan did not have is not built in an acceptance |
| The demo catalogue holds no photographs, so the search row states the listing in text where the prototype's row carries a picture | named as a deviation above: the component draws no empty cell for an image it does not have; the agent ledger, whose catalogue entries do have pictures, draws the cell |
| The tile host is a third party and it is slow: the tiles of a map that first drew at one zoom and then fitted its bounds arrive ten seconds or more after the page did | the capture waits for them and reports what it found; the e2e test separates "the map asked for nothing" (the product is broken) from "the host refused" (the network is) |
| The tile host is reached over IPv6 where the browser offers it, and this machine's IPv6 path is broken — the request stalls and the host answers `408` rather than failing fast, so the browser never falls back to IPv4 | the capture puts the browser on IPv4; the finding is in the report because the same machine will show an empty map in any browser until its IPv6 path is repaired — the application's own map code is not involved |
| The tile host refuses a browser session that has already asked for tiles — a third map in a pass is answered with `408` while the same route paints in a browser of its own | the capture gives a map route its own context; a visitor's own browser asks for one map's worth of tiles and is answered |

## How to reproduce

```bash
# the tokens and the palette
python scripts/design/design_gap.py tmp/design/realt2/v2

# the stack
pwsh scripts/docker/start.ps1

# the shots (24 routes, 1440 and 390, light and dark)
SITE_URL=http://localhost:3082 OUT_DIR=docs/reviews/design-acceptance-2026-11-18 \
  node scripts/ops/acceptance_capture.js

# the live sweep of every route
SITE_URL=http://localhost:3082 node scripts/ops/live-sweep.js

# the accessibility gate
PLAYWRIGHT_BASE_URL=http://localhost:3082 npx playwright test e2e/accessibility
```
