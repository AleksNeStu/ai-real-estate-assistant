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
import { getTranslations } from 'next-intl/server';

import { absoluteUrl } from '@/lib/site';

/** Every locale the app ships, in the order the routing config lists them. */
export const LOCALES = ['pl', 'en', 'ru', 'de', 'es', 'it', 'pt', 'tr', 'uk'] as const;

/**
 * The hreflang map for the whole site: one entry per locale plus the
 * `x-default` pointer. Shared by the layout and by any page that declares its
 * own canonical — a page-level `alternates` replaces the inherited one, so it
 * has to carry the languages too or the hreflang cluster disappears for that
 * page.
 *
 * @param path - the route path WITHOUT the locale prefix. A cluster must
 *               point at the SAME page in every language: the search page
 *               in Polish is /pl/search, not the Polish home page. Without
 *               the path every page claimed the home pages as its
 *               translations.
 */
export function languageAlternates(path: string = ''): Record<string, string> {
  const suffix = path === '/' ? '' : path.startsWith('/') ? path : `/${path}`;
  const languages: Record<string, string> = {};
  for (const locale of LOCALES) {
    languages[locale] = absoluteUrl(`/${locale}${suffix}`);
  }
  languages['x-default'] = absoluteUrl(`/pl${suffix}`);
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

/**
 * The per-page metadata of a public route.
 *
 * WHY THE PAGES NEEDED IT
 *
 * Every public route inherited the layout's title and description, so
 * fourteen of them answered with the same two strings: "AI Real Estate
 * Assistant" and "Next-gen real estate search and analytics". A search engine
 * sees fourteen pages that claim to be about the same thing, and it has no way
 * to tell that /market-trends is about price history and /agents is about
 * brokers. The copy was already there - the message catalogue carries a
 * `pages` namespace with a title and a description per route, in nine
 * languages - it was simply never wired into the metadata.
 *
 * The title and the description come from that catalogue, so a page speaks
 * the language of its own route rather than a translated afterthought.
 *
 * @param locale    - the current locale
 * @param path      - the route path WITHOUT the locale prefix, e.g. `/search`
 * @param pageKey   - the key in the catalogue namespace
 * @param namespace - the catalogue namespace the key lives in (`pages` by
 *                    default; the chat route keeps its own)
 */
export async function routeMetadata(
  locale: string,
  path: string,
  pageKey: string,
  namespace: string = 'pages',
): Promise<Metadata> {
  const t = await getTranslations({ locale, namespace });
  // An empty page key means the namespace carries the copy itself - the chat
  // route reads `chat.title`, not `chat.chat.title`.
  const title = pageKey ? t(`${pageKey}.title` as never) : t('title' as never);
  const description = pageKey
    ? t(`${pageKey}.description` as never)
    : t('description' as never);
  const url = absoluteUrl(`/${locale}${path === '/' ? '' : path}`);

  return {
    title,
    description,
    alternates: {
      canonical: url,
      languages: languageAlternates(),
    },
    openGraph: {
      title,
      description,
      url,
      type: 'website',
    },
    twitter: {
      card: 'summary_large_image',
      title,
      description,
    },
  };
}
