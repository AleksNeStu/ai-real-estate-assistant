---
id: 2026-11-22-free-tier-and-hosted-tier
date: 2026-11-22
area: licensing
scope: repository
status: accepted
---

# The engine stays MIT, the hosted tier stays closed, and the server is never MIT

## Situation

This repository is MIT (ADR-0009: `docs/adr/0009-project-license-mit.md`), it is
public, and it is the top of a funnel whose bottom is a hosted product,
PropVector AI. Stage 0 landed the thing that made the split worth writing
down: the free tier now answers with **official transaction prices from the
Rejestr Cen Nieruchomości (RCN)** — the register of notarial prices — instead
of a seeded catalogue that only looks like data.

That changes what each tier *is*. Before Stage 0 the free tier shipped a demo
catalogue and the paid tier shipped "real data", so the open-core split was a
promise about the future. Now the free tier ships the register, free by law,
and the paid tier has to ship something the register is not.

Three claims were floating around the repository without a record: the compare
table says the hosted version "comes next", the plan says the tiers are
complementary, and the natively reading says their licence is the model. None
of them was written down where a future reader could check it, and the
repository's own precedent (`docs/reasoning/2026-11-09-maintained-locales.md`)
says a decision that is not on disk is a decision that gets re-litigated.

## Options

1. **One licence for everything.** MIT the engine and MIT the server. The
   server becomes something anyone can run and resell.
2. **One licence for nothing new.** Keep MIT, change nothing, and let the
   hosted tier's licence be whatever it happens to be when it ships.
3. **MIT engine, closed server, with the boundary written down.** The engine
   stays MIT; the hosted tier is proprietary and is not published; and if the
   server is ever published, it goes out source-available — never MIT.
4. **Copy the natively licence onto this repository.** Theirs is
   "Personal Use Source License v1.0": personal, educational and
   non-commercial use only, no SaaS, no competing product.

## Reasoning

Option 1 is the one that looks like generosity and is actually the dangerous
one. MIT on the server means anyone can run the hosted tier's machinery and
sell it as a service — the licence would hand the competitor the product. The
engine is not the risk: the engine is the thing we want copied.

Option 2 is what the repository is doing by default, and the default is what
produced the mess this record exists to fix: the compare table and the
reasoning log rest on a split nobody wrote down. "We will decide when the
server ships" is a decision deferred to the moment it is most expensive to
take.

Option 3 is the one that keeps both properties the business actually needs.
The engine's MIT is the funnel, the stars, the contributors and the sponsor
revenue — ADR-0009 already settled it and nothing since has argued against
it. The hosted tier is the running service: live listing feeds, more
countries, alerts, the AI CRM and its bi-directional sync, connectors,
SSO/MFA, white-label and SLAs. None of that is in this repository, and none of
it is worth publishing — a competitor reading the feed adapters and the CRM
sync would be helped, and a user running it would be a support ticket.

The middle option inside option 3 — source-available for a server that is ever
published — is the part worth spelling out. "Published" and "MIT" are not the
same question. If a server is ever published, the licence must forbid
commercial use and forbid running it as a service, and it must keep that
restriction in forks. That is source-available, and it is deliberately a
weaker promise than MIT.

Option 4 is a misreading of the model we are copying. The natively repository
is described as open source; its licence file says *"Natively is
source-available, not open source"*. The label in the description is marketing.
Their stars did not come from the licence — they came from the **install**
(a download that works the moment it is installed, a Homebrew cask) and from
the **distribution** (sponsor, site, Telegram, launch). We are an order of
magnitude behind on stars while holding a *more* permissive licence. The gap
is packaging and distribution, and the answer to it is the CLI, the one-command
installer and the PWA — not a licence downgrade.

The wrong paths, because they look right until they are measured:

- **"The free tier is the demo, so the register is a paid feature."** The
  register is free to everyone by law since 13 February 2026. Charging for it
  would be selling a public record behind a paywall, and it would contradict
  every page the repository publishes.
- **"The seeded catalogue is the free tier's substance."** It is 250 rows of
  seeded text. A comparison against the register's real transactions is a
  different product, and it is the one a buyer can check.
- **"Publish the server under MIT later if there is demand."** Demand for the
  server is exactly the case where MIT is the wrong answer: the people who
  want to run it themselves are the people who would rather not pay.

