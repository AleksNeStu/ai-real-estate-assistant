/**
 * Which locales the interface is maintained in.
 *
 * English and Polish are the pair the product is written for. Polish is the
 * home market — the demo catalogue, the currency and the x-default come from
 * it — and English is the language every provider, every partner and every AI
 * reader understands. A new key lands in these two catalogues only.
 *
 * The other seven keep the wording they were given. They still ship: their
 * URLs, their hreflang entries and the language switcher stay, and the merge
 * in `merge.ts` fills whatever they do not carry with the English wording. A
 * feature therefore costs two translations instead of nine, and the seven
 * older catalogues age into the backlog instead of blocking every change.
 *
 * The lists live in `config.ts` — that is where the locales of the interface
 * are named — and this module is the one a rule or a test asks: "is this
 * locale kept up to date?"
 */

import { maintainedLocales } from './config';

export { frozenLocales, maintainedLocales, type MaintainedLocale } from './config';

/** Whether a locale is kept up to date with every new key. */
export function isMaintained(locale: string): boolean {
  return (maintainedLocales as readonly string[]).includes(locale);
}
