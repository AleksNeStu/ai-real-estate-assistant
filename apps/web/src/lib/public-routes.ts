/**
 * The routes of the product, classified.
 *
 * The proxy decides what a visitor without an account may see. The decision
 * is a list, and a list that lives inside the proxy cannot be read by a test
 * without running the whole middleware. Here it is a module, so the test can
 * read the same names the proxy reads.
 *
 * A route belongs to exactly one of the three classes:
 *
 * - **public** — the demo answers it. A visitor with no account reaches it.
 * - **account** — the route is the account of the visitor. It renders, and the
 *   `AccountGate` layout explains what the account gives, offering the two
 *   ways in. It is NOT redirected to the sign-in: the redirect threw away the
 *   context, so a visitor who opened `/favorites` was told to sign in without
 *   ever hearing what a favourite is. The API behind it answers 401 without a
 *   token.
 * - **auth** — the route is the sign-in itself.
 *
 * A route that belongs to none of them is a visitor without an account who is
 * sent to the sign-in page by mistake. The test that reads the routes of the
 * tree fails when that happens: a new page that nobody classified is a
 * public page that asks for a login.
 */

export const PUBLIC_ROUTES = [
  '/',
  '/search',
  '/property',
  '/city-overview',
  '/knowledge',
  '/analytics',
  '/market-trends',
  '/cma',
  '/tools',
  '/chat',
  '/agents',
  '/valuation',
  '/showcase',
  '/privacy',
  '/terms',
] as const;

export const ACCOUNT_ROUTES = [
  '/favorites',
  '/saved-searches',
  '/documents',
  '/settings',
  '/leads',
  '/agent-analytics',
  '/usage',
  '/admin',
] as const;

export const AUTH_ROUTES = ['/auth'] as const;

/** What a route is for a visitor without an account. */
export type RouteClass = 'public' | 'account' | 'auth' | 'unknown';

/**
 * Whether the path is one of the routes, or a page under it.
 *
 * The proxy matches on the path without the locale, and it matches a
 * segment: `/property/42` is the property route, and `/favorites/anything`
 * is the favourites route.
 */
function isUnder(path: string, route: string): boolean {
  if (route === '/') return path === '/';
  return path === route || path.startsWith(`${route}/`);
}

/**
 * The class of the path, for a visitor without an account.
 *
 * `unknown` is the answer that matters: it means the proxy sends the visitor
 * to the sign-in page, so a route that nobody classified is a route that
 * needs an account it should not need.
 *
 * A path that ends in a slash is the path without it - `/search/` is the
 * search, and a visitor who typed the slash is not a visitor who must sign
 * in. A path with two slashes in it is the path with one.
 */
export function classifyRoute(path: string): RouteClass {
  const collapsed = path.replace(/\/{2,}/g, '/');
  const normalized = collapsed.length > 1 ? collapsed.replace(/\/+$/, '') : collapsed;
  if (PUBLIC_ROUTES.some((route) => isUnder(normalized, route))) return 'public';
  if (ACCOUNT_ROUTES.some((route) => isUnder(normalized, route))) return 'account';
  if (AUTH_ROUTES.some((route) => isUnder(normalized, route))) return 'auth';
  return 'unknown';
}
