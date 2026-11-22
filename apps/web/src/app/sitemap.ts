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
 * When the route list itself last changed.
 *
 * A `lastmod` is a claim about the CONTENT of a URL: "this page changed on
 * that day". The sitemap used to stamp every entry with the moment it was
 * READ - `new Date()` on every request - which claims that every page on the
 * site changed a fraction of a second ago, every second. A crawler that
 * believes that re-crawls the whole site constantly and learns nothing.
 *
 * The static routes change when the route list changes, so their date is
 * written down here and bumped with the list. The listings carry their own
 * date - the moment their data was scraped - because that is when their
 * content really changed.
 */
const ROUTES_LASTMOD = new Date('2026-11-20T00:00:00.000Z');

type CatalogueEntry = {
  id: string;
  lastmod: Date;
};

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
async function fetchCatalogue(limit: number): Promise<CatalogueEntry[]> {
  try {
    const response = await fetch(`${serverApiUrl()}/properties?limit=${limit}`, {
      headers: { Accept: 'application/json' },
      next: { revalidate: 3600 },
    });
    if (!response.ok) return [];
    const data = (await response.json()) as {
      properties?: { id?: string; scraped_at?: string }[];
    };
    return (data?.properties ?? [])
      .map((property) => {
        const id = property?.id;
        if (!id) return null;
        const scraped = property?.scraped_at ? new Date(property.scraped_at) : null;
        return {
          id,
          lastmod: scraped && !Number.isNaN(scraped.getTime()) ? scraped : ROUTES_LASTMOD,
        };
      })
      .filter((entry): entry is CatalogueEntry => entry !== null);
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
  const defaultLocale = routing.defaultLocale;

  /**
   * ONE ENTRY PER PATH.
   *
   * The file used to name every locale version of every page as its own
   * `<loc>` - 261 paths x 9 locales = 2,349 URLs, nine near-duplicates of
   * each page. That is the shape that produced 261 sitemap warnings and no
   * indexed page: a crawler was handed the same page nine times and had no
   * way to tell which copy was the original.
   *
   * A sitemap is an INDEX, so it names a page once and describes the rest of
   * its cluster beside it. The `hreflang` alternates carry every locale
   * version of that same path, and `x-default` names the default locale's
   * version of it, so a crawler still reaches all nine languages and can
   * tell that the nine are one page rather than nine.
   */
  const addPage = (path: string, lastModified: Date) => {
    const alternates = languageAlternates(path);
    const changeFrequency = path === '' ? 'daily' : 'weekly';
    const priority = path === '' ? 1.0 : path === '/search' ? 0.9 : 0.7;

    entries.push({
      url: absoluteUrl(`/${defaultLocale}${path}`),
      lastModified,
      changeFrequency,
      priority,
      alternates: { languages: alternates },
    });
  };

  for (const path of PUBLIC_PATHS) {
    addPage(path, ROUTES_LASTMOD);
  }

  for (const entry of await fetchCatalogue(500)) {
    addPage(`/property/${entry.id}`, entry.lastmod);
  }

  return entries;
}
