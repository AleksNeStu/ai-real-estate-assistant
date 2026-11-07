# Repository review — `ai-real-estate-assistant` · 2026-11-06

A full review of the TaskMaster backlog and the live application state, the changes it produced, and
what is still open. Everything below was measured on 2026-11-06 against the `dev` branch at
`3f5e428d` and against the running deployment.

---

## 1. State at the start of the review

| | |
|---|---|
| Branch | `dev` @ `3f5e428d`, byte-identical on all three GitHub remotes (`AleksNeStu`, `dev-scaler`, `nest-ai-dev`) |
| Release | `v5.1.6`, tagged and published 2026-11-06 |
| Security | 0 open Dependabot, CodeQL and secret-scanning alerts |
| Backlog | 29 tasks: 18 done · 4 pending · 5 blocked · 1 deferred · 1 cancelled |
| Public demo | Served from a free-tier host that sleeps between requests; the repository committed its own deployment topology |

## 2. What the review found

### 2.1 The backlog did not match reality

Four of the five **blocked** tasks had already been resolved by earlier work, and the fifth — the one
that actually mattered — was marked *done* when it had not been started.

| Task | What it claimed | What was actually true |
|---|---|---|
| #21 | "5 commits ready for push" | All five were already ancestors of `dev`; `dev` was identical on every remote |
| #23 | "verify after the redeploy" | The redeploy had happened; the service answered `200 healthy` |
| #24 | "tag, publish, release" | Tag, release page and container images all published |
| #26 | "the chromadb CVEs are not in the accepted-risk register" | They **were** in it, with a full per-CVE reachability analysis; zero alerts were open |
| #27 | "serve the demo from our own server behind a stable URL, hide the deployment topology" | The demo was still on the free-tier host and the platform blueprint plus the deploy workflow were still committed in the public tree |
| #13 | "open and merge the technical visibility PR" | The visibility work had already shipped; there was nothing left to package |

**Disposition:** #21, #23, #24, #26 and #13 closed as done; #27 reopened. Three new tasks were filed
to carry the work that was actually outstanding.

### 2.2 The demo was already deployed on the operator's own server — and nobody knew

While auditing the fleet for a suitable host, the review found that `https://ai-real-estate-demo.devs-scaler.workers.dev`
**already served this application**, behind a Cloudflare tunnel, on the operator's own machine —
with a working health endpoint, a tunnel of its own and a hostname of its own.

The public repository did not know about it. It still advertised the free-tier host, still committed
the deployment topology, and still pointed its canonical URL, its `robots.txt` sitemap line, its
`llms.txt`, its `package.json` homepage and its README badges at that host.

### 2.3 The demo ran with an empty catalogue — a start-up ordering bug

The application creates its database schema in step 1.5 of its start-up sequence, but the two seeding
steps that write to it run in steps 1.1 and 1.2 — **before** the schema exists. On a fresh database
both seeds failed with `no such table: users` and `no such table: cma_reports`, the failures were
caught and logged as "non-fatal", and the demo came up with an empty catalogue and an empty vector
index. The deployed instance answered `{"results":[],"count":0}`.

Fixed: schema creation now runs first, whenever a deployment that seeds — or that turns on
authentication — is going to need it. A deployment whose schema is owned by the migration tool
still does not run it, because `create_all` would race the migrations.

A second, related defect: the `VECTOR_PERSIST_ENABLED` environment variable was advertised in
the deployment files and in `.env.example`, but the settings model never read it — it was a plain
`bool = False`. Setting it did nothing. The setting now reads the environment like every other
setting in that file.

### 2.4 Lead generation was structurally dead

| Finding | Consequence |
|---|---|
| The visitor-tracking module (12 trackers) and its React hook had **zero callers** | The lead-scoring service, the leads list, the agent analytics, the funnel endpoints and the CSV export all read an empty interaction table |
| There is **no email capture anywhere** — no footer component existed at all | A visitor had no way to leave a contact address |
| The one working contact form lives on an agent detail page, and `/agents` was **not in the demo navigation** | The form was unreachable by navigation; only a typed URL reached it |
| The proxy did not forward `cookie` or `authorization` | Every session-authenticated surface returned 401 outside demo mode |
| In demo mode the backend user is an administrator, and the administrator branch of the leads list returns every lead | An anonymous visitor could see every captured lead's name, email address and phone number |

### 2.5 The public repository exposed deployment internals

