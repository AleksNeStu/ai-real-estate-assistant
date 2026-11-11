import en from '../../../messages/en.json';

/**
 * The copy of the public routes.
 *
 * Every public route declares its own title and description, and it takes
 * them from the message catalogue - so that a page speaks the language of its
 * own route instead of the language of the site. The route declarations name
 * a key in the catalogue; this test is what says the key is there.
 *
 * It exists because a route once asked for a key that no catalogue carries
 * (`pages.home`): the catalogue's fallback answers with the key itself, so
 * nothing crashed - the landing page simply published its title as the text
 * "home.title".
 */

interface RouteCopy {
  title: string;
  description: string;
}

/** The routes that declare their own metadata, and the key they read. */
const ROUTES: { path: string; namespace: string; key: string }[] = [
  { path: '/search', namespace: 'pages', key: 'search' },
  { path: '/chat', namespace: 'chat', key: '' },
  { path: '/market-trends', namespace: 'pages', key: 'marketTrends' },
  { path: '/city-overview', namespace: 'pages', key: 'cityOverview' },
  { path: '/agents', namespace: 'pages', key: 'agents' },
  { path: '/tools', namespace: 'pages', key: 'tools' },
  { path: '/knowledge', namespace: 'pages', key: 'knowledge' },
  { path: '/valuation', namespace: 'pages', key: 'valuation' },
  { path: '/cma', namespace: 'pages', key: 'cma' },
  { path: '/analytics', namespace: 'pages', key: 'analytics' },
];

const catalogue = en as unknown as Record<string, Record<string, RouteCopy>>;

describe('the copy of the public routes', () => {
  it.each(ROUTES)('$path has a title and a description', ({ namespace, key }) => {
    const copy = key ? catalogue[namespace]?.[key] : catalogue[namespace];

    expect(copy).toBeDefined();
    expect(typeof copy?.title).toBe('string');
    expect(copy?.title.length).toBeGreaterThan(0);
    expect(typeof copy?.description).toBe('string');
    expect(copy?.description.length).toBeGreaterThan(0);
  });

  it('gives every route its own title', () => {
    const titles = ROUTES.map(({ namespace, key }) =>
      (key ? catalogue[namespace]?.[key] : catalogue[namespace])?.title,
    );

    expect(new Set(titles).size).toBe(titles.length);
  });
});
