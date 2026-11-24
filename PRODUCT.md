# PRODUCT — what this repository is, and what it is not

> The drift lens. A change that contradicts this file is a defect, not a
> preference. Every statement here is a fact about the tree as it stands —
> none of them is a promise about a future release.
>
> Sources: `README.md`, `CLAUDE.md`, `DESIGN.md`, `docs/adr/`,
> `docs/plans/plan-mode/typed-tickling-frog.md`, and the code itself.

## One sentence

An open-source conversational assistant for property search: you ask in plain
language, it answers with matched listings and the financial tools around them
— mortgage, comparison, ROI, valuation — over your own data, on your own
machine, with your own LLM keys.

## Who it is for

| Audience | What they do with it |
|---|---|
| **Developers and self-hosters** | clone it, point it at their own data (a spreadsheet, a CSV, their own catalogue), bring their own model keys, and read the code. The stars and the forks are the metric that matters here. |
| **Real-estate professionals** | the second audience: lead scoring, an agent board, CMA, e-signatures, portfolio analytics. These are the surfaces the hosted tier sells. |
| **A visitor on the public demo** | `https://realty.kittray.com` — no login, no keys, no install: search, ask, read a listing, get an official price, and decide whether to talk to the studio. |

## The two tiers, and the line between them

| | This repository (free, MIT) | PropVector AI (hosted) |
|---|---|---|
| Conversational search, tools, valuation, buyer memory, accounts, alerts | ✅ | ✅ |
| **Official notarial transaction prices** (Rejestr Cen Nieruchomości) | ✅ — free by law since 13 Feb 2026 | ✅ |
| Bring-your-own keys, 17 providers, local Ollama | ✅ | ✅ |
| **Live listing feeds** (a real feed, not the register) | ❌ | Pro |
| More countries | ❌ | Pro |
| AI CRM, bi-directional sync, CRM connectors | ❌ | Pro / Enterprise |
| SSO, MFA, white-label, SLAs | ❌ | Enterprise |

**The line is deliberate and it does not move with the roadmap.** The register
is the free tier's substance: it is published by the state mapping office and
it is free of charge for everyone, so charging for it would be selling a public
record behind a paywall. What the hosted tier sells is what the register is not:
live listing feeds, more countries, the CRM around them. Free `$0` · Pro `$29/mo`
· Enterprise (custom) — and the tiers may move before launch.

**Consequence for the code:** anything that needs a paid listings API, a
payment, a CRM connector or another country belongs to the hosted tier, not
here. A task that needs one is not blocked — it is *out of scope*, and it is
named as such.

## The invariants

1. **One entity, one name.** The same thing is called the same thing in the
   code, the database, the interface and the e-mail. See
   `docs/domain/GLOSSARY.md`.
2. **The demo needs no login.** A visitor on the public address reaches the
   whole public journey — search, chat, a listing, a city, a valuation, the
   official price — without an account. Only the **account** routes are gated
   (favourites, saved searches, documents, leads, settings, usage,
   agent-analytics, admin): they are the account's, and the gate says what the
   account gives.
3. **The published capabilities describe the running deployment.** The
   endpoint says what the deployment can actually do — a real mail transport, a
   real model, a real register — and says it the same way on every page.
4. **An answer carries its evidence.** A price names the register, the
   comparables, the sample size and the period. A search names its sources.
   The app never invents a number.
5. **The engine stays MIT.** The hosted server, if it is ever published, goes
   out source-available — never MIT (ADR-0009).
6. **The interface keeps both themes.** The visitor chooses light or dark.
   The *materials* the studio publishes (README images, screenshots, the social
   preview, the clips) are dark only.

## The funnel — where a visitor is supposed to end up

```
landing (hero instrument · feature ledger · exit cards · studio strip · waitlist)
  → UTM-tagged outbound link → reportOutbound() → POST /api/v1/analytics/outbound
  → the click becomes an interaction on the visitor's lead
  → the lead lands on the agent board (leads, funnel, high-value rail)
  → the visitor is invited to nestlab.tech (the studio) or propvectorai.com (the hosted tier)
```

The waitlist form promises an e-mail only when `GET /api/v1/capabilities`
says `lead_capture.waitlist_enabled` — that is, when a real mail sender is
configured. On a deployment without one it says so instead of claiming a
subscription it cannot keep.

## The surfaces that are public

Every one of them answers, and every one of them is read live before it is
called done (Rule 106 §13):

| Surface | Path |
|---|---|
| landing | `/`, `/en`, `/pl`, `/ru` |
| search | `/[locale]/search` |
| chat | `/[locale]/chat` |
| listing | `/[locale]/property/[id]` |
| city overview | `/[locale]/city-overview` |
| valuation | `/[locale]/valuation`, `/[locale]/valuation/[place]` |
| market trends | `/[locale]/market-trends` |
| tools · analytics · showcase | `/[locale]/tools`, `/[locale]/analytics`, `/[locale]/showcase` |

## Definition of done, per change

- The gate is green: `python scripts/workflows/full_ci.py` (lint, pytest with
  coverage, Jest with its thresholds, e2e, the security scans).
- Every changed public URL is read **live**, and its coverage state read
  second.
- The change is committed on `dev` with a conventional message and **no
  AI co-author trailer**.
- No claim in the README, the landing copy or the capabilities endpoint
  became untrue. If it did, the claim is corrected in the same change.

## The honest limits

- The register lags the market by 6–12 months and is not published for every
  district — so the answer always shows its sample size, its period and its
  comparison area, and widens them when the sample is thin.
- The catalogue in the demo is **seeded** unless a real dataset is ingested;
  the official prices are real either way.
- The seven non-maintained locales fall back to English by design.
