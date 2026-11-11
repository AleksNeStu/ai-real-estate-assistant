import { MetadataRoute } from 'next';

import { routing } from '@/i18n/routing';
import { languageAlternates } from '@/lib/metadata';
import { serverApiUrl } from '@/lib/api/server';
import { absoluteUrl } from '@/lib/site';

/**
 * The public, indexable routes.
 *
 * The list used to carry the account areas as well - /leads, /usage,
 * /documents, /analytics, /agent-analytics - and a sitemap is a list of
 * pages to index. Those pages are behind the account gate, so listing them
 * asked a crawler to fetch pages it cannot have, and told a search engine
 * that the site is about lead dashboards.
 */
const PUBLIC_PATHS = [
  '', // homepage
  '/search',
  '/chat',
  '/market-trends',
  '/city-overview',
  '/agents',
  '/tools',
  '/knowledge',
  '/valuation',
  '/showcase',
  '/cma',
];

/**
 * The listings of this deployment.
 *
 * The listing page is the page a buyer searches for - "two-room apartment in
 * Kraków, Old Town" - and it is the one page of the site that was missing
 * from the sitemap entirely, so it could not be found by anything that reads
 * a sitemap rather than a link.
 *
 * The catalogue is read from the backend. A deployment that cannot be reached
 * answers with the routes it knows: a sitemap that lists the site's pages is
 * better than a sitemap that fails.
 */
async function fetchCatalogueIds(limit: number): Promise<string[]> {
  try {
    const response = await fetch(`${serverApiUrl()}/properties?limit=${limit}`, {
      headers: { Accept: 'application/json' },
      next: { revalidate: 3600 },
    });
    if (!response.ok) return [];
    const data = (await response.json()) as { properties?: { id?: string }[] };
    const ids = (data?.properties ?? [])
      .map((property) => property?.id)
      .filter((id): id is string => Boolean(id));
    return ids;
  } catch {
    return [];
  }
}

/**
 * The sitemap is read when it is asked for, not when the image is built.
 *
 * The catalogue of a deployment is its own: the listings of one instance are
 * not the listings of another. A sitemap generated at build time would carry
 * the catalogue of the machine that built the image.
 */
export const dynamic = 'force-dynamic';

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const entries: MetadataRoute.Sitemap = [];
  const lastModified = new Date();
  const defaultLocale = routing.defaultLocale;

  for (const path of PUBLIC_PATHS) {
    entries.push({
      url: absoluteUrl(`/${defaultLocale}${path}`),
      lastModified,
      changeFrequency: path === '' ? 'daily' : 'weekly',
      priority: path === '' ? 1.0 : path === '/search' ? 0.9 : 0.7,
      // One entry per page, with the cluster of its translations: a sitemap
      // that lists the same page nine times - once per language - asks a
      // crawler to treat nine URLs as nine pages.
      alternates: { languages: languageAlternates(path) },
    });
  }

  for (const id of await fetchCatalogueIds(500)) {
    entries.push({
      url: absoluteUrl(`/${defaultLocale}/property/${id}`),
      lastModified,
      changeFrequency: 'weekly',
      priority: 0.6,
      alternates: { languages: languageAlternates(`/property/${id}`) },
    });
  }

  return entries;
}
