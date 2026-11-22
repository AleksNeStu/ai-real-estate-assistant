import sitemap from '../sitemap';
import { routing } from '@/i18n/routing';

// The next-intl routing module is ESM and Jest does not load it; the sitemap
// only reads the locale list from it.
jest.mock('@/i18n/routing', () => ({
  routing: {
    locales: ['pl', 'en', 'ru', 'de', 'es', 'it', 'pt', 'tr', 'uk'],
    defaultLocale: 'pl',
    localePrefix: 'always',
    alternateLinks: false,
  },
}));

/**
 * The sitemap is the site's index for everything that reads a sitemap
 * instead of a link - a crawler, an answer engine, a directory.
 *
 * It had no test at all: a typo in the route list, or a catalogue that
 * stopped answering, would have emptied the index while the pipeline stayed
 * green. These tests hold the two things it promises: the public routes are
 * listed, and every listing of the deployment is listed with them.
 */

jest.mock('@/lib/api/server', () => ({
  serverApiUrl: () => 'http://api.test/api/v1',
}));

jest.mock('next-intl/server', () => ({
  getTranslations: async (namespace?: string) => (key: string) => `${namespace ?? ''}.${key}`,
  setRequestLocale: () => undefined,
}));

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

describe('the sitemap', () => {
  it('lists the public routes of the deployment', async () => {
    mockCatalogue([]);
    const entries = await sitemap();
    const urls = entries.map((entry) => entry.url);

    const origin = 'https://realty.kittray.com';
    const locale = routing.defaultLocale;
    expect(urls).toContain(`${origin}/${locale}`);
    expect(urls).toContain(`${origin}/${locale}/search`);
    expect(urls).toContain(`${origin}/${locale}/chat`);
    expect(urls).toContain(`${origin}/${locale}/market-trends`);
    expect(urls).toContain(`${origin}/${locale}/tools`);
  });

  it('lists every listing the catalogue holds', async () => {
    mockCatalogue([{ id: 'prop-a' }, { id: 'prop-b' }]);
    const entries = await sitemap();
    const urls = entries.map((entry) => entry.url);
    const origin = 'https://realty.kittray.com';
    const locale = routing.defaultLocale;

    expect(urls).toContain(`${origin}/${locale}/property/prop-a`);
    expect(urls).toContain(`${origin}/${locale}/property/prop-b`);
  });

  it('does not ask a crawler for the account areas', async () => {
    mockCatalogue([]);
    const entries = await sitemap();
    const urls = entries.map((entry) => entry.url).join(' ');

    for (const gated of ['/leads', '/usage', '/documents', '/analytics', '/agent-analytics']) {
      expect(urls).not.toContain(gated);
    }
  });

  it('gives every entry its translations', async () => {
    mockCatalogue([{ id: 'prop-a' }]);
    const entries = await sitemap();

    for (const entry of entries) {
      expect(entry.alternates?.languages).toBeDefined();
      expect(Object.keys(entry.alternates?.languages ?? {}).length).toBeGreaterThan(1);
      expect(entry.alternates?.languages?.['x-default']).toBeDefined();
    }
  });

  /**
   * The file used to name every locale version of every page as its own
   * `<loc>` - 2,349 URLs for 261 paths, nine near-duplicates of each page.
   * The shape now is one entry per path: the default locale's version is the
   * entry, and the other eight are its hreflang alternates.
   */
  it('names a page once, not once per language', async () => {
    mockCatalogue([]);
    const entries = await sitemap();
    const urls = entries.map((entry) => entry.url);

    expect(urls).toContain('https://realty.kittray.com/pl/search');
    expect(urls).not.toContain('https://realty.kittray.com/en/search');
    expect(new Set(urls).size).toBe(urls.length);
  });

  it('points the cluster of a page at that page in every language', async () => {
    mockCatalogue([]);
    const entries = await sitemap();
    const search = entries.find((entry) => entry.url.endsWith('/pl/search'));

    expect(search).toBeDefined();
    const languages = search?.alternates?.languages ?? {};
    // The home pages are NOT the translations of the search page.
    expect(languages.pl).toMatch(/\/pl\/search$/);
    expect(languages.en).toMatch(/\/en\/search$/);
    expect(languages['x-default']).toMatch(/\/pl\/search$/);
  });

  it('still answers with the routes when the catalogue is unreachable', async () => {
    mockCatalogue('unreachable');
    const entries = await sitemap();
    const urls = entries.map((entry) => entry.url);

    // A sitemap that fails is worse than a sitemap without the listings.
    expect(urls.length).toBeGreaterThan(0);
    expect(urls.some((url) => url.endsWith('/search'))).toBe(true);
  });
});
