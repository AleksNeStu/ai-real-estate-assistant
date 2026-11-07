# Brand and discovery — how this project reaches people

*2026-11-07. The reasoning behind the public face of this repository: what it
says, how it is found, what it looks like, and what it is for.*

## The funnel, in one paragraph

This repository is the free, open-source version of a product with a paid
version behind it. The visitor arrives for one of three reasons: to use the
tool, to run it on their own server, or to read the code. All three are worth
having — and all three end in the same place: the studio. The hosted version
(PropVector AI) is the product; the studio is the service; this repository is
the open door to both.

That shape is a decision, not an accident. A branded free tool invites "whose
data is this?" and moves the stars off the repository, which is the one asset
the open-source version owns and the hosted version cannot have (GTM-30/31:
promotion is the moat, the code is not). So the identity of the project stays
with the project, and the studio appears as a clearly labelled channel
(GTM-26: value before registration).

## SEO — the project page

GitHub pages are indexed; the deployment is deliberately not (`SEARCH_INDEXING=false`
plus a robots.txt that disallows everything, per the operator's decision of
2026-11-07). So the repository carries the search surface, not the demo.

| Surface | State |
|---|---|
| Repository description | "Open-source AI real estate assistant: RAG + vector search over your own listings, 16 LLM providers, FastAPI + Next.js. Run it on your own server with Docker, or try the live demo." |
| Topics | `self-hosted`, `docker`, `langchain`, `ai-assistant` next to the technical ones |
| README first screen | what it is, in one paragraph, in the first 200 words |
| Headings and anchors | generated table of contents, every internal link verified |
| Release notes | a short highlights list; the details stay in the changelog and on the release page |
| Structured data | `Organization`, `WebSite`, `SoftwareApplication`, `FAQPage` — in the app, for the deployed site |
| Canonical URL | one setting (`SITE_URL`) that the build reads; changing the address is one release |

## GEO — being cited by answer engines

An answer engine quotes a source that states a fact plainly and makes it easy
to lift. `llms.txt` is the shape for that, and it answers the questions an
engine is actually asked: when to use this, when not to, what it can do, how
to run it, who builds it.

Two sections were added on 2026-11-07:

- **"Run it on your own server"** — the compose file, the deployment guide, the
  automated deploy workflow, the published image names, the one-click hosted
  option. This is the answer to "can I run this myself", which is the question
  that brings developers.
- **"Who builds this"** — the studio, the hosted version, and the studio's
  other products. An engine asked "who is behind this project" can answer from
  the file instead of from a guess.

The README carries the same two blocks, in prose, for a human reader.

## IEO — matching the intent

"Intent engine optimization" is the layer where the query decides the answer.
Four intents arrive at this project, and each one must find its answer in the
first screen:

| Intent | Where the answer is |
|---|---|
| "What is this?" | the headline and the first paragraph |
| "Can I run it myself?" | "Deploy it your way" — the compose file and the workflow |
| "Is there a paid version?" | "The hosted version, and what comes next" |
| "Who is behind it?" | the studio line in the footer, and "More from the studio" |

The "Questions people actually ask" block in the README answers the six
questions that are asked in issues and discussions, in the place where a
reader or an engine can lift them verbatim.

## The brand

`DESIGN.md` asks for an elegant, **monochrome** language with a neutral zinc
palette: the property data and the map carry the colour, the chrome stays
quiet. The old icon contradicted that — a blue circle with a bolt, a generic AI
mark that belonged to no product.

The mark is now a **roof over a single point**: the property, and the listing
inside it. Zinc-950 on a zinc-50 tile, two shapes, legible at sixteen pixels,
identical in the light and the dark interface. It ships as the app icon, the
favicon (regenerated from the same source), the PWA icons in both SVG and PNG,
the social card, and the mark at the top of this README.

The social preview was a screenshot of the application. It is now a card: the
mark, the name, the promise, and the four facts a visitor needs (MIT,
self-hosted, 16 providers, 9 languages).

Two broken references were fixed on the way: the PWA manifest pointed at an
icon file that did not exist, and it declared a screenshot size the card did
not have.

## What is left, in order

1. **The public address.** `kittray.com` is delegated to Cloudflare by the
   operator; the demo moves to `realty.kittray.com` when that happens, with
   `SITE_URL` set and one release. Until then the demo answers on the
   workers.dev address it has today.
2. **The repository avatar.** GitHub has no API for it — the file is
   `apps/web/public/logo.svg`, and it is a drag onto the repository picture.
3. **Distribution.** The launch drafts under `docs/marketing/` (Show HN, Reddit,
   Product Hunt, directories, video) are written and unused; they are the next
   surface, and they are the only channel that brings people who have never
   seen the repository.
4. **The hosted tier.** PropVector AI is the product this repository funnels
   into. It is the only one of the four surfaces that can charge.

## What would prove it works

- Stars and forks per month, and the share of them that come from the
  self-hosting path rather than from the hosted demo.
- The demo's lead capture: how many visitors leave an address, and how many of
  those become a studio conversation.
- How often the repository is quoted by an answer engine, and for which
  question. That is the GEO metric, and it is not visible in the traffic
  numbers — it has to be looked for by asking.
