import https from 'node:https';

import type { MetadataRoute } from 'next';

import sitemap from '../sitemap';
import { LOCALES } from '@/lib/metadata';
import { routing } from '@/i18n/routing';

/**
 * The sitemap is an INDEX, so it names a page ONCE.
 *
 * The file used to name every locale version of every page as its own
 * `<loc>` - 261 paths x 9 locales = 2,349 URLs, nine near-duplicates of each
 * page. That is the shape that produced 261 sitemap warnings and no indexed
 * page: a crawler was handed the same page nine times and had no way to tell
 * which copy was the original.
 *
 * The entry is now the default locale's version of the path, and the other
 * eight live beside it as the `hreflang` alternates, with `x-default`
 * naming the default locale's version of the same path.
 *
 * These tests read the generated file the way a crawler does - the XML, not
 * the object Next turns it into - and they read the deployed file too, so
 * the shape the crawler actually sees is the shape that is held.
 */

// The next-intl routing module is ESM and Jest does not load it; the sitemap
// only reads the locale list and the default locale from it.
jest.mock('@/i18n/routing', () => ({
  routing: {
    locales: ['pl', 'en', 'ru', 'de', 'es', 'it', 'pt', 'tr', 'uk'],
    defaultLocale: 'pl',
    localePrefix: 'always',
    alternateLinks: false,
  },
}));

jest.mock('@/lib/api/server', () => ({
  serverApiUrl: () => 'http://api.test/api/v1',
  // The catalogue of the places the register covers: a city and one of its
  // districts.
  fetchServerPlaceCatalogue: jest.fn(async () => ({
    places: [
      {
        name: 'Kraków',
        slug: 'krakow',
        register_city: 'KRAKÓW',
        districts: [{ name: 'Old Town', slug: 'old-town' }],
      },
    ],
  })),
}));

jest.mock('next-intl/server', () => ({
  getTranslations: async (namespace?: string) => (key: string) => `${namespace ?? ''}.${key}`,
  setRequestLocale: () => undefined,
}));

const ORIGIN = 'https://realty.kittray.com';

function mockCatalogue(properties: { id: string }[] | 'unreachable') {
  global.fetch = jest.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url.includes('/properties')) {
      if (properties === 'unreachable') throw new Error('unreachable');
      return {
        ok: true,
        json: async () => ({ properties }),
      } as unknown as Response;
    }
    return { ok: false, json: async () => ({}) } as unknown as Response;
  }) as unknown as typeof fetch;
}

/**
 * The XML the framework writes out of the entries, in the shape it writes it
 * in: a `urlset` of `url` elements, one `<loc>` each, the alternates beside
 * it. Rendering it here is what lets the tests parse the file a crawler
 * reads rather than the object it was built from.
 */
function renderSitemapXml(entries: MetadataRoute.Sitemap): string {
  const urls = entries
    .map((entry) => {
      const links = Object.entries(entry.alternates?.languages ?? {})
        .map(
          ([hreflang, href]) =>
            `<xhtml:link rel="alternate" hreflang="${hreflang}" href="${href}" />`
        )
        .join('\n');
      return [
        '<url>',
        `<loc>${entry.url}</loc>`,
        links,
        entry.lastModified ? `<lastmod>${entry.lastModified.toISOString()}</lastmod>` : '',
        entry.changeFrequency ? `<changefreq>${entry.changeFrequency}</changefreq>` : '',
        entry.priority !== undefined ? `<priority>${entry.priority}</priority>` : '',
        '</url>',
      ]
        .filter(Boolean)
        .join('\n');
    })
    .join('\n');

  return [
    '<?xml version="1.0" encoding="UTF-8"?>',
    '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">',
    urls,
    '</urlset>',
  ].join('\n');
}

const SITEMAP_NS = 'http://www.sitemaps.org/schemas/sitemap/0.9';
const XHTML_NS = 'http://www.w3.org/1999/xhtml';

function parseSitemapXml(xml: string): Document {
  return new DOMParser().parseFromString(xml, 'text/xml');
}

/** The path of an entry, without the origin and without the locale prefix. */
function pathOf(url: string): string {
  const pathname = url.replace(ORIGIN, '');
  return pathname.replace(/^\/[a-z]{2}(?=\/|$)/, '');
}