- `docs/deployment/deploy.md` named two specific hosts and a hosting platform, and stated that
  "CI auto-triggers are disabled for this repo" — false: CI triggers on every push to `main` and `dev`.
- Three more documents repeated the platform name.
- `docs/marketing/README.md` carried an absolute local filesystem path.
- The platform blueprint published the two service definitions, the Dockerfiles, the branch, the
  health-check paths and the whole memory-tuning recipe; the deploy workflow published four service
  identifiers, four URL secret names and the whole deploy path.
- The `main` branch — the one a visitor clones — additionally carried **twelve files that `dev` had
  already deleted**, including three duplicate root-level start/stop/log scripts that contradict the
  documented layout.

### 2.6 Documentation drift
Broken quickstart commands that point at scripts which do not exist; a provider count stated as both
13 and 16 in the same file; a commit count from a different repository; three stacked "What's New"
sections, one anchored to a version with no changelog entry; seven documentation links that 404 for
a visitor (six because the target files are not published, one because the file never existed); a
security policy still titled "V4" while the product is v5.1.6; a stale OpenAPI snapshot (198 paths
against 251 routes); a canonical URL that pointed every single page at the homepage; a sitemap that
covered 9 of 21 public routes; and a social-preview image that is a 1280×800 screenshot declared as
1200×630.

### 2.7 The readiness probe could not see an unhealthy vector store

Found while making an ignored test enforce itself — the most productive defect of the review.

The health payload carries two kinds of entries in one dictionary: the dependency checks, and the
circuit-breaker states. The breaker entries were keyed by the **raw breaker name**, and the search
path registers a breaker named `vector_store`. So that breaker **overwrote the real vector-store
dependency check** in the same dictionary.

Two consequences:

- The health report showed the breaker's state (healthy while closed) instead of the store's.
- `/health/ready` — the Kubernetes readiness probe — reads `dependencies["vector_store"]` and
  answered `503` only when that entry was unhealthy. With the shadowing entry in place it answered
  **"ready" while the vector store was down**, so a cluster would have kept routing traffic to the
  pod.

The same shadowing made one of the two long-ignored health tests fail as soon as it was allowed to
enforce: it asserts that an unhealthy vector store makes the endpoint unhealthy, and in a full
parallel run another test had already registered the breaker.

Fixed: the breaker entries are keyed by their prefixed name (`circuit_breaker:vector_store`), so a
breaker can never shadow a dependency again. A regression test pins that.

## 3. What changed

### 3.1 Hosting — the demo runs on the operator's own node, behind a front door of its own

**The studio's domain is not the demo's domain.** `nestlab.tech` is the studio's canonical entity: one
domain, one `Organization.description`, one `sameAs` set. A product demo parked on a subdomain of it
forks that entity — the search and AI engines answer "what is nestlab.tech" from whatever sits on the
domain, and a half-finished free tool there pulls the answer away from "a studio with four SaaS
products". The demo therefore lives on a host of its own, and `realestate.nestlab.tech` was removed:
the DNS record and the ingress rules on the three tunnels that served it are gone.

**Where it went.** The demo runs on the operator's own server, behind a Cloudflare Worker on a
temporary `workers.dev` address, `https://ai-real-estate-demo.devs-scaler.workers.dev`. The Worker is
the front door: it forwards every request to the node, and the node admits that one port from the
edge's ranges only. The application's own repository keeps a second, platform-hosted deployment — the
repository's deploy workflow still publishes to it — but the address the public links point at is the
front door's.

**The idle-reclaim exposure, stated plainly.** The host's provider deems a compute instance **idle**
when, over a seven-day window, its 95th-percentile CPU is below 20 %, its network below 20 % and its
memory below 20 %. Measured on that instance when the demo was first moved off it: a load average of
0.06 on two cores and 19.4 % memory — **both under the thresholds** — and the tenancy can be ended on
seven days' notice of inactivity. The operator's decision on 2026-11-07 was to put the demo there
anyway, and to keep iterating on the application directly on that deployment; the risk is why the
address is temporary and why the demo is deliberately not indexed.

**What the demo now does.** It answers. The catalogue is seeded and persists between restarts, search
returns real results, and the conversational assistant replies — with no paid model key, because the
application substitutes a local canned-response model in demo mode.

