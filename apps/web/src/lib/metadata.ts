/**
 * Metadata helpers shared by the locale layout and the individual pages.
 *
 * WHY THE CANONICAL IS NOT IN THE LAYOUT
 *
 * A layout does not know which route it is rendering, so a canonical declared
 * in `apps/web/src/app/[locale]/layout.tsx` is inherited by every page below
 * it. The layout used to declare `/${locale}` — the home page's URL — which
 * told a search engine that all thirty routes were duplicates of the home
 * page. That is a single-page-app canonical applied to a multi-page site, and
 * it makes the pages compete with each other instead of being indexed on their
 * own terms.
 *
 * Most of the routes are client components (`'use client'`), and a client
 * component cannot export `generateMetadata`. A route segment that needs an
 * explicit canonical therefore needs a server-component layout, or the page
 * itself must be a server component. The helpers here make that a one-liner
 * either way.
 *
 * Removing the canonical from the layout is not a regression: with no
 * canonical declared, a page is treated as self-canonical, which is correct.
 * An explicit canonical is only needed where a page could plausibly compete
 * with another URL for the same content.
 */

import type { Metadata } from 'next';

import { absoluteUrl } from '@/lib/site';

/** Every locale the app ships, in the order the routing config lists them. */
export const LOCALES = ['pl', 'en', 'ru', 'de', 'es', 'it', 'pt', 'tr', 'uk'] as const;

/**
 * The hreflang map for the whole site: one entry per locale plus the
 * `x-default` pointer. Shared by the layout and by any page that declares its
 * own canonical — a page-level `alternates` replaces the inherited one, so it
 * has to carry the languages too or the hreflang cluster disappears for that
 * page.
 */
export function languageAlternates(): Record<string, string> {
  const languages: Record<string, string> = {};
  for (const locale of LOCALES) {
    languages[locale] = absoluteUrl(`/${locale}`);
  }
  languages['x-default'] = absoluteUrl('/pl');
  return languages;
}

/**
 * Per-page metadata with a correct canonical and the full hreflang map.
 *
 * @param locale - the current locale (BCP-47 two-letter tag)
 * @param path   - the route path WITHOUT the locale prefix, e.g. `/showcase`.
 *                  Use `/` for the home page.
 */
export function pageMetadata(locale: string, path: string): Metadata {
  const suffix = path === '/' ? '' : path.startsWith('/') ? path : `/${path}`;
  return {
    alternates: {
      canonical: absoluteUrl(`/${locale}${suffix}`),
      languages: languageAlternates(),
    },
  };
}
