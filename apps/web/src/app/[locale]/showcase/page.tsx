import { getTranslations } from 'next-intl/server';
import type { Metadata } from 'next';

import { pageMetadata } from '@/lib/metadata';
import { ShowcaseBody } from './showcase-body';

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations('showcase');
  return {
    title: `${t('heroTitle')} · ${t('forksTitle')}`,
    description: t('heroSubtitle'),
    // Absolute canonical + the full hreflang map. The layout no longer
    // declares a canonical (see the note in @/lib/metadata), and a page-level
    // `alternates` replaces the inherited one, so the languages have to be
    // repeated here.
    ...pageMetadata(locale, '/showcase'),
  };
}

/**
 * /<locale>/showcase — public-facing social-proof page.
 *
 * Three sections render an explicit empty state ("no forks or quotes yet —
 * be the first") so the route is reachable from external sources (Show HN
 * thread replies, Product Hunt, Reddit posts) without showing fake data.
 * The entry format of every section is one toggle away: the page says what
 * an entry looks like instead of only saying that there is none.
 *
 * Intended future content:
 *  - Forks: pull from GitHub API (`repos/AleksNeStu/ai-real-estate-assistant/forks`)
 *    once the repo has > 0 forks and operator authorizes the public listing.
 *    Filter out low-quality forks (no commits, archived, etc.).
 *  - Companies: opt-in testimonials from operators who deployed this stack
 *    in production. Requires explicit permission per Rule 281 (no internal
 *    infra disclosure).
 *  - Quotes: GitHub issue / PR comments from users, or tweet quotes (with
 *    permission) — never fabricated.
 */
export default async function ShowcasePage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;

  return <ShowcaseBody locale={locale} />;
}
