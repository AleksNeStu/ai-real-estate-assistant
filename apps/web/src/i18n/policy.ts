/**
 * Which locales the interface is maintained in.
 *
 * English, Polish and Russian are the set the product is written for. English is
 * the default the site opens in — the language every provider, every partner
 * and every AI reader understands — while Polish stays the home market: the
 * demo catalogue and the currency still come from it. Russian joined them on
 * 2026-11-24 (Task #63). A new key lands in these three catalogues only.
 *
 * The other six keep the wording they were given. They still ship: their
 * URLs, their hreflang entries and the language switcher stay, and the merge
 * in `merge.ts` fills whatever they do not carry with the English wording. A
 * feature therefore costs three translations instead of nine, and the six
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
