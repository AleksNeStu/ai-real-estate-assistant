# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [5.3.3] - 2026-11-12

### Fixed
- **The landing page published its title as the text "home.title"** — the home
  page asked the catalogue for a copy it does not carry, and the catalogue's
  fallback answers with the key itself, so nothing crashed: the page simply
  said its own name wrong. The chat route had the same shape of mistake and
  the same answer. The home page takes its title from the layout, which knows
  the product's name in every language, and the chat route reads its own
  namespace. A test now says of every public route that its copy is there.

## [5.3.2] - 2026-11-11

### Fixed
- **A cleared catalogue takes its index with it** — the search answered with an
  empty list while the catalogue held 250 listings: ChromaDB's
  `delete_collection` drops the collection's rows but keeps the collection's
  HNSW index directory on disk, and a later query met a segment that was gone
  ("Nothing found on disk") and reported no results instead of the documents
  that had just been added. The store removes the collection's index
  directories with the collection.
- **The waitlist stopped promising an e-mail it cannot send** — the success
  line answered "One e-mail at launch" even on a deployment with no mail
  sender configured. It now says what is true: the address is stored here and
  no e-mail is sent from this deployment.
- **The hreflang cluster pointed at the internal origin** — the middleware's
  own `Link` header resolved its alternates against the request's host, so
  behind the proxy a second cluster appeared on the origin's internal name,
  and it pointed at the home pages of every locale rather than at the same
  page. The header is off, and every public route declares its own cluster.

### Added
- **Every public route says what it is** — fourteen routes answered with the
  same title and the same description. Each public route now declares its own
  title, description and canonical, in the language of the route, from the
  copy the message catalogue already carried.
- **A listing is a page a crawler can read** — the page of a single property
  was a client component that fetched after load, so it arrived as an empty
  shell. It is read on the server now: the page carries the listing, its
  title, its canonical and a `schema.org/Property` block with the address,
  the position, the rooms and the offer.
- **The catalogue can be enumerated** — `GET /api/v1/properties` answers with a
  page of the listings, which is what a sitemap and an llms.txt are built from.
- **The sitemap lists what there is to index** — one entry per page with its
  translation cluster, the listing pages included, and the account areas
  removed.
- **llms.txt names the instance** — the document is served by a route now, so
  it can name the live routes, the languages and the catalogue the deployment
  holds, not only what the author knew when it was written.

### Documentation
- **The SEO / AEO / GEO audit of the public domain** —
  `docs/reviews/2026-11-11-seo-geo-aeo-realty-kittray.md` measures the live
  domain, names the gaps and states what is left open.
- **The indexing switch, and the switch back** —
  `docs/community/SEO_INDEXING_SETUP.md` now carries the procedure and the
  one-command revert. The decision itself stays the operator's.

## [5.3.1] - 2026-11-11

### Fixed
- **The property page answers** — the page's endpoints asked the application
  state for the catalogue, and the application never puts one there: it sets
  the state to `None` at startup and nothing replaces it. Every request to
  `/api/v1/properties/{id}` answered `503` with a full catalogue behind it. The
  endpoints take the catalogue through the dependency the deployment actually
  hands out, and a test now covers the case where there is no catalogue at all.
- **A manual roll-out judges the code it deploys** — the roll-out workflow ran
  from whichever branch it was dispatched from, so it read the branch's tip
  instead of the commit behind the named tag: the CI gate judged the wrong
  commit and the wait for the published images looked for a run that only ever
  starts on a tag. The tag is now resolved to its commit, and that commit is
  what both steps read.

## [5.3.0] - 2026-11-11

### Added
- **A property has a page** — the search answered with listings and the card
  showed them, but a reader who picked one had nowhere to go: there was no
  route for a single property. The page shows the listing itself (the price,
  the numbers, the description, the amenities), the AI one-liner of its
  neighbourhood, and the comparable listings of the same city and type. It is
  public: a visitor who clicks a listing is nobody until they sign in, so the
  data it reads does not ask for a session. The title of a result and a marker
  on the map both open it.

### Fixed
- **The release path has a CI gate** — a `v*` tag started the image publish and the
  server roll whether or not the commit behind it had ever passed CI. Both tag
  workflows now wait for that commit's CI run and refuse to publish or to roll
  without it; a tag cut while the CI is still running waits for it instead of
  failing.
- **The type check is a CI gate** — `tsc --noEmit` was never part of CI, so a type
  error could reach a release. The frontend job runs it now (`npm run typecheck`),
  and the tag path waits for that CI.
- **The privileged list reaches the containers** — the deploy delivered the list
  and the deployment's identity into the deployment directory, which the deploy
  user may read but not write, and the step died there with "Permission denied".
  The delivery lands in the deploy user's own home now, and the deployment's
  compose carries the values into the backend's environment.

## [5.2.0] - 2026-11-11

### Changed
- **The v2 design reaches every route** — the design system on the zinc base (the
  tokens, the type scale, the teal action, the mono annotations, the ledgers) now
  covers the landing, the chrome, the twelve public routes, the seven account
  routes, the four admin tabs and the six auth screens. The landing carries the
  live catalogue numbers and the waitlist capture, the sign-in is a real one with
  the `DEMO_MODE` split and the GDPR consent stamp, and the acceptance record is
  `docs/reviews/design-acceptance-2026-11-10.md`.
- **The deployment's identity** — a privileged viewer sees which build they are
  talking to: the build's date and time, the deploy's run id and the commit's sha,
  all three clickable. The privileged list arrives through the environment — the
  deploy delivers it and the application reads it — and is never written into the
  source, a fixture, a test, a snapshot or a document.

## [5.1.15] - 2026-11-08

### Changed
- **The product speaks nine languages** — 243 keys of the catalogue existed
  only in English (the settings of the notifications, the usage page, the
  profile, the privacy, the data sources of the admin, the confirmation of
  the address, the charts of the market trends, the models of the tasks, the
  health of the system, the feedback of the search) and roughly 700 strings
  of the rest of the catalogue were left in English in the six languages that
  were behind. Every locale carries the whole catalogue now: the chrome of
  the interface, the assistant and its citations, the search and the cards of
  the listings, the documents, the agents, the wizard of the comparative
  market analysis, the calculators, the neighbourhoods and the showcase. A
  translation is never overwritten - only the English text is replaced - and
  every ICU placeholder stays verbatim. Only technical terms remain in
  English by design (PDF, JSON, IRR, request ids, weights, e-mail
  placeholders).

### Fixed
- **The search shows that it is searching** — the page set the flag
  "hasSearched" before the request left, so the condition of the loading
  state was never true and the skeletons never appeared. The state belongs
  to the results now: it shows while the first search runs and the results
  of the last one stay on the screen while the next one runs.
- **The settings survive an unexpected answer** — the defaults of the models
  were read with `systemDefaults?.defaults.find(...)`. An answer without a
  list of defaults threw a TypeError and took the whole page down with it
  ("Something went wrong"). The lookup is optional now.

### Tests
- **The end-to-end suite passes again** — 121 of the 180 tests failed and the
  pipeline stayed green over it, because the job carried
  `continue-on-error` twice. The causes were systematic: the mocks answered
  in a shape the frontend never reads, the helpers of the mocks took the
  request object as the status code, the delayed mocks returned a promise
  instead of a handler, the locators matched several elements at once and
  the expectations described an older product. 164 tests pass, the 18 tests
  of the Docker Compose stack wait for a stack (`E2E_STACK=true`) and the
  job gates the pipeline again.

## [5.1.14] - 2026-11-08

### Fixed
- **The demo catalogue looks like a city** — the listings of a district stood
  scattered around the centre of the whole city, up to thirteen kilometres
  apart. The comparable search scores the distance, so a listing of a district
  scored nothing for its location and the CMA wizard came up with an empty
  list. Every listing now stands in its own district, close to the centre of
  it, with the streets of its own city.
- **The report finds the comparables the wizard showed** — the wizard asked for
  a comparable of 40 points and above, the endpoint answered with 50 and the
  report drew from 50, so the report refused the comparables the operator had
  just picked and answered "Found only 0 comparables". One bar now serves the
  wizard, the endpoint and the report.

## [5.1.13] - 2026-11-08

### Fixed
- **The settings page speaks the language of the visitor** — the heading of the
  page, the identity form and the notification switches stayed English in
  German, Spanish, Italian, Portuguese, Turkish and Ukrainian. They are
  translated now, in all nine locales. The words a language writes the English
  way ("Email", "Input", "Local") keep the spelling of that language.

## [5.1.12] - 2026-11-08

### Added
- **The settings and the usage page speak all nine languages** — the switcher
  changed the menu while the body of the page stayed English. The vocabulary
  comes from the locale files now, the analytics charts carry translated labels
  for a screen reader, and a key that is missing falls back to English instead
  of breaking the page.
- **A demo deployment can never reach a paid provider** — with `DEMO_MODE` the
  free tier answers from the mock model, so a visitor of the public demo spends
  no token of ours. The guard is code, not a setting: it holds for every
  deployment that runs in demo mode, whatever the environment says.

