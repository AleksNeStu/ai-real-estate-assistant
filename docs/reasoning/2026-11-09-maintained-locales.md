---
id: 2026-11-09-maintained-locales
date: 2026-11-09
area: i18n
scope: apps/web
status: accepted
---

# The interface ships in nine languages and is maintained in two of them

## Situation

The interface shipped in nine locales, and the rule was that a new key landed
in all nine catalogues in the same commit. The English catalogue was the
source; the other eight carried the translated string at the same JSON path
with the same ICU placeholder names. The key-parity test held the rule.

The operator asked what translation actually earns — for SEO, for GEO, for
leads, for partners — and noted that it makes development harder. Then the
order came: follow English and Polish, and move the rest of the languages to
the backlog.

The cost was never the translation. 210 landing strings in eight languages
landed in one session. The cost was the gate: the key-parity test plus three
hardcoded locale lists plus a `seo.structuredData.languages` entry per
catalogue. Every feature paid that tax nine times over.

## Options

1. **Keep nine in lockstep.** The old rule. Every feature costs nine
   translations and nine catalogue edits, and the queue of work that waits for
   a translator is the queue of features that do not ship.
2. **Drop the seven.** Remove the locales, their URLs, their hreflang
   entries, their language-switcher entries and the "nine interface
   languages" claim that nine catalogues and the JSON-LD carry.
3. **Freeze the seven.** They keep shipping and keep the wording they were
   given; whatever they do not carry is rendered in English. The reach stays,
   the tax goes.
4. **Freeze the seven and give the freeze a trigger.** Option 3, plus a rule
   for when a frozen locale is brought back to the maintained pair.

## Reasoning

Option 1 is the tax itself. The point of the change is to stop a feature from
waiting on eight translations it does not need today.

Option 2 destroys reach to save work. It costs 112 sitemap URLs, eight
hreflang entries, the language switcher, and a claim that nine catalogues and
the structured data make. The operator's own framing — "the rest of the
languages to backlog" — is a statement about the queue, not about the
interface.

Option 3 is the one that keeps both. The nine locales stay in
`config.ts`, in the hreflang cluster, in the sitemap and in the JSON-LD; the
search and AI surfaces keep their reach. What changes is the rule that made
each of them a blocker.

Option 4 adds the trigger, and the trigger is already measurable:
`Lead.page_url` in `apps/api/db/models.py` carries the locale prefix, so the
traffic of a locale is countable without new instrumentation. A locale that
earns traffic is refreshed; one that does not stays frozen and costs nothing.

The wrong paths, because they look right until they are measured:

- **"Just drop the keys from the frozen catalogues."** The server-side
  `getMessageFallback` would cover the server, and the client would render
  the key path. Measured: with the fallback absent on the client, a missing
  key rendered `[landing.hero.title]`. next-intl's client `useTranslations`
  does not inherit the server's fallback — which forced the merge rather than
  a deletion.
- **"Merge the arrays position by position."** A row of the comparison table
  is a row. Positional merging mixes one locale's capability name with
  another locale's column, and the order diverges the moment English inserts
  a row. An array is taken whole.
- **"Put the maintained/frozen lists in `config.ts`."** A concurrent session
  was working on the same files and reverted that file twice. The split now
  lives in its own module, `apps/web/src/i18n/policy.ts`, so the policy has
  one owner and does not depend on a file two lanes edit.

The doctrine the decision rests on: **GTM-01** (stand where the money already
flows — the home market here is Polish: the demo catalogue, the currency and
the x-default are Polish), **GTM-03** (think in markets, not tools — a
translation is not a market), **GTM-22** (SEO and GEO from day one — the
hreflang cluster and the nine-language claim stay, so the reach does not
shrink), **GTM-29** (fit the product to its geo — English and Polish are the
two geos the product actually has).

## Evidence

Checked live:

| Check | Result on 2026-11-09 |
|---|---|
| Catalogue parity before the change | nine locales, 2966 leaves each, missing 0, extra 0 |
| Client fallback without `getMessageFallback` | renders `[landing.hero.title]` — the key path |
| Placeholder drift (`{count}` where English says `{amount}`) | renders the key path |
| `npx jest` after the change | 91 suites, 1369 tests, all green |
| `npx tsc --noEmit` | clean |
| `npm run lint` | 0 errors (26 pre-existing warnings) |
| Polish leftovers | `landing.footer.openSource` and `shell.landing.openSource` were `Open source`; now `Kod otwarty` |
| Polish catalogue | 0 missing keys, 0 extra keys, 0 placeholder mismatches, 0 Cyrillic |

Inferred, not checked: that a frozen locale has traffic worth refreshing.
The traffic is countable — the mechanism is there — but no locale's traffic
was read.

## Decision

**The interface ships in nine locales and is maintained in two of them.**

- `en` and `pl` are the maintained pair. A new key lands in
  `apps/web/messages/en.json` and `apps/web/messages/pl.json` in the same
  commit, never English-first.
- `ru`, `de`, `es`, `it`, `pt`, `tr` and `uk` are frozen. They keep their
  wording, they are allowed to lag behind, and they are not touched by a
  feature.
- A frozen locale renders the English wording of anything it does not carry.
  The merge in `apps/web/src/i18n/merge.ts` fills the gap and
  `apps/web/src/i18n/catalogue.ts` hands the same merged object to the server
  components and to `NextIntlClientProvider`, so a key path never reaches the
  screen.
- The key-parity test now holds the maintained pair to identical key sets,
  forbids any locale from inventing a key or from naming its placeholders
  differently, and asserts that every locale renders the English key set. A
  frozen catalogue may lag; it may not break.
- The seven languages are backlog (TaskMaster #63). One is refreshed when its
  traffic justifies it.

## Consequences

- A new namespace costs two translations instead of nine. The gate that
  enforced nine is gone.
- The nine-language claim stays true. The seven frozen locales render their
  own wording on everything they were translated for, and English on anything
  newer — which is a fact about the freshness of seven catalogues, not about
  the interface.
- A frozen locale that falls far behind becomes a half-translated page. The
  fallback keeps it readable; it does not make it native.
- The Polish catalogue is the one that must be right, so it gets the quality
  pass: two English leftovers were found and fixed in this change.
- `config.ts` still lists nine locales and must keep doing so. Removing one
  is a separate decision with a separate cost, and it was not taken here.

## Revisit when

- A frozen locale's traffic justifies a refresh — measured from the locale
  prefix of `Lead.page_url`.
- The operator decides to drop a locale rather than freeze it, which would
  cost the URLs, the hreflang entries and the JSON-LD claim.
- A ninth language is added, or the maintained pair changes, which would mean
  re-reading this decision rather than following it.