The doctrine this rests on: **GTM-01** (stand where the money already flows —
the running service, the feeds, the CRM), **GTM-03** (think in markets, not
tools — a licence is not a market), **GTM-22** (SEO and GEO from day one — the
open repository is the acquisition surface, which is why its licence stays
permissive), **GTM-29** (fit the product to its geo — the free tier is
Polish, so the free tier's substance is the Polish register).

## Evidence

Checked live on 2026-11-22:

| Check | Result |
|---|---|
| RCN data became free of charge | Dz.U. 2025 poz. 1542, published 12.11.2025, in force **13 February 2026** (GUGiK notice on gov.pl, 13.11.2025) |
| The register is published and free today | geoportal.gov.pl's RCN page: WMS/WFS service at `mapy.geoportal.gov.pl/wss/service/rcn`, published by GUGiK after the fee was waived |
| The distribution rules around it | the amending regulation entered into force 28.08.2026; starostas must adapt their own publication by 30.09.2026 (GUGiK notice, 28.08.2026) |
| The engine is MIT in the tree | `LICENSE`, root `package.json`, `apps/api/pyproject.toml`, README badge — and ADR-0009, which chose MIT over AGPLv3 deliberately |
| The RCN valuation is implemented, not promised | `apps/api/data/rcn/rcn_client.py`, `apps/api/services/rcn_valuation.py`, `apps/api/tools/rcn_valuation_tool.py`, with tests under `apps/api/tests/` |

Read live on 2026-11-22 by the plan's Stage 5 pass, and not re-verified here:
the natively licence file ("Personal Use Source License v1.0" — personal,
educational and non-commercial only, no SaaS, no competing product, forks keep
the licence, attribution required), their scale (3363 stars, 706 forks, 300k+
downloads) and ours (325 stars, 117 forks).

Inferred, not checked: that the free tier's register answer will be worth more
to a visitor than a seeded catalogue. The register is real and free; that it
converts is a hypothesis that only the traffic and the waitlist can answer.

## Decision

**The engine stays MIT. The hosted tier stays closed and is not published. A
server that is ever published goes out source-available — no commercial use,
no SaaS — and never MIT.**

- The **free tier** (this repository, MIT) ships, as of Stage 0: the official
  notarial transaction prices from the Rejestr Cen Nieruchomości, free by law
  since 13 February 2026, plus the 250-listing seeded catalogue as the browse
  surface. It keeps the MIT licence (ADR-0009) and the self-hosting story.
- The **hosted tier** (PropVector AI) ships: live listing feeds, more
  countries, alerts, the AI CRM and its bi-directional sync, connectors,
  SSO/MFA, white-label and SLAs. It is proprietary. It is not published, and
  its private PRDs stay out of this repository.
- The **licence discipline**: the engine stays MIT. If a server is ever
  published, it is source-available — commercial use forbidden, running it as
  a service forbidden, the restriction carried into forks. Never MIT on the
  server: MIT there would let anyone resell it.
- The **natively reading is corrected in the record**: their repository is
  source-available, not open source, and their stars came from the install
  and the distribution, not from the licence. This repository does not
  downgrade itself to "personal use" — it closes the packaging gap instead
  (TaskMaster #124, #125, #126).

## Consequences

- The public compare table has to state what each tier ships **today**, and
  the free tier's entry is now "official notarial transaction prices" rather
  than "a demo catalogue" (TaskMaster #123). A table that lags the code is
  the same lie the FAQ JSON-LD was telling.
- The public client (`packages/cli`, TaskMaster #124) may point at a local
  self-hosted instance or at the hosted one. The base URL decides, so the
  client can be MIT without making the service MIT.
- The self-hosted tier stays a first-class path, so "run it yourself" is not a
  consolation prize for people who cannot pay — it is the funnel.
- Publishing the server becomes a decision that must be taken deliberately,
  with a licence that is not MIT. Until then, "not published" is the answer.
- If the studio's paid product changes what the hosted tier ships, this record
  is superseded by a new one — it is not edited.

## Revisit when

- The hosted server is published in any form, or a fork of it appears — the
  licence question stops being hypothetical.
- The compare table's tier list changes, or a third tier appears.
- The natively licence or their packaging changes the reading this record
  rests on — it was read live on 2026-11-22 and is dated.
- The register's terms change — GUGiK's publication rules were still moving
  (the amending regulation took effect on 28.08.2026, and the starostas'
  own services had to adapt by 30.09.2026).