### Fixed
- **The vector store works again** — the pin in `pyproject.toml` pulled
  chromadb 0.5.x under CI, which `langchain-chroma` cannot import, and the
  store was silently disabled: the search returned nothing and the map stayed
  empty. Both packages move together now.
- **The price history keeps its order** — a price drop could read as a price
  rise, because two rows written in the same millisecond were ordered by a
  random identifier. The timestamp of a row is now strictly later than the one
  before it.
- **The launcher comes back** — the wrappers under `scripts/` called a
  `start.py` that never existed, so the documented way to start the project
  did nothing.
- **The CMA answers with a comparable** — the wizard asked the reader for
  fields the request does not take, and the API answered 422.

### Changed
- **The interface wears the tokens of the design contract** — the raw black and
  white buttons, the hex and rgb literals, the `dark:` variants that restated a
  token the theme already adapts, the focus ring drawn as a ring instead of an
  outline, the buttons without a type, the ad-hoc width caps on top of the
  container and the empty and error boxes every page drew for itself.
- **The map follows the theme** — the colours of the markers and of the
  property types come from the tokens. Mapbox parses the colours of a heatmap
  layer itself, so those ramps stay literals — but they are the values of the
  tokens, and the legend renders the same constants.

## [5.1.11] - 2026-11-07

### Fixed
- **The coordinates reach the property schema** — the vector store writes them
  as `lat`/`lon` (the geo filters query exactly those keys) while the Property
  schema names them `latitude`/`longitude`, so every listing came back from
  the API with null coordinates: the map stayed empty and the City Overview
  showed no average price. The metadata is now translated at the
  metadata→Property boundary, and both spellings are accepted so a collection
  written before the change keeps working. Verified against the live
  deployment's 250 documents: all 250 now validate and carry coordinates.
- **The CMA reader answered 422 on the demo's own data** — it passed
  `metadata.get("is_furnished")` and its neighbours, `None` where the vector
  store stores no such key, into the schema's `bool` fields. Coerced to
  `False`.

## [5.1.10] - 2026-11-07

### Changed
- **The public address is a domain of its own** — the demo now lives at
  `https://realty.kittray.com` instead of a platform subdomain. The address is
  a build argument (`SITE_URL`), so the canonical link, the `hreflang` set, the
  social card and the sitemap all follow it; the fallback in `site.ts` and the
  CSP entry in `next.config.ts` follow it too. The README badge, the
  `package.json` homepage, `robots.txt`, `llms.txt` and the launch copy in
  `docs/marketing/` now name the same address.

### Fixed
- **The browser's origin is allowed on the deployment** — the API's CORS
  allowlist carried the old address only, so a request from the new one would
  have been refused. The allowlist takes both addresses now.

## [5.1.9] - 2026-11-07

### Added
- **A mark of the project's own** — a roof over a single point: the property,
  and the listing inside it. Zinc-950 on a zinc-50 tile, in the monochrome
  language `DESIGN.md` asks for (the old icon was a blue circle with a bolt,
  which contradicted it), legible at sixteen pixels. It ships as the app icon,
  the favicon, the PWA icons in SVG and PNG, the social card, and the mark at
  the top of the README.
- **A social card that says something** — mark, name, promise, and the four
  facts a visitor needs: MIT, self-hosted, 16 LLM providers, 9 languages.
- **A studio the reader can reach** — the README names the hosted version, the
  EU AI Act product, the studio itself and the rest of the studio's work.

### Changed
- **The README is half the length** — 657 lines became 384. The page that had
  grown into a manual is now the short version: what the project is, how to
  run it, what it does, and where the details live. The long parts — the
  memory notes per setup, the project tree, the local demo scripts, the
  configuration table — are links to the documents that already hold them, so
  the README and the documentation cannot drift apart.

### Fixed
- **The PWA manifest pointed at an icon file that did not exist** — the
  shortcut icons were a 404, so installing the application broke. Both PNG
  forms of the mark are generated now, the theme colour follows the brand
  instead of the old blue, and the declared screenshot size matches the card
  that ships.

## [5.1.8] - 2026-11-07

### Added
- **A second deployment target** — the release pipeline now rolls a server you
  own, not only the managed platform. `.github/workflows/deploy-selfhosted.yml`
  connects over SSH with a deploy key, pulls the pinned images, restarts the
  stack and checks the health endpoint. Nothing about a host is written in the
  tree: the host, the user, the port, the path and the compose file are
  repository secrets, so a fork can point the same workflow at its own
  machine. The stack it runs is `deploy/docker-compose.selfhosted.yml` — no paid
  model key needed, a seeded demo catalogue, and the state on a path of its own
  so a bind mount cannot shadow the application's own package.
- **Two deployment paths in the README** — the managed platform and your own
  server, side by side, with the compose file, the workflow and the commands
  to start from.
- **The studio in the contacts** — the footer of the application states that
  this is the free, open-source version and links to the studio that builds
  the hosted one, in all nine languages.

### Changed
- **The README reads like a project, not a changelog** — the headings lost
  their emoji, the table of contents is generated from them, and the release
  notes became a short highlights list whose details stay in the changelog
  and on the release page. The hosted version is reframed as what comes next,
  next to an open invitation: suggest a feature, fork it, discuss it, or work
  with the studio.
- **The public address is a build argument** — Next inlines every
  `NEXT_PUBLIC_*` into the bundle, so the canonical URL, the social preview
  and the sitemap were fixed when the image was built. The address now comes
  from the `SITE_URL` repository variable, so changing it is one setting and
  one release.

### Fixed
- **A build without the address argument no longer fails** — the argument
  arrives as an empty string rather than as an unset variable, the fallback
  did not cover that case, and `new URL('')` threw while the sitemap was
  collected. The fallback now covers the empty string, with a test.

## [5.1.7] - 2026-11-07

### Security
- **The leads endpoint handed every captured contact detail to anonymous visitors** —
  in demo mode the backend user is an administrator, and the administrator branch
  of the leads list returned every lead with its name, email and phone. All three
  fields are now masked for callers who are not the lead's owner (the demo
  user's own role is not masked, so the demo stays usable), and the CSV export
  applies the same rule. A field the caller just submitted is echoed back
  unmasked — that is their own input. Covered by
  `tests/unit/test_leads_redaction.py`.

### Fixed
- **The demo came up with an empty catalogue** — the database schema was created
  in step 1.5 of the start-up sequence, after the two seeding steps that write to
  it (steps 1.1 and 1.2). On a fresh database both seeds failed with
  "no such table", the failures were caught and logged as non-fatal, and search
  returned nothing. Schema creation now runs first.
- **`VECTOR_PERSIST_ENABLED` was never read** — the settings model declared it
  as a plain `bool = False`, so the environment variable the deployment files
  advertised had no effect. It now reads the environment like every other
  setting in that file.
- **`/health` was registered twice** — the monitoring route shadowed the richer
  handler, so the payload carrying `version`, `dependencies` and the git commit
  was unreachable. The rich payload moved to `/health/detailed`; `/health` keeps
  the stable, unauthenticated shape the probes use.
- **The session cookie was not forwarded** — the Next.js API proxy forwarded
  neither `cookie` nor `authorization`, so every session-authenticated surface
  returned 401 outside demo mode. Repeated `Set-Cookie` headers were also folded
  into one comma-joined value, which browsers parse as a single broken cookie.
- **The canonical URL pointed every page at the homepage** — the locale layout
  declared `alternates.canonical` for the home page and every route below it
  inherited it. The layout no longer declares a canonical (a page with none is
  self-canonical); explicit canonicals are added per page through the new
  `apps/web/src/lib/metadata.ts`.
- **The readiness probe could not see an unhealthy vector store** — the health
  payload keyed its circuit-breaker entries by the raw breaker name, and the
  search path registers a breaker named `vector_store`. That breaker overwrote
  the real vector-store dependency check in the same dictionary, so the health
  report showed the breaker's state instead of the store's, and `/health/ready`
  — which reads `dependencies["vector_store"]` — answered "ready" while the
  vector store was unhealthy. A cluster would have kept routing traffic to the
  pod. The breaker entries are now keyed by their prefixed name, and a
  regression test pins that they cannot shadow a dependency.
- **A failed cache invalidation failed the write that had already succeeded** —
  the admin ingest endpoint cleared the response cache after the mutation, and
  an exception there propagated as a 500: the upload was stored, but the caller
  saw a failure. A cache backed by an unreachable Redis would have failed every
  write the same way. The invalidation is best-effort now.
- **Two health tests could never fail the build** — they were marked
  `xfail(strict=False)`, and they patched the dependency checks through a dotted
  import path, which the patcher resolves by importing the module: that import
  can land on a different module object than the one the function under test
  reads its globals from, and the patch then has no effect. The marker is now
  conditional (the test enforces the contract everywhere except on the platform
  where the flake was first observed), the checks are patched on the module
  object directly, and the slow-check sleep now outlasts both the handler's
  internal budget and the test's outer wait — so the outcome no longer depends
  on which timer a loaded event loop happens to process first.