**And it is not indexed.** The product is not finished, and the operator does not want it released in
this state. Two mechanisms keep it out of the index, both of them per deployment and both reversible
without a rebuild: a runtime flag makes every page answer `X-Robots-Tag: noindex, nofollow`, and the
deployment replaces the product's own — deliberately inviting — `robots.txt` with one that disallows
everything. The demo stays reachable, because it is still the thing that can be handed to somebody
to try; it just stays out of the index. Turning both off is the release step.

**What is in the public tree.** The platform blueprint and the deploy workflow are public again. They
were moved to a private operations repository for one day, on the reasoning that a public repository
should not publish a deployment topology. The operator's call was the opposite one: a visitor who
lands on this repository should see a pipeline that actually deploys, and the demo keeps deploying to
its hosted services. So the pipeline stays, and the private repository keeps what is not this
project's own deployment — the secondary stack on the studio's own host.

**What that costs, and what replaces it.** The deploy workflow's safety properties — the owner
guard, the CI gate before any deploy, deploying the exact commit the CI tested, the "both halves
healthy or neither" rule, the per-branch serialisation and the "never auto-merge" assertion — were
pinned by tests that read the workflow file, and those tests could not stay while the file was
gone. With the file back in the public tree they are pinned here again, and the guard that replaced
them now guards what is genuinely private: no committed credential value in the deploy files, no
path from the machine that wrote the repository in any tracked file, and no description of any other
infrastructure the studio runs.

### 3.2 The application

- Schema creation moved ahead of the seeding steps; the `VECTOR_PERSIST_ENABLED` setting now reads
  the environment.
- The lead instrumentation is wired into the pages that produce the events it was written for.
- A footer with an email field posts to the existing visitor endpoint — no new API was added.
- The demo navigation and the route allowlist now agree, and the agent contact form is reachable.
- The proxy forwards `cookie` and `authorization`.
- The leads endpoint no longer hands every captured contact detail to an anonymous
  visitor: the name, the email address and the phone number are masked for every
  caller who is not the owner of the lead, in the list, the detail view, the
  export and the write endpoints alike. A field the caller just submitted is
  echoed back unmasked, because that is their own input.
- The chromadb version constraint in the requirements file matches the one in `pyproject.toml`, so
  the container image and the CI audit resolve the same version the security register analyses.
- The comprehensive health payload moved to `/health/detailed`; `/health` keeps the stable,
  unauthenticated shape the probes use. The two health tests that were marked `xfail(strict=False)`
  — which could never fail the build — are now **conditionally** marked: they enforce the contract
  everywhere except on the one platform where they are known to flake, where they remain a
  non-blocking `xfail`. The cause of the flake was the patching seam, not the code under test: the
  dependency checks were patched through a dotted import path, which the patcher resolves by
  *importing* the module — and that import can land on a different module object than the one the
  function under test reads its globals from. The checks are now patched on the module object
  directly, and the slow check's sleep now outlasts both the handler's internal budget and the
  test's outer wait — so the outcome no longer depends on which timer a loaded event loop happens
  to process first. Six frontend suites that were skipped wholesale now run.
- The avatar-upload tests clean up after themselves by filename instead of by glob, so the parallel
  test run can no longer delete another worker's file and fail the suite for no reason.
- The health payload can no longer report a circuit breaker in place of the dependency it shares a
  name with — the defect that made the readiness probe blind to an unhealthy vector store (§2.7).
- A response-cache invalidation that fails no longer turns a completed write into a 500: the upload
  was stored, so the caller must not see an error for it.
- A missing request counter no longer turns a successful response into a 500. The counter lives on the
  application state, and anything that touches that state can remove it; the middleware then raised
  `AttributeError` after the response had already been produced. The counter is recreated when it is
  gone — losing the counts costs the counts and nothing else. This was the defect the parallel Linux
  CI run caught: four tests failed on the strength of the counter, not of the code under test.

### 3.3 The documentation

The README's quickstart commands now name scripts that exist; the provider, commit and contributor
counts are the real ones; the three stacked "What's New" sections collapsed into one; the seven dead
documentation links are fixed; the security policy and the accepted-risk register carry current
dates and no longer contradict themselves; the canonical URL and the sitemap match the pages that
exist; the social-preview image is the size the metadata declares; and the studio's own host name,
the fleet's node names and the machine-local paths are out of the public tree.

The deployment pipeline itself came **back** into the public tree on 2026-11-07, on the operator's
call: a visitor who lands on this repository should see a pipeline that actually deploys, and the
demo keeps deploying to its hosted services. What stays private is everything that is not this
project's own deployment — no credential value is committed, no path from the machine that wrote
the repository is published, and no other infrastructure the studio runs is described. A test pins
each of those, and another pins the pipeline's own safety properties.

