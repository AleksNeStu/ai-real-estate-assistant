---
id: 2026-11-24-maintained-locales-ru
date: 2026-11-24
area: i18n
scope: ai-real-estate-assistant
status: accepted
task: "TaskMaster #63"
---

# The Russian catalogue joins the maintained set

## Situation

The interface ships in nine languages and was maintained in two of them. English and Polish
carry every key; the other seven catalogues hold the wording they were given and fall back to
the English wording for anything newer — `apps/web/src/i18n/merge.ts` merges the English
catalogue with the locale's, so a frozen locale renders English text rather than a key path.
TaskMaster #63 was the standing backlog for bringing one of the seven back.

The Russian catalogue was the worst of the seven in practice: at 85.3 % of the English leaf set
(2 983 of 3 497 leaves) it was missing 514 keys — the buyer memory, the model catalogue, the
CMA preview, the valuation register, the whole `pages` namespace that the redesign introduced.

The operator was asked which of the seven to bring back and chose Russian. The reason is the
obvious one: it is the language the operator reads, so the product's own operator-facing
surfaces — the settings page, the memory panel, the lead board — can be read without a
translation step.

## Options

| Option | What it costs | Why it was not chosen |
|---|---|---|
| **Russian (chosen)** | 514 new strings, and every future key also lands in Russian | — |
| German | the same 514 strings | the largest audience of the Polish market, but the operator does not read it |
| Ukrainian | the same 514 strings | a neighbour market the catalogue stories already reach; same reading problem as German |
| Leave all seven frozen | nothing today | the frozen catalogues age: the redesign's 413 `pages` keys would stay English for Russian readers forever |

## Reasoning

**The wrong path that looked right.** The cheap version of this task is to add `ru` to
`maintainedLocales` and let the merge fill the gap — the interface would still *work*, because
the merge falls back to English. That is exactly what "frozen" means, so it would have looked
like the task was done. It is not: the deliverable of #63 is a Russian interface, and a half
Russian one with an English settings page is not that. The 514 leaves had to be written.

**The second wrong path.** Translating by machine and trusting it. Two problems: the wording
would not match the tone of the existing catalogue (the plural forms are the visible part —
`ru.json` already carries `one/few/many/other` where Polish carries `one/other`), and a
machine translation of the buyer-memory text would say something the product does not promise.

**The method.** 112 of the 514 missing strings were English texts the catalogue already
carries elsewhere — "Save", "Confirm", "E-mail + password" — and were filled from the
existing Russian wording for the identical English string. The remaining 402 were written by
hand, namespace by namespace, keeping every placeholder name (`{count}`, `{address}`, `{size}`)
exactly as English has it, because `merge.ts` falls back to the English wording when the
placeholder names differ.

**Why the ordering of the merge matters.** The rebuilt catalogue keeps the locale's own key
order and appends the new keys inside their parent object, so the diff is additions only. A
rebuild in the English order would have rewritten the whole file and buried 514 real changes
in 3 000 reordered lines.

## Evidence

- **Measured before:** `en.json` 3 497 leaves, `ru.json` 2 983 leaves, 514 missing, 0 invented,
  0 placeholder mismatches (`scripts` in the session temp dir, the same four checks the Jest
  parity test makes).
- **Measured after:** `en.json` 3 497 leaves, `ru.json` 3 497 leaves, 0 missing, 0 invented,
  0 placeholder mismatches, the unit sets equal.
- **Enforced in CI:** `apps/web/src/lib/__tests__/i18n-key-parity.test.ts` walks
  `maintainedLocales` — with `ru` in the list it now fails if a key is added to English and
  Polish but not to Russian.
- **The cost, stated:** a feature now costs three translations instead of nine, and the six
  remaining frozen catalogues keep their place in the backlog.

## Decision

`ru` joins `maintainedLocales` in `apps/web/src/i18n/config.ts`. Its catalogue carries every
English key. The six other frozen locales are unchanged.

## Consequences

- A new key must land in `en.json`, `pl.json` and `ru.json`; the parity test fails otherwise.
- The Russian interface stops falling back to English on the 514 keys this change added.
- The remaining six frozen catalogues are untouched and still age into the backlog.
- The interface text is content for visitors. The repository's own code, comments, commits and
  documents stay English — this change adds no Russian to any of them.

## Revisit when

- The interface drops below nine locales, or the Russian catalogue stops being kept in step for
  two releases in a row — then Russian goes back to being frozen and the six become eight.
- A fourth maintained locale is proposed: the cost per feature becomes four translations, and
  the decision record for this one has to be revisited alongside it.

## Related

- [The interface ships in nine languages and is maintained in two of them](2026-11-09-maintained-locales.md)
  — the split this change widens, and the key-parity test it introduced.