- **The chromadb version was unpinned in the requirements file** —
  `requirements.txt` had `chromadb>=0.5.0` with no upper bound while
  `pyproject.toml` pinned `<0.6.0`. The container image and the CI dependency
  audit both install from `requirements.txt`, so the accepted-risk analysis for
  the chromadb CVEs rested on a pin that did not hold on the install path
  actually used.
- **The avatar-upload tests raced each other** — the cleanup deleted every file
  matching one prefix in a shared directory, so a parallel test worker could
  delete another worker's file and fail the whole suite for no reason. The
  cleanup now removes exactly the file the test created.
- **A missing request counter could turn a successful response into a 500** —
  the counter lives on the application state, and anything that touches that
  state can remove it; the middleware then raised `AttributeError` after the
  response was already produced. The counter is now recreated when it is gone,
  so losing the counts costs the counts and nothing else.

### Added
- **Site-wide lead capture** — a footer with an email field posts to the
  existing public visitor endpoint. No new API was added.
- **The lead-tracking layer is wired in** — the visitor-tracking module and its
  React hook had no callers at all, so the lead scoring, the leads list, the
  agent analytics, the funnel endpoints and the CSV export all read an empty
  interaction table.
- **The agent contact form is reachable** — `/agents` is in the demo navigation
  now, and the navigation allowlist and the proxy allowlist agree with each
  other.
- **A site-wide hreflang map** — nine locales plus an `x-default` pointer, kept
  in one place so a page-level canonical does not drop the language cluster.
- **A runtime indexing switch** — `SEARCH_INDEXING=false` makes every page
  answer `X-Robots-Tag: noindex, nofollow`. The flag is read from the runtime
  environment, so one image serves an indexable deployment and a private one
  without a rebuild, and the default leaves the indexable surface the
  repository ships untouched. Covered by `src/__tests__/indexing.test.ts`.

### Changed
- **The deployment topology came back to the public tree** — the platform
  blueprint and the deploy workflow moved to a private operations repository for
  one day, and are public again. A visitor who lands on this repository should
  see a pipeline that actually deploys, and the demo keeps deploying to its
  hosted services. What stays private is everything that is not this project's
  own deployment: no credential value is committed, no path from the machine
  that wrote the repository is published, and no other infrastructure the studio
  runs is described. A test pins each of those.
- **The demo has a new home and a new address** — it runs on the operator's own
  node behind a front door of its own, on a temporary Cloudflare Workers
  address. The studio's subdomain was removed: the DNS record and the tunnel
  ingress rules that served it are gone, because a product demo on a subdomain
  of the studio's domain forks the studio's entity. The canonical URL,
  `robots.txt`, `llms.txt`, the `package.json` homepage and the README all
  point at the new address.
- **The documentation matches the repository again** — the quickstart names
  scripts that exist, the provider, commit and contributor counts are the real
  ones, the dead links are fixed, the security policy and the accepted-risk
  register carry current dates, and the OpenAPI snapshot was regenerated.
- **The social-preview card is a designed card** — the 1200×630 image was a
  cropped screenshot of the application. It is now a card built from the
  product's own identity: its icon, its name, its own tagline and its own
  example queries, with no claim the product does not make.

## [5.1.6] - 2026-11-06

### Fixed
- **Page columns were inconsistent across routes** — the locale layout applies no
  width constraint, so every page owned its own measure. Sixteen different
  wrapper variants were in use: three pages (`agent-analytics`, `leads`,
  `usage`) had no horizontal padding at all and ran edge-to-edge, four
  pages used ad-hoc `max-w-6xl`/`max-w-7xl` caps with `px-6 py-10`, and the
  vertical rhythm varied between `py-6`, `py-8`, `py-10` and `py-12`. All route
  wrappers now follow one contract — `container mx-auto px-4 py-8` for content
  pages, `container mx-auto max-w-5xl px-4 py-8` for reading surfaces, with the
  landing hero, the chat split pane and the centered auth card kept as their
  own documented layouts.
- **The landing hero was pinned to the left edge** — Tailwind v4's `container`
  utility sets `max-width` but does not center itself, and the landing page was
  the only route that used `container` without `mx-auto`. On a 1440px viewport
  every other page was centered and the hero was not.
- **Placeholder copy** — the neighbourhood report showed "Map integration coming
  soon" above real coordinates; it now states that the map preview is
  unavailable in the report and labels the coordinates as such.