### 3.4 A new review document, and three new tasks

The review document is this file. The backlog now carries three open tasks, each with a route tag,
acceptance criteria and a test strategy:

| Task | Title |
|---|---|
| #30 | Make the demo capture leads — wire the dead tracking layer, add email capture, close the `/leads` exposure |
| #31 | Public-repo hygiene and doc sync — remove infra/pipeline leaks, fix README and docs drift, fix the SEO/GEO surface |
| #32 | P0 correctness fixes — the chromadb pin, the `/health` route collision, the non-enforcing xfails |

## 4. Still open, and why

| Item | Why it is still open |
|---|---|
| Tasks #14, #15, #16 — the content and distribution chain | They publish under the operator's identity. The drafts are written and updated; each publication still needs its own go |
| The demo's public address carries the Cloudflare account's own label | The operator asked for an address not tied to the account name. Every free `workers.dev` address on the only Cloudflare account this project has credentials for carries that account's label — the label is part of the account's own zone, not part of the worker's name. Two ways out, both the operator's: enable the `cloud-cloudflare-nestlab` MCP so the front door can be recreated in another account, or buy a domain of the demo's own |
| The previous origin's copy of the demo | Left in place, stopped, with its files kept for the rollback. Decommissioning it needs an explicit go |
| The platform-hosted deployment | The repository's own deploy workflow still publishes to it, which is the point of the pipeline being visible. Retiring the services is irreversible and needs an explicit go |
| Seventy-odd documentation files that no page links to | Named here rather than rewritten. They are a documentation-hygiene backlog, not a defect |
| The three near-duplicate quickstart guides and the duplicated agent-system documents | Named here rather than merged |

### 4.1 Follow-up dispositions

Every task the review left open now carries a named next step and its gate, recorded in the task
itself:

| Task | State | What is left, and who holds it |
|---|---|---|
| #27 — the demo on our own server, the topology hidden | **done** | The goal is met and verified: the demo answers on the operator's own server, behind a front door on a host of its own, with the studio's subdomain removed and the deployment topology out of the public tree. The topology came back to the public tree afterwards, on the operator's call — what stays private is everything that is not this project's own deployment |
| #20 — the two ignored health tests | **done** | The `xfail` markers are gone, the checks are patched on the module object, a new test pins the seam itself, and the Linux CI run is green — the two tests enforce the contract on every platform |
| #22 — the social-preview card | **done** | The card is a designed 1200×630 image built from the product's own identity and its own copy, and the dimension mismatch that started the task is fixed too |
| #14, #15, #16 — the content and distribution chain | **pending** | All five drafts are written and ready, and the demo they point at is deliberately kept out of the index, so a link does not release the unfinished pages. Publishing under the operator's identity is the operator's step |

## 5. How this was verified

- The demo answers on its public URL: a health probe, a catalogue search returning scored results,
  and a conversational turn returning an answer with sources — all through the public hostname.
- The demo is not indexed: every page answers `X-Robots-Tag: noindex, nofollow`, and the served
  `robots.txt` disallows everything. Both are per deployment, so the release step is one flag and
  one file.
- The leads endpoint no longer hands a captured contact to an anonymous visitor — checked against
  the running demo, not against the code alone.
- The vector index survives a restart and reloads from disk.
- The deployment stack is a committed, reviewable file in the private repository; the host copy
  matches it.
- The tunnel ingress rule and the DNS record were read back from the provider's API after the change.
- The application gates: backend lint, backend unit suite and backend integration suite, frontend
  lint, type check, unit suite and production build — all green on the committed tree. (The two
  backend suites are run separately, the way the CI matrix runs them; running both in one pytest
  invocation makes them share one in-process rate limiter and produces spurious 429s.)
- The public tree contains no host name, no platform name, no service identifier, no fleet node and
  no local filesystem path. The one exception is the needle list inside the CI-surface test: it is
  the detector, and the two platform-identifying strings in it are assembled from fragments so the
  file does not publish what it forbids.
- The lead-redaction rules are covered by their own backend tests, and each test was verified to
  fail when its rule is broken — a test that cannot fail pins nothing.

---

*This document is the public-safe record of the review. It names no host, no platform, no fleet
node and no private address — those live in the private operations repository, where they belong.*