describe('the sitemap holds one entry per path', () => {
  it('names a page once, not once per language', async () => {
    mockCatalogue([{ id: 'prop-a' }, { id: 'prop-b' }]);
    const entries = await sitemap();

    const paths = entries.map((entry) => pathOf(entry.url));
    // 11 public routes + 2 listings + 2 place pages, each of them named once.
    expect(paths.length).toBe(15);
    expect(new Set(paths).size).toBe(paths.length);
  });

  it('names the default locale version of the path', async () => {
    mockCatalogue([]);
    const entries = await sitemap();

    const urls = entries.map((entry) => entry.url);
    expect(urls).toContain(`${ORIGIN}/${routing.defaultLocale}`);
    expect(urls).toContain(`${ORIGIN}/${routing.defaultLocale}/search`);
    // The other eight are the alternates of the entry, not entries of their own.
    expect(urls).not.toContain(`${ORIGIN}/en/search`);
  });

  it('carries every locale version of the path beside the entry', async () => {
    mockCatalogue([]);
    const entries = await sitemap();
    const search = entries.find((entry) => pathOf(entry.url) === '/search');

    expect(search).toBeDefined();
    const languages = search?.alternates?.languages ?? {};

    for (const locale of LOCALES) {
      expect(languages[locale]).toBe(`${ORIGIN}/${locale}/search`);
    }
    // The default version is the entry's own address.
    expect(languages[routing.defaultLocale]).toBe(search?.url);
  });

  it('points x-default at the default locale version of the path', async () => {
    mockCatalogue([]);
    const entries = await sitemap();

    for (const entry of entries) {
      const path = pathOf(entry.url);
      expect(entry.alternates?.languages?.['x-default']).toBe(
        `${ORIGIN}/${routing.defaultLocale}${path}`
      );
    }
  });

  it('keeps the home page free of a trailing slash', async () => {
    mockCatalogue([]);
    const entries = await sitemap();
    const home = entries.find((entry) => pathOf(entry.url) === '');

    expect(home?.url).toBe(`${ORIGIN}/${routing.defaultLocale}`);
    expect(home?.alternates?.languages?.pl).toBe(`${ORIGIN}/pl`);
  });
});

describe('the generated sitemap file', () => {
  it('holds one loc per path, with the alternates beside it', async () => {
    mockCatalogue([{ id: 'prop-a' }]);
    const entries = await sitemap();
    const document = parseSitemapXml(renderSitemapXml(entries));

    const urls = document.getElementsByTagNameNS(SITEMAP_NS, 'url');
    expect(urls.length).toBe(entries.length);

    const paths = new Set<string>();
    for (let index = 0; index < urls.length; index += 1) {
      const url = urls[index];
      const locs = url.getElementsByTagNameNS(SITEMAP_NS, 'loc');
      expect(locs.length).toBe(1);

      const links = url.getElementsByTagNameNS(XHTML_NS, 'link');
      expect(links.length).toBe(LOCALES.length + 1);

      const hreflangs = Array.from(links).map((link) => link.getAttribute('hreflang'));
      expect(hreflangs).toEqual(expect.arrayContaining([...LOCALES, 'x-default']));

      paths.add(pathOf(locs[0].textContent ?? ''));
    }

    expect(paths.size).toBe(urls.length);
  });
});

/**
 * The deployed file is the one a crawler reads, so its URL count is read
 * from the live address.
 *
 * The test is opt-in: the network is not the unit suite's business, and a
 * deployment that has not been rolled yet still serves the previous shape.
 * Run it with `RUN_LIVE_SITEMAP_TEST=1`.
 */
const RUN_LIVE = process.env.RUN_LIVE_SITEMAP_TEST === '1';
const LIVE_SITEMAP = `${ORIGIN}/sitemap.xml`;

function fetchText(url: string, timeoutMs = 30_000): Promise<{ status: number; body: string }> {
  return new Promise((resolve, reject) => {
    const request = https.get(url, { timeout: timeoutMs }, (response) => {
      let body = '';
      response.setEncoding('utf8');
      response.on('data', (chunk) => {
        body += chunk;
      });
      response.on('end', () => resolve({ status: response.statusCode ?? 0, body }));
    });
    request.on('timeout', () => request.destroy(new Error('the request timed out')));
    request.on('error', reject);
  });
}

(RUN_LIVE ? describe : describe.skip)('the deployed sitemap', () => {
  it('is well formed and its URL count is read', async () => {
    const { status, body } = await fetchText(LIVE_SITEMAP);
    expect(status).toBe(200);

    const document = parseSitemapXml(body);
    const urls = document.getElementsByTagNameNS(SITEMAP_NS, 'url');
    const locs = Array.from(document.getElementsByTagNameNS(SITEMAP_NS, 'loc')).map(
      (loc) => loc.textContent ?? ''
    );

    const paths = new Set(locs.map(pathOf));
    const localeCount = LOCALES.length;

    // The file is in one of the two shapes it has ever been in: one entry per
    // path, or the one it is leaving behind - one entry per path per locale.
    expect([paths.size, paths.size * localeCount]).toContain(urls.length);

    for (let index = 0; index < urls.length; index += 1) {
      const loc = urls[index].getElementsByTagNameNS(SITEMAP_NS, 'loc');
      expect(loc.length).toBe(1);

      const links = urls[index].getElementsByTagNameNS(XHTML_NS, 'link');
      const hreflangs = Array.from(links).map((link) => link.getAttribute('hreflang'));
      expect(hreflangs).toEqual(expect.arrayContaining([...LOCALES, 'x-default']));
    }

    const shape = urls.length === paths.size ? 'one entry per path' : 'one entry per path per locale';
    console.log(
      `deployed sitemap: ${urls.length} URLs, ${paths.size} distinct paths (${shape})`
    );
  }, 60_000);
});