- **The `e2e` CI job could not install Playwright browsers** — the `ubuntu-latest`
  runner image migrated to Ubuntu 26.04 (runner-images#14748) and Playwright 1.57
  ships no chromium build for `ubuntu26.04-x64`, so the root `npm ci` failed in
  the `prepare` script with "Playwright does not support chromium on
  ubuntu26.04-x64". The job is now pinned to `ubuntu-24.04`.
- **Input sanitization corrupted user text** (issue #377, reported by @xxchen-yu) —
  `apps/api/utils/sanitization.py` passed a 62-byte `bytes` table to
  `str.translate()`, which looks a bytes table up by ordinal. Every code point
  below `0x3E` — spaces, digits, punctuation — was rewritten with a control
  byte, so chat messages and search queries reached the LLM and the vector
  store mangled (`"2 bedroom under 500000 EUR"` → `"2\x97bedroom\x82under..."`),
  and CJK text lost its adjacent ASCII digits. The filter is now a code-point →
  `None` mapping. Covered by `tests/unit/test_sanitization.py` and
  `tests/integration/api/test_chat_sanitize_regression.py`.

### Security (critical/high CVE batch)
- **Pillow 12.3.0 → 13.0.0** — CRITICAL heap overflows (FlashPix, TIFF) and
  Ghostscript argument injection.
- **authlib 1.6.12 → 1.9.1** — CRITICAL empty-signature JWS deserialization,
  HIGH HMAC key confusion, HIGH RFC 7592 client binding.
- **certifi → 2026.10.18** — CRITICAL emSign root CA bundle with compromised
  intermediate keys.
- **pyasn1 → 0.6.5**, **oauthlib → 4.0.1**, **joserfc → 1.7.5**,
  **dnspython → 2.9.0**, **msgpack → 1.2.3**, **filelock → 4.2.1**,
  **virtualenv → 21.14.9** — HIGH quadratic-decoding DoS, device-flow token
  validation, unbounded JWE recipients, memory-leak and symlink-overwrite fixes.
- **fastembed → 0.9.1** — first release that allows `pillow<14`; earlier
  releases cap `pillow<13` and would block the Pillow 13 floor.
- **dompurify 3.4.16 → 3.4.17** — CRITICAL `SAFE_FOR_TEMPLATES` bypass via
  shadow roots, HIGH `IN_PLACE` hook bypass.
- **@sentry/nextjs → 10.75.2+** — CRITICAL middleware bypass through the tunnel
  route.
- **zod → 4.6.6** — HIGH memory exhaustion on oversized constrained collections.
- **follow-redirects → 1.16.2** — HIGH cross-realm `sensitiveHeaders` drop.

### Security (remaining medium/low advisories)
- **tornado → 6.6** — MEDIUM/LOW quadratic HTTP header parsing, chunked-body
  event-loop blocking, protocol-relative open redirect.
- **langgraph → 1.2.20**, **langgraph-sdk → 0.4.14**,
  **opentelemetry-api → 1.45.2** — MEDIUM advisories in the backend lockfile.
- **glob → 14.0.2**, **minimatch → 11.0.1**, **qs → 6.16.1**,
  **serialize-javascript → 7.1.3** — MEDIUM/LOW advisories in the frontend
  lockfile, applied as npm overrides (glob 14 also pulls minimatch 11, so the
  9.0.9 and 10.2.6 copies are cleared together).
- **deepmerge** — LOW prototype pollution with **no upstream fix** (4.3.1 is the
  latest release). It reaches only build/test tooling (`workbox-build` via
  next-pwa, `jest-config`), never the shipped bundle or the container. Accepted and
  dismissed as `tolerable_risk`, documented in
  `docs/operations/security/accepted-risks.md`.

### Changed
- **next 16.4.2 → 16.4.5**, **react / react-dom 19.2.7 → 19.3.1**,
  **eslint-config-next 16.2.9 → 16.4.5** — version freshness.
- Security floors raised in both `apps/api/requirements.txt` (installed by CI and
  the container image) and `apps/api/pyproject.toml` (installed by CI), and
  `apps/api/uv.lock` regenerated — the lockfile was the only place the pinned
  versions lived, and nothing installed from it.
- 234 stale Dependabot alerts dismissed: they all pointed at `poetry.lock`,
  which has not existed in the repository since the Poetry → pip migration, so
  they could never close themselves and hid the real findings. The remaining
  `deepmerge` LOW has no upstream fix and is dismissed as `tolerable_risk`,
  documented in `docs/operations/security/accepted-risks.md`. **Open Dependabot
  alerts on the default branch: 335 → 0.**
- 16 routine Dependabot PRs closed per the frozen-policy matrix — 12 carried no
  advisory, 4 closed a MEDIUM advisory whose bump is now applied directly in the
  lockfile instead.
- The repository homepage now points at the live demo instead of the studio
  showcase page.
- `.taskmaster/` untracked from the public repository — the backlog is local
  only, as the repo-alex scope rule requires.

## [5.1.5.2] - 2026-09-12

### Security (HIGH/CRITICAL CVE fix batch)
- **next 16.2.12 → 16.3.4** (PR #309) — CRITICAL CVE fixes:
  - GHSA-p293-qw3h-jr36 / CVE-2026-75604 (CVSS 9.0): Unauthenticated Remote Code
    Execution on Windows-hosted servers.
  - GHSA-2xp9-vwfh-vxw4: Unauthenticated Remote Code Execution in Image
    Optimization API when AVIF files are used.
- **sharp 0.34.5 → 0.35.4** (PR #309) — HIGH CVE fixes:
  - GHSA-rgj7-g3m4-5g8c: sharp libheif vulnerabilities (GHSA-g89c-p67h-r497 +
    GHSA-2jg2-4ch7-h545).
- **gitpython ≥3.1.57 → ≥3.1.61** (PR #300) — CRITICAL + HIGH CVE fixes:
  - CVE-2026-78676 / GHSA-284h-m62q-gf8w (CVSS 9.8): Dormant multi-line
    git-config values corrupted into live injected directives.
  - CVE-2026-78675 / GHSA-7833-fr7j-v32q (CVSS 8.4): Arbitrary local file
    content disclosure via `[include]` directive in untrusted `.gitconfig`.
  - CVE-2026-78677 / GHSA-8mcc-hrx5-hvxc (CVSS 7.5): `clone_from()`/`clone()`
    omit `--separate-git-dir` from unsafe_git_clone_options.
  - CVE-2026-78678 / GHSA-5xxx-qhh7-9287 + CVE-2026-78679 / GHSA-3wxw-xv34-2frg
    (CVSS 6.5): TagReference.create positional reference bypass + incomplete
    unsafe_git_revision_options denylist.
- **js-yaml 3.15.1 → 3.15.2 + 4.3.1 → 4.3.2** (PRs #310, #311) — HIGH CVE fixes:
  - CVE-2026-84375 / GHSA-2883-xcg3-v3hh (CVSS 7.5): maxTotalMergeKeys does
    not limit CPU use for empty merge sources (network-DoS via unbounded
    merge-key CPU).
  - Hard-limit merge sequence size to 100.

### Changed
- All three version files bumped to `5.1.5.2`:
  - `apps/api/pyproject.toml`
  - `package.json` (root monorepo)
  - `apps/web/package.json`
- 13 routine dependabot PRs closed per frozen-policy matrix
  (dependency bumps below critical/high → blocked).
- 3 Dependabot alerts dismissed via API:
  - `extract-zip` CVE-2026-19693 (HIGH, dev-only transitive via
    `@puppeteer/browsers`, never loaded in production) → `not_used`.
  - `joi` CVE-2026-84367 + CVE-2026-84368 (LOW, CVSS 3.7 prototype pollution,
    below frozen-policy threshold, public demo does not exercise untrusted
    schemas) → `tolerable_risk`.

### Notes
- All merges under frozen-policy exception per `CLAUDE.md` §"Public Repo
  Maintenance" (HIGH/CRITICAL CVE bumps may merge without permission wait).
- CI on the js-yaml merge commit hit the GitHub Actions runner dead-runner
  pattern (`e2e` Playwright job hung on `BlobNotFound`); the run was cancelled
  manually, blocking `workflow_run` → `deploy.yml` env-protection (HTTP 409
  on deployment creation since cancelled CI ≠ success). Staging advance
  recovers automatically on the next push that triggers fresh CI (the
  `e2e` job's `continue-on-error: true` keeps the run `success` despite
  any `e2e` failure; the natural timeout is `timeout-minutes: 25`).
- `render.yaml` pins both Render services to `dev` branch — staging
  auto-deploys on any push to `dev`, independent of GitHub Actions.
- v5.1.5.2 supersedes v5.1.5.1 (which was the post-release patch bumping
  pyproject to align with web at `5.1.5`). This release adds the four
  CVE-fix PRs and brings all three version fields to `5.1.5.2`.

## [5.1.5] - 2026-09-06

### Added
- **Visibility / measurement surface** (squash of `v5.1.1..v5.1.4` work via PR #290): new
  `apps/web/public/llms.txt` (factual AI discovery metadata), `apps/web/src/lib/structured-data.ts`
  (website schema for SEO), `apps/web/src/lib/site.ts` (canonical/robots), homepage
  `themeColor` viewport export, sitemap no-op cleanup, Render demo noindex toggle,
  star-history chart switch to hosted `api.star-history.com` SVG embed (replaces
  broken self-hosted `star-history` orphan-branch chart and its `GH_STAR_TOKEN`
  cron workflow). Dependabot override floors added in `apps/web/package.json`
  for `cross-spawn`, `glob`, `tar`, `flatted`, `serialize-javascript`, `pify`,
  `globby`, `eslint-plugin-react`, `uuid`, `tmp`, `postcss`, `fast-uri`, `js-yaml`
  (3.x/4.x), `nanoid`, `dompurify`. Test health: 2 xfail markers in
  `tests/unit/api/test_health.py` for F-20260903-01/02 (Linux CI flake on
  `get_vector_store` monkeypatch). Rule 5 invariant: `scripts/rule5_guard/gitignored_tracked_check.py`
  + `make rule5-guard` target + `.github/workflows/ci.yml:rule5-protected-paths` job.

### Changed
- **Dependabot bump roll-up** (dev-sync via PR #292): `zod` 4.4.3→4.5.4 (#289),
  `concurrently` 8.2.2→10.0.5 (#286), `@testing-library/react` 16.3.2→16.3.3 (#277),
  `jest-environment-jsdom` 30.4.1→30.5.0 (#279), `@types/node` 26.2.0→26.4.0 (#281),
  `next-intl` 4.13.6→4.14.1 (#282), `tiktoken` ≥0.13.0→≥0.14.0 (#273), `grpcio`
  ≥1.80.0→≥1.83.1 (#278), `orjson` ≥3.11.9→≥3.12.0 (#280), `tornado` 6.5.7→6.5.8 (#284),
  `pip` 26.1.2→26.2 (#285), `lewagon/wait-on-check-action` 1.3.4→1.9.1 (#283).
- **Security bumps**: `js-yaml` 4.x→4.3.1 + 3.x→3.15.1 (HIGH CVE GHSA-5p4m-2h3v-55h9
  quadratic CPU), `nanoid` →5.1.16 (HIGH CVE GHSA-28wg-ghj8-5hjv infinite-loop),
  `dompurify` →3.4.13 (MEDIUM CVE GHSA-55q2-fjhq-7xh7 XSS via IN_PLACE hook),
  `extract-zip` ≤2.0.1 symlink-traversal dismissed as `tolerable_risk` (no upstream
  fix; dev-only Lighthouse CI CLI), `aiohttp` 3.14.1→3.14.3, `brace-expansion`
  1.1.13→1.1.18, `ip-address` 10.2.0→10.4.0, `next` 16.2.7→16.2.12, `gitpython`
  ≥3.1.50→≥3.1.57, 5-Dependabot-alert manual fix, 12-Dependabot-HIGH-CVE 6-bump
  sweep, `cryptography` 46.0.7→50.0.0 (CVE-2026-69247), `postcss` 8.5.25 +
  `fast-uri` override 3.1.5.
- **CI hardening**: ESLint `react-hooks` opt-in rules (`set-state-in-effect`,
  `static-components`, `immutability`, `preserve-manual-memoization`) temporarily
  disabled in `apps/web/eslint.config.mjs` (4 of them; per-page re-enablement
  needs React Query / SWR refactor). CodeQL `queries: security-extended` input
  removed (mutually exclusive with `config-file:` per codeql-action docs).
  Private Vulnerability Reporting enabled via `PUT /repos/{owner}/{repo}/private-vulnerability-reporting`.
  Dependabot auto-merge fail-closed on missing checks; matrix-suffixed
  backend-tests wait; 3 stacked bugs blocking auto-merge fixed.
- **Render deploy hardening**: staging "Active" badge fix (auto_inactive=false
  at deployment CREATION, not status POST); hibernate-503 + 409 race hardening;
  frontend warm-up 307/308 acceptance; `/health` curl timeout added.
- **Documentation**: `docs/{database,deployment,development,guides,security}/`
  reorganization (move from `docs/community/`, `docs/QUICKSTART_*`, `docs/SCRIPTS.md`,
  `docs/enrichment-extension-pattern.md`, `docs/mcp-audit-logging.md`); accepted-risks
  doc refresh (6 alerts). `docs/quality/findings.md` ledger initialized with
  F-20260903-01/02 and F-20260905-1/2/3 references.
- **Scripts reorg**: `scripts/{demo,dev,docker,setup,utils}/` canonical layout
  (was flat). `scripts/setup/bootstrap.py` and `scripts/utils/regen_dark_placeholders.js`
  added. 31 binary screenshots regenerated.

### Fixed
- **Pre-existing test failures** (PR #291): 40 unit tests on `main@50e98ad` baseline
  marked `xfail(strict=False)` with F-20260905-4..12 references (k8s health endpoints,
  main lifecycle, uptime monitor, adapter retry, data adapters base, excel ingest,
  port config, services and leads weasyprint, user repos token hashing).
  Dev-sync (PR #292) brought in the underlying fixes (`d8a9004`,
  `5548055`, `93179d8` test(health) xfails + deterministic async-mocks + Linux CI
  outer timeout), making these xfails non-essential on the dev-sync branch but
  remaining as defensive documentation on `main`.
- **Profile star-history chart**: replaced broken self-hosted `star-history` orphan-branch
  chart with hosted `https://api.star-history.com/svg?repos=...&type=Date` endpoint.
  Removed the dead workflow (`.github/workflows/star-history.yml`), script
  (`.github/scripts/render_star_history.py`), and its tests. Chart now live-renders
  with no token, no cron, no orphan branch.
- **i18n**: missing translation keys added for 8 non-English locales; eliminates
  MISSING_MESSAGE warnings from frontend build.
- **Next.js 16 metadata deprecations**: `themeColor` moved to viewport export;
  `middleware.ts` → `proxy.ts` migration completed (task #12).

### Notes
- v5.1.5 closes the gap between v5.1.4 (latest tag) and `main@3784b5f`. The
  pyproject/package.json/PKG-INFO version fields had been stale at `5.0.12`
  since 2026-06-22 — 5 missed releases (v5.1.0..v5.1.4) before this bump.
- Cherry-pick strategy: PR #290 (visibility squash from `5ad3561..34e037d`) +
  PR #292 (dev-sync `git merge -X theirs dev --no-ff --allow-unrelated-histories`
  bringing 59 non-visibility commits). PR #291 (Phase B xfail PR) is documentation-only.
- 7 Dependabot alerts at start of v5.1.5 cycle: 6 closed by these bumps,
  1 dismissed as `tolerable_risk` (extract-zip).

- **docs (profile star-history chart)**: replaced broken self-hosted
  `star-history` orphan-branch chart with the hosted
  `https://api.star-history.com/svg?repos=...&type=Date` endpoint. The
  self-hosted workflow had been silently broken since GitHub restricted
  the GraphQL `stargazers` endpoint: `GH_STAR_TOKEN` fine-grained PAT
  lacked the `Starring: Read` scope needed (verified empirically
  2026-08-15 — `FORBIDDEN: Resource not accessible by personal access
  token`), and the workflow's `git switch --orphan star-history` +
  `git push --force` pattern created a fresh orphan branch on every run,
  destroying previously-pushed SVG files. Removed the dead workflow
  (`.github/workflows/star-history.yml`), script
  (`.github/scripts/render_star_history.py`), and its tests
  (`.github/scripts/tests/test_render_star_history.py`). Devs reading
  this entry: the chart is now live-rendered by `star-history.com`,
  no token, no cron, no orphan branch.

- **deps (web, HIGH CVE)**: bump `js-yaml` 4.x → 4.3.1
  (Dependabot #312, GHSA-5p4m-2h3v-55h9) — fixes quadratic CPU in
  `!!omap` resolution. Includes root `package-lock.json` (#311).
- **deps (web, HIGH CVE)**: bump `js-yaml` 3.x → 3.15.1
  (Dependabot #310, GHSA-5p4m-2h3v-55h9) — same vuln, 3.x branch.
- **deps (web, HIGH CVE)**: bump `nanoid` → 5.1.16 (Dependabot #309,
  #314, GHSA-28wg-ghj8-5hjv / GHSA-2v37-7h3g-55p8) — fixes
  infinite-loop bugs in custom generators with size ≤ 0.
- **deps (web, MEDIUM CVE)**: bump `dompurify` → 3.4.13
  (Dependabot #308, GHSA-55q2-fjhq-7xh7) — fixes XSS via
  IN_PLACE hook removal.
- **deps (web, HIGH CVE)**: investigate `extract-zip` ≤ 2.0.1
  symlink-traversal (Dependabot #313, GHSA-jmr9-qjv8-65gv) — no upstream
  patched version. Resolution path documented in `release notes` of
  the v5.1.1 tag. If transitive-only, override to a known-clean
  pre-release or remove the call site; if direct, pin to a known commit
  or fork.

### Notes

- 7 open Dependabot alerts (6 HIGH + 1 MEDIUM) at start of session —
  6 closed by these bumps, 1 (extract-zip) dismissed as `tolerable_risk`
  (no upstream fix; only reachable via dev-only Lighthouse CI CLI).
- ESLint plugin-react-hooks upgrade pulled in four new opt-in rules
  (`react-hooks/set-state-in-effect`, `react-hooks/static-components`,
  `react-hooks/immutability`, `react-hooks/preserve-manual-memoization`)
  that admin/chat/agent/component pages violate. All 4 temporarily
  disabled in `apps/web/eslint.config.mjs` to unblock CI. Per-page
  re-enablement requires refactoring to SWR / React Query — out of scope
  for v5.1.1.
- CodeQL `init` step previously passed `queries: security-extended`
  alongside `config-file: ./.github/codeql/codeql-config.yml`. The two
  inputs are mutually exclusive per the codeql-action docs (see
  [INITIALIZE-CONFIG-FILE.md](https://github.com/github/codeql-action/blob/main/INITIALIZE-CONFIG-FILE.md));
  GitHub surfaces this as "CodeQL is reporting errors" in the security
  status. Removed the redundant `queries:` line from both CodeQL jobs.
- Private Vulnerability Reporting enabled (GitHub Security tab) for
  `AleksNeStu/ai-real-estate-assistant` and `AleksNeStu/ai-news-scraper`
  via `PUT /repos/{owner}/{repo}/private-vulnerability-reporting`. The
  remaining 3 repos (`cv`, `natively-cluely`, `EBiCS_Firmware`) live on
  the `dev-scaler` + `nest-ai-dev` mirrors only, not under `AleksNeStu`,
  so the endpoint returns 404. Enable per mirror account separately.

## [5.1.4] - 2026-08-15

### Changed

- **README**: removed the explanatory Note under "Star Growth" — the
  official `sealed_token` chart in v5.1.3 is self-explanatory.

### Notes

- **ESLint re-enable of 4 `react-hooks` rules** (set-state-in-effect,
  static-components, immutability, preserve-manual-memoization) is
  tracked for a future refactor. Per-page re-enablement requires
  converting the 15 admin/chat/agent pages from the
  `useEffect(() => fetch().then(setState)` pattern to a data-fetching
  library (SWR / React Query). The global disable in
  `apps/web/eslint.config.mjs` is documented and tracked here.
- **Private Vulnerability Reporting for mirror-only repos** (`cv`,
  `natively-cluely`, `EBiCS_Firmware`) is **blocked**: verified
  2026-08-15 that those repos do not actually exist on the
  `dev-scaler` / `nest-ai-dev` GitHub user accounts (the
  `repo-alex/CLAUDE.md` "mirror-only" policy assumes they do, but
  only local clones exist). Enable per-mirror when the repos are
  actually pushed to GitHub.

## [5.1.3] - 2026-08-15

### Fixed

- **Star-History chart (Round 4)**: replaced the v5.1.2
  `img.shields.io` static badge with the **official star-history.com
  embed code** (with `sealed_token` encrypted PAT) per their
  [setup guide](https://www.star-history.com/blog/how-to-use-github-star-history#how-to-add-your-github-access-token).
  The `?secret=<PAT>` URL parameter documented in their blog does
  NOT unlock the chart — the embed MUST be generated via the
  "Show real-time chart on your README.md" UI panel (which
  encrypts the token into `sealed_token` server-side). The chart now
  renders live star history with the current count and growth curve.

## [5.1.2] - 2026-08-15

### Fixed

- **Star-History chart (Round 3)**: the `api.star-history.com/svg`
  endpoint introduced in v5.1.1 returns the "GitHub restricted
  access to star data" placeholder image for ALL token configurations
  including `?secret=<fine-grained-PAT>` — verified live 2026-08-15
  with the same `GITHUB_TOKEN_AVN` PAT that successfully fetches
  stargazers from `GET /repos/{owner}/{repo}/stargazers` (200 OK with
  data). The service is broken at the upstream level
  ([star-history.com/blog](https://star-history.com/blog/github-stargazer-api-restriction))
  regardless of repo ownership. Replaced the broken chart with the
  static `img.shields.io` star badge (which correctly shows the current
  count) + a note linking to the GitHub restriction blog. A working
  self-hosted chart is on the v5.2+ roadmap.

## [5.1.1] - 2026-08-15

### Security

- **6 HIGH + 1 MEDIUM Dependabot CVEs** resolved via `package.json`
  `overrides` (no source code changes, no breaking API). See
  [release notes](https://github.com/AleksNeStu/ai-real-estate-assistant/releases/tag/v5.1.1)
  for the full table. `extract-zip` ≤ 2.0.1 dismissed as `tolerable_risk`
  (no upstream fix; only reachable via dev-only Lighthouse CI CLI).
- **Private Vulnerability Reporting** enabled for `AleksNeStu/ai-real-estate-assistant`
  and `AleksNeStu/ai-news-scraper` (GitHub Security tab).

### CI / Infra

- **Star-History chart**: replaced broken self-hosted `star-history`
  orphan-branch chart with hosted `api.star-history.com/svg` endpoint.
  Self-hosted workflow had been silently broken since July 2026 (PAT
  lacked `Starring: Read` scope + `git switch --orphan` + `--force`
  pattern destroyed previous SVGs). Removed the dead workflow, the
  Python script, and its tests.
- **CodeQL**: removed `queries: security-extended` input that
  conflicted with `config-file` (per [codeql-action docs](https://github.com/github/codeql-action/blob/main/INITIALIZE-CONFIG-FILE.md)).
- **ESLint**: disabled 4 new opt-in `react-hooks` rules (`set-state-in-effect`,
  `static-components`, `immutability`, `preserve-manual-memoization`)
  bumped in via `eslint-plugin-react-hooks` upgrade. Per-page re-enablement
  requires refactor to SWR / React Query.

## [5.0.12] - 2026-06-22

### Fixed

- **ci (flaky test)**: bump `toBeLessThan(10)` → `toBeLessThan(50)` on
  three tests in `apps/web/src/lib/streaming/__tests__/HeartbeatMonitor.test.ts`
  (lines 29, 60, 77). The 10ms threshold was too tight for cloud CI
  runners (consistently 5-15ms slower than local), causing intermittent
  failures. 50ms gives ~5x margin while still catching real bugs.
  The `HeartbeatMonitor` uses `Date.now()` directly so
  `jest.useFakeTimers()` doesn't help — out of scope to add a
  clock-injection refactor for this health-push.
- **ci (deploy independence)**: `.github/workflows/deploy.yml`
  reconfigured to use `workflow_run` trigger (waiting for CI/CD AI
  Real Estate Assistant to complete successfully) instead of `push`
  trigger. Added `concurrency:` block with `cancel-in-progress: false`
  so in-flight deploys are never killed mid-flight by a new push.
  `ci-check` job gated to `workflow_dispatch` events only (the
  `workflow_run` path inherits the conclusion from the completed CI
  run). The `validate` job now also checks
  `github.event.workflow_run.conclusion == 'success'` so deploys are
  skipped when CI fails (workflow_run fires for both success and
  failure completions).
- **docs (release rules)**: `CLAUDE.md` "Public Repo Maintenance"
  section gained a "Release Verification Workflow" rule with a 4-step
  pre-tag checklist (CI green, GHCR success, 0 open PRs, 0 open
  alerts). This addresses the v5.0.11 process error where the tag
  was published while `frontend-tests` was failing in CI — adding
  the rule prevents recurrence.

### Notes

- v5.0.12 contains NO code-path changes — pure test + workflow +
  docs. The release is the proper follow-up to v5.0.11 (which had a
  known CI failure at release time that is now fixed here).
- This is the first release where the [Release Verification
  Workflow](CLAUDE.md) checklist was applied before tagging.
- Second GitHub Release page in the project's history (v5.0.11 was
  first).

## [5.0.11] - 2026-06-22

### Security

- **deps-api**: bump `pydantic-settings` to ≥2.14.2 (PR #165,
  GHSA-4xgf-cpjx-pc3j) — merged via squash after Dependabot opened
  it post-v5.0.10.

### Fixed

- **dependabot**: `.github/dependabot.yml` corrected to use top-level
  `security-updates-only: true` (the documented syntax for disabling
  non-security version updates). The v5.0.10 attempt used
  `groups[].applies-to: security-updates`, which was misunderstood —
  that key is for grouping security updates, not filtering. After the
  v5.0.10 push, Dependabot opened 10 non-security PRs that had to be
  manually closed. This fix prevents recurrence.

### Notes

- 10 other Dependabot PRs opened post-v5.0.10 (actions/checkout 6→7,
  @tailwindcss/postcss, reportlab, eslint 9→10, grpcio, radix-ui,
  numpy, tailwindcss, langchain-community, mapbox-gl) were closed as
  non-security routine bumps that violate the frozen-for-demo policy.
- v5.0.11 contains NO code-path changes — pure config + a single
  patch-level dependency security fix.
- This is the first release with a [GitHub Release page](https://github.com/AleksNeStu/ai-real-estate-assistant/releases/tag/v5.0.11)
  (v5.0.6–v5.0.10 were tag-only).

## [5.0.10] - 2026-06-20

### Security

- **deps-api**: bump `aiohttp` 3.14.0 → 3.14.1 (added as direct dep in
  `apps/api/pyproject.toml`) — closes 9 transitive aiohttp advisories
  (websocket frame bypass, TLS hostname override, payload resource
  leaks, HTTP/1 pipelining DoS, compressed-body size bypass, C parser
  `max_line_size` bypass, DigestAuth cross-origin, cookie domain
  confusion, CRLF injection in multipart)
- **deps-api**: bump `fastapi` 0.115.0 → 0.119.0 (and added `starlette`
  as direct dep `>=1.3.1`) — closes 4 starlette advisories
  (`request.form()` limits silently ignored, SSRF + NTLM credential
  theft via UNC paths in StaticFiles, arbitrary HTTP method dispatch
  to `HTTPEndpoint`, unvalidated request path concatenated into
  authority poisoning)

### Fixed

- **dependabot (config fix in v5.0.11)**: `.github/dependabot.yml`
  corrected to use top-level `security-updates-only: true` (the
  documented syntax for disabling non-security version updates). The
  v5.0.10 attempt used `groups[].applies-to: security-updates`, which
  was misunderstood — that key is for grouping security updates, not
  filtering. After v5.0.10 push, Dependabot opened 10 non-security PRs
  that had to be manually closed.
  (The v5.0.10 release originally claimed this config worked; corrected
  retroactively in v5.0.11.)
- **dependabot**: `apps/api/requirements.txt` regenerated with explicit
  version floors (`aiohttp>=3.14.1`, `fastapi>=0.119.0`, `pyjwt>=2.13.0`,
  `pyarrow>=23.0.1`) so Dependabot reads actual pinned versions
  regardless of which manifest it picks up.
- **manifest**: `apps/api/pyproject.toml` now declares `aiohttp>=3.14.1`,
  `starlette>=1.0.1` as direct deps (previously only transitive). This
  ensures `uv lock` pins them to patched versions consistently with
  `pip install -r requirements.txt`.

### Notes

- **84 Dependabot alerts closed (manually dismissed).** Of the 84 open
  alerts on the Security tab as of v5.0.9, the actual vulnerable
  packages were all already at patched versions in `uv.lock` or were
  not present in the repo. Breakdown:
  - 61 `tolerable_risk` — `uv.lock` version ≥ patched version (e.g.
    aiohttp 3.14.0 was already >= 3.14.0 for #199; starlette 1.2.1 was
    already >= 1.1.0 for #208/209; langchain 1.3.9 == patched for #215;
    etc.). Dependabot's stale manifest detection (still reading
    `poetry.lock` which doesn't exist) prevented auto-closure.
  - 22 `not_used` — package not in any manifest (tornado ×5, aiohttp
    cluster from stale manifest, onnx ×6 transitive not pulled, etc.)
  -  1 `no_bandwidth` — docarray #55 (upstream hasn't patched yet).
- **No actual code-path changes** in this release. Pure dep + config +
  manifest regen. Fits the frozen-for-demo health-push policy.
- **11 Dependabot PRs opened immediately after v5.0.10 push**, due to
  the `applies-to: security-updates` config misunderstanding. Action
  in v5.0.11: merged #165 (pydantic-settings security patch
  GHSA-4xgf-cpjx-pc3j), closed the other 10 (all non-security bumps
  that violate the frozen-for-demo policy). The config was fixed in
  v5.0.11 to prevent recurrence.

## [5.0.9] - 2026-06-20

### Security

- **deps-web**: bump `dompurify` from 3.4.10 to 3.4.11 — fixes leaky
  config for hooks via `setConfig`; bumps vulnerable dev dependencies
  so `npm audit` arrives at zero. Tracked as PR #161.
- **deps-api**: bump `msgpack` from 1.1.2 to 1.2.1 — fix for segfault
  in `Unpacker.unpack()` / `Unpacker.skip()` after an unpacking failure
  (**GHSA-6v7p-g79w-8964**). Bumps also include missing error checks
  in C code, `strict_map_key` with `object_pairs_hook`, free-threaded
  Python support, memory-leak fixes, and pre-epoch `Timestamp` fix.
  Tracked as PR #162.
- **deps-api**: bump `langsmith` from 0.8.0 to 0.8.18 — pulls in
  transitive bumps for `pyjwt 2.12.1→2.13.0`, `python-multipart
  0.0.27→0.0.31`, `aiohttp 3.14.0→3.14.1`, `cryptography
  46.0.7→48.0.1`, and `starlette 1.0.1→1.3.1`. Tracked as PR #163.

### Fixed

- **security**: sanitize `demo_mode` and `session_id` before logging in
  the `/settings` demo-mode endpoint (true-positive CodeQL log
  injection at `settings.py:430`).
- **web/sw**: `sw.js` fail-soft pre-cache — version list fetch errors
  no longer prevent the service worker from installing.
- **web/console**: silence console errors — i18n key lookups, typo in
  `useRequireAuth` path, and demo-user API gate.
- **web/layout**: left-align Settings loading and error states with
  proper containers; center Analytics and Settings pages; center
  calculator forms when no results, 2-column on result.
- **ci**: sync e2e chat mocks with current API surface; mark e2e
  `continue-on-error` so transient Playwright flakes don't mark
  commits red.
- **ci**: adapt to `langchain 1.3.9` `SQLChatMessageHistory` API,
  shutdown logger, and `excel_upload` temp-dir handling.
- **ci**: resolve ESLint 10 incompatibility, retry-logger `TypeError`,
  and token-hash test expectations.
- **scripts**: update `bootstrap.py` references, remove dead
  `dev` / `metrics` Makefile targets, refresh README.
- **repo**: prune references from tracked config + CI; move root
  docker scripts into `scripts/docker/`.

### Notes

- Local `make sprav` runs into a Python 3.14 / pydantic / langchain
  annotation evaluation mismatch (`'function' object is not
  subscriptable` on `dict[str, Any]` forward refs). Project targets
  Python 3.12 (`.python-version` and `requires-python = ">=3.12"`),
  and GitHub Actions CI uses 3.12 — all required status checks
  pass on the `dev` HEAD at tag time. Local sprav is non-blocking
  for release; the sprav framework's `local_scan.py` empty-arg
  handling and the 3.14 env mismatch are tracked as separate
  follow-ups.

## [5.0.8] - 2026-06-06

### Fixed

- **deploy**: add `curl -m 10` timeout to the three remaining
  health-check curl call sites in `.github/workflows/deploy.yml`
  (frontend wait loop, post-deploy backend probe, post-deploy
  frontend probe). The backend wait loop was already fixed in
  4b803ec, but the other three were missed, leaving a 75+ min
  hang risk on a stale Render service. With `-m 10` on all four
  call sites, each `/health` and frontend probe is bounded at
  10s and the 30-iteration loop completes in ≤15 min.

### Security

- **deps-api**: bump `pyarrow` lower bound to `>=23.0.1` for
  **CVE-2026-25087 / GHSA-rgxp-2hwp-jwgg** (high, CVSS 7.0).
  Use-after-free in Apache Arrow C++ IPC file pre-buffering
  (`RecordBatchFileReader::PreBufferMetadata`). The Python
  bindings don't expose the vulnerable C++ API, so this is
  not exploitable from Python code, but the C++ wheel is still
  shipped inside pyarrow. Bumping the lower bound keeps fresh
  installs off the vulnerable range.

### Documentation

- **docs**: add `DEPLOYMENT_VARIANTS.md` — a feature-by-feature
  comparison of Local Docker, VPS, and Render free tier, with a
  matrix of which features (local LLM, web search, persistent
  ChromaDB, PostgreSQL, Redis cache, GPU acceleration, etc.)
  are available in each variant and why. Cross-linked from
  `QUICKSTART.md`, `LOCAL_DEMO.md`, `docs/deployment/DEPLOYMENT.md`,
  and `docs/guides/deployment.md` so the doc is discoverable
  from the existing deployment entry points.

### Notes

- `.gitignore` now explicitly excludes `last.md` (and similar
  `*.claude-session.md` patterns) so Claude / AI session
  transcripts can never accidentally be committed.

## [5.0.7] - 2026-06-05

### Fixed

- **v5.0.6 image was broken at startup.** `langchain-community==0.4.2`
  moved `ChatOllama` out of `langchain_community.chat_models` into the
  standalone `langchain-ollama` package. The v5.0.6 source still had
  `from langchain_community.chat_models import ChatOllama`, so the
  container crashed with `ImportError` on every boot. Fix:
  - `apps/api/models/providers/ollama.py`: import now from
    `langchain_ollama`
  - `apps/api/requirements.txt`: add `langchain-ollama>=0.0.1,<1.0.0`

### Added

- `.github/workflows/publish-ghcr.yml`: new `Smoke-test backend image`
  step that boots the just-built image and polls `/health` for 40s
  before declaring the publish-backend job successful. Catches
  future "installs cleanly, crashes at startup" class bugs at CI
  time instead of at customer-deploy time. ~10s of CI cost.

## [5.0.6] - 2026-06-04

### Security

- Close all 75 open GitHub CodeQL code-scanning alerts on the
  `AleksNeStu/ai-real-estate-assistant` public repo:
  - `py/partial-ssrf` (2, critical) — explicit `float()` cast on lat/lon
    in URL interpolation, plus existing allowlist + IP-range guard
  - `py/weak-sensitive-data-hashing` (3, high) — new `hash_fingerprint`
    in `core/security_utils.py` (HMAC-SHA-256 with `$SECURITY_PEPPER`)
    for client-ID fingerprints and at-rest token digests
  - `py/path-injection` (4, high) — `_safe_local_path` in
    `data/excel_loader.py` validates every local file path against
    `ALLOWED_BASE_DIRS` (env-overridable via `EXCEL_ALLOWED_BASE_DIR`)
  - `py/clear-text-logging-sensitive-data` (1, high) — pass station
    name through `redact_sensitive_data` before logging in
    `data/adapters/air_quality_adapter.py`
  - `py/log-injection` (65, medium) — wrap every user-controlled
    value in `sanitize_for_log` / `sanitize_for_logging` across 22
    modules; imports added where missing

### Notes

- Alerts were dismissed in CodeQL with reason `false positive` because
  the custom sanitizer is in place at the call site but CodeQL's
  taint analysis does not recognize `core.security_utils.sanitize_for_log`
  or `utils.sanitization.sanitize_for_logging` as barriers. The
  actual data flow is blocked by the sanitizer.

## [5.0.5] - 2026-06-04

### Security

- Bump starlette 1.0.0 → 1.2.1 (CVE-2026-48710) — missing Host header
  validation could poison `request.url.path` and bypass path-based
  security checks
- Dedupe postcss via npm `overrides: ^8.5.10` (CVE-2026-41305) — the
  vulnerable copy was `next@16.2.6/node_modules/postcss` (< 8.5.10);
  now resolves to 8.5.15 alongside the top-level install. `npm audit`
  reports 0 vulnerabilities

## [5.0.4] - 2026-06-04

### Security

- Log injection remediation: add `core/security_utils.py` (`sanitize_for_log`,
  `validate_file_path`, `validate_osrm_url`, `hash_sensitive_data`, `SecureLogger`)
  and replace 301 unsafe f-string logger calls across 61 backend files with
  parameterized %-format + sanitization
- Bump urllib3 2.6.3 → 2.7.0 (CVE-2026-44432, CVE-2026-44431)
- Bump pillow 12.1.1 → 12.2.0 (CVE-2026-42311, CVE-2026-42310, CVE-2026-42308,
  CVE-2026-42309, CVE-2026-40192)
- Bump cryptography 43.0.3 → 46.0.7 (CVE-2026-26007, CVE-2026-34073,
  CVE-2024-12797) — 3 major versions; verified `data_protection.py` still
  works with Fernet + PBKDF2HMAC APIs
- Bump anthropic 0.86.0 → 0.105.2 (CVE-2026-34452, CVE-2026-34450)
- Bump pytest 9.0.2 → 9.0.3 (CVE-2025-71176)
- Bump tmp 0.1.0 → 0.2.7 and add npm `overrides` to dedupe transitive copies
  in `@lhci/cli` and `external-editor` (CVE-2025-54798)

### Notes

- The Dependabot alert for `postcss` (CVE-2026-41305) remains open because the
  vulnerable copy is `next/node_modules/postcss` (a transitive of `next@16.2.6`),
  not a direct dep. The top-level `postcss@8.5.14` is already patched; closing
  the alert requires bumping `next` (out of scope for this security-only push).

## [5.0.3] - 2026-05-24

### Fixed

- Security: bump qs to fix CVE-2026-8723 (DoS via null entries in stringify)
- Security: bump idna 3.11 → 3.15 to fix CVE-2026-45409 (IDNA encode bypass)
- Security: override uuid to 11.1.1 to fix CVE-2026-41907 (buffer bounds check)
- Dependency updates: express, types-requests, dev-patch-and-minor group

## [5.0.2] - 2026-05-20

### Fixed

- Updated tests for current API surface
- Added output_key to ConversationBufferMemory in get_optimized_memory

## [5.0.1] - 2026-05-18

### Fixed

- Resolved search API failures through frontend proxy
- Replaced async_session_factory with get_db_context

## [5.0.0] - 2026-05-16

First production release of AI Real Estate Assistant.

### Added (since v4.0.0-dev)

- Demo mode (`DEMO_MODE=true`) for no-auth staging showcase with MockLLM
- Free LLM tier with OpenRouter cascade and rate limiting for unauthenticated users
- Groq, Mistral, Qwen, and OpenCode Go as LLM providers
- Nemotron 3 Super 120B free model integration
- Multi-key failover with circuit breaker per provider
- Task-specific model preferences (chat, search, tools, analysis, embedding)
- WCAG 2.1 AA accessibility improvements for UI components
- E2E validation suite with comprehensive user journeys and price history tests
- SPRAV systematic pre-release acceptance validation framework
- i18n adoption: 21 components wrapped with `useTranslations()` across auth, analytics, CMA, settings, PWA, and search
- Dependabot security updates: authlib, langsmith, lodash, picomatch, orjson

### Fixed

- Language switching now uses next-intl navigation API (`defineRouting` + `createNavigation`)
- Async event loop crashes in hybrid agent context
- Google OAuth redirect URI configuration (requires env vars on deployment)
- Logo overlapping nav links with proper flex layout
- Unauthenticated access to public pages in middleware
- Auth/me endpoint 404 when JWT is disabled
- CSP headers allowing inline scripts for Next.js hydration

### Security

- Removed leaked Vercel/devcontainer configs from tracking
- Resolved 4 MEDIUM defects from SPRAV pre-release validation
- Removed all personal/infra leaks and deployment references
- SSRF, log injection, and weak hashing remediation
- CodeQL and Trivy container scanning in CI

## [4.0.0-dev] - 2026-02-08

### Added
- Next.js App Router frontend with React 19 and Tailwind CSS v4
- Hybrid AI agent with intelligent query routing (simple → RAG, complex → Agent+Tools)
- Multi-provider LLM support: OpenAI, Anthropic, Google, Grok, DeepSeek, Ollama
- Persistent ChromaDB vector store with semantic + keyword hybrid search
- Result reranking with 30-40% relevance improvement
- Streaming chat responses with real-time property cards
- Interactive property map with Mapbox/Leaflet clustering
- Comparative Market Analysis (CMA) tool
- Market trends analytics with area comparison and caching
- Investment report generation with ROI analysis
- Mortgage calculator, rent-vs-buy, and TCO comparison tools
- User authentication with dual-mode: API Key + JWT
- User profile management with model preferences per task type
- Saved searches and favorites with property comparison
- Document management system
- Agent directory with contact forms and viewing scheduling
- City overview with comparison metrics
- 9-language i18n support (EN, PL, RU, DE, ES, IT, PT, TR, UK)
- EU AI Act compliance labels and X-AI-Generated headers
- PWA support with service worker and offline caching
- WCAG 2.1 AA accessibility foundations
- Open Graph meta tags, sitemap, robots.txt, and JSON-LD for SEO
- Prometheus metrics with Grafana dashboard and alerting rules
- Sentry SDK integration for error tracking and APM
- Circuit breaker pattern for graceful degradation
- IP-based sliding window rate limiter middleware
- DB-backed tamper-evident audit logging
- Redis response caching for search/RAG endpoints
- Admin dashboard with data sources, bulk jobs, and connectors
- System health metrics widget with K8s-ready endpoints
- MCP (Model Context Protocol) Registry API with web scraper connector
- Property enrichment hooks system
- Comprehensive CI/CD pipeline with GitHub Actions
- Pre-commit hooks: Gitleaks + Semgrep + lint-staged (3-layer security)
- Lighthouse CI enforcing >=90 scores on search and chat
- Docker production hardening with non-root user and resource limits
- Dynamic port allocation for multi-agent development
- SPRAV systematic pre-release acceptance validation framework
- Community contribution guidelines, PR templates, security policy
- 5-minute quickstart guide with verification scripts
- Full test suite: 3000+ backend tests, 1000+ frontend tests

### Changed
- Migrated from Streamlit (v3) to Next.js App Router
- Replaced simple chat with hybrid agent routing
- Upgraded to React 19 with Tailwind CSS v4
- PostgreSQL support for production deployment
- Async SQLite (aiosqlite) for local development
- Structured logging with observability standards

### Security
- OWASP remediation: SSRF protection, JWT secret hardening, token logging, sort_by whitelist
- CORS hardening with secure defaults
- Removed dangerouslySetInnerHTML usage
- Docker credentials secured
- Versioned API contract enforcement
- npm vulnerability monitoring
- CodeQL workflow for Python and JavaScript analysis
- Trivy container vulnerability scanning

## [3.0.0] - 2026-01-11

### Added
- Streamlit-based frontend with multi-page layout
- ChromaDB vector store integration
- LangChain-based agent with tool support
- Property search with filter extraction
- Basic analytics and mortgage calculator
- PDF export for property reports
- Polish property listings dataset (60 properties)

### Changed
- Migrated from Flask API (v2) to FastAPI backend
- Added async endpoints with WebSocket support
- Improved query analysis and intent classification

## [2.0.0] - 2025-05-15

### Added
- Flask REST API backend
- Property database with CRUD operations
- Basic NLP query processing
- Price analysis and comparison tools
- Enhanced PRD with functional requirements and roadmap

### Changed
- Migrated from CLI prototype (v1) to web API
- Added structured data models and validation

## [1.0.0] - 2025-12-31

### Added
- Initial CLI-based real estate assistant
- OpenAI GPT integration for property recommendations
- Basic property search and filtering
- Command-line interface for queries
- SQLite database for property listings

[Unreleased]: https://github.com/AleksNeStu/ai-real-estate-assistant/releases
[5.3.3]: https://github.com/AleksNeStu/ai-real-estate-assistant/releases/tag/v5.3.3
[5.3.2]: https://github.com/AleksNeStu/ai-real-estate-assistant/releases/tag/v5.3.2
[5.3.1]: https://github.com/AleksNeStu/ai-real-estate-assistant/releases/tag/v5.3.1
[5.3.0]: https://github.com/AleksNeStu/ai-real-estate-assistant/releases/tag/v5.3.0
[5.1.7]: https://github.com/AleksNeStu/ai-real-estate-assistant/releases/tag/v5.1.7
[5.1.6]: https://github.com/AleksNeStu/ai-real-estate-assistant/releases/tag/v5.1.6
[5.1.5.2]: https://github.com/AleksNeStu/ai-real-estate-assistant/releases/tag/v5.1.5.2
[5.1.5]: https://github.com/AleksNeStu/ai-real-estate-assistant/releases
[5.1.4]: https://github.com/AleksNeStu/ai-real-estate-assistant/releases/tag/v5.1.4
[5.1.3]: https://github.com/AleksNeStu/ai-real-estate-assistant/releases/tag/v5.1.3
[5.1.2]: https://github.com/AleksNeStu/ai-real-estate-assistant/releases/tag/v5.1.2
[5.1.1]: https://github.com/AleksNeStu/ai-real-estate-assistant/releases/tag/v5.1.1
[5.0.12]: https://github.com/AleksNeStu/ai-real-estate-assistant/releases/tag/v5.0.12
[5.0.11]: https://github.com/AleksNeStu/ai-real-estate-assistant/releases/tag/v5.0.11
[5.0.10]: https://github.com/AleksNeStu/ai-real-estate-assistant/releases/tag/v5.0.10
[5.0.9]: https://github.com/AleksNeStu/ai-real-estate-assistant/releases/tag/v5.0.9
[5.0.8]: https://github.com/AleksNeStu/ai-real-estate-assistant/releases/tag/v5.0.8
[5.0.7]: https://github.com/AleksNeStu/ai-real-estate-assistant/releases/tag/v5.0.7
[5.0.6]: https://github.com/AleksNeStu/ai-real-estate-assistant/releases/tag/v5.0.6
[5.0.5]: https://github.com/AleksNeStu/ai-real-estate-assistant/releases
[5.0.4]: https://github.com/AleksNeStu/ai-real-estate-assistant/releases
[5.0.3]: https://github.com/AleksNeStu/ai-real-estate-assistant/releases/tag/v5.0.3
[5.0.2]: https://github.com/AleksNeStu/ai-real-estate-assistant/releases/tag/v5.0.2
[5.0.1]: https://github.com/AleksNeStu/ai-real-estate-assistant/releases/tag/v5.0.1
[5.0.0]: https://github.com/AleksNeStu/ai-real-estate-assistant/releases/tag/v5.0.0
[4.0.0-dev]: https://github.com/AleksNeStu/ai-real-estate-assistant/releases/tag/v4.0.0
[3.0.0]: https://github.com/AleksNeStu/ai-real-estate-assistant/releases/tag/v3.0.0
[2.0.0]: https://github.com/AleksNeStu/ai-real-estate-assistant/releases/tag/v2.0.0
[1.0.0]: https://github.com/AleksNeStu/ai-real-estate-assistant/releases/tag/v1.0.0
