/**
 * The anonymous journey of the product, as a test.
 *
 * The demo answers a visitor with no account. The proxy decides that, and
 * the decision is a list of routes - a list that used to live inside the
 * proxy, where a test could not read it without running the whole
 * middleware. So a new page could be added, nobody would classify it, and
 * the public demo would send that visitor to the sign-in page without
 * anybody noticing.
 *
 * These tests read the routes of the tree and read the classification, and
 * they hold the two against each other. Every route the product has belongs
 * to one of the three classes: public, account, or the sign-in itself. A
 * route that belongs to none of them is a visitor without an account who is
 * bounced to the sign-in page by mistake.
 */

import fs from 'fs';
import os from 'os';
import path from 'path';

import { ACCOUNT_ROUTES, AUTH_ROUTES, PUBLIC_ROUTES, classifyRoute } from '../public-routes';

const LOCALE_DIR = path.join(__dirname, '..', '..', 'app', '[locale]');
const PROXY_FILE = path.join(__dirname, '..', '..', 'proxy.ts');

/** Whether the directory holds a page - in any of the extensions Next serves. */
function hasPage(dir: string): boolean {
  return ['page.tsx', 'page.ts', 'page.jsx', 'page.js', 'page.mdx'].some((name) =>
    fs.existsSync(path.join(dir, name)),
  );
}

/**
 * Every page route of the tree, as the proxy sees it: the first segment.
 *
 * The walk knows the three kinds of directory that are not a route of their
 * own: a private folder (`_name`), a parallel-route slot (`@slot`) and a
 * group (`(name)`) - the group does not appear in the path, so the pages
 * inside it are the pages of the path around it.
 */
function routeKeysOfTheTree(root: string = LOCALE_DIR): string[] {
  const routes: string[] = [];

  if (hasPage(root)) {
    routes.push('/');
  }

  const walk = (dir: string, prefix: string): void => {
    for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
      if (!entry.isDirectory()) continue;
      // `__tests__` is not a route, a private folder is not a route, and a
      // parallel-route slot is not a route either.
      if (entry.name.startsWith('__') || entry.name.startsWith('_')) continue;
      if (entry.name.startsWith('@')) continue;
      const child = path.join(dir, entry.name);
      // A group in parentheses does not appear in the path: `(marketing)/
      // about/page.tsx` is `/about`. The pages inside a group are still pages,
      // so the walk goes into it - it just adds no segment of its own, so the
      // pages of a group at the root are `/about` and not `//about`.
      const isGroup = entry.name.startsWith('(');
      const route = isGroup ? prefix : `${prefix}/${entry.name}`;
      if (hasPage(child)) {
        routes.push(route || '/');
      }
      walk(child, route);
    }
  };

  walk(root, '');

  // The proxy matches on the first segment: `/admin/monitoring` is the admin
  // route, `/property/42` is the property route.
  const keys = new Set(
    routes.map((route) => {
      if (route === '/') return '/';
      const segments = route.split('/').filter(Boolean);
      return segments.length ? `/${segments[0]}` : '/';
    }),
  );
  return [...keys].sort();
}

/**
 * The routes whose first segment is a dynamic one.
 *
 * The proxy matches literal paths, so a route under a dynamic first segment
 * (`/[slug]`, and `(group)/[slug]` as well) cannot be classified by name - a
 * visitor who opens it is sent to the sign-in page whatever the list says.
 * Such a route is reported on its own, so the failure says what it is.
 */
function dynamicFirstSegmentsOfTheTree(root: string = LOCALE_DIR): string[] {
  if (!fs.existsSync(root)) return [];
  const dynamic: string[] = [];

  const walk = (dir: string, prefix: string): void => {
    for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
      if (!entry.isDirectory()) continue;
      if (entry.name.startsWith('__') || entry.name.startsWith('_')) continue;
      if (entry.name.startsWith('@')) continue;
      const isGroup = entry.name.startsWith('(');
      // A dynamic segment is the first segment of the path only when nothing
      // real stands before it - a group adds nothing to the path.
      if (!isGroup && entry.name.startsWith('[') && prefix === '') {
        dynamic.push(`/${entry.name}`);
      }
      walk(path.join(dir, entry.name), isGroup ? prefix : `${prefix}/${entry.name}`);
    }
  };

  walk(root, '');
  return dynamic;
}

describe('the routes of the product', () => {
  it('has a tree to read', () => {
    expect(fs.existsSync(LOCALE_DIR)).toBe(true);
    // The tree of the product: the pages the visitor reaches are in it.
    const routes = routeKeysOfTheTree();
    for (const route of ['/', '/search', '/property', '/favorites', '/auth']) {
      expect(routes).toContain(route);
    }
  });

  it('classifies every route the product has', () => {
    const unclassified = routeKeysOfTheTree().filter((route) => classifyRoute(route) === 'unknown');
    expect(unclassified).toEqual([]);
  });

  it('reads the pages of a group as the routes they are', () => {
    // The tree of the product has no group today, so the walk is proved on a
    // tree that has one: a group at the root adds no segment of its own, so
    // `(marketing)/about/page.tsx` is `/about` and not `//about` - a key that
    // would collapse into the root and pass as public. A private folder and a
    // parallel-route slot are not routes of their own, so the walk reads
    // neither of them as a route.
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'public-routes-'));
    const page = (relative: string): void => {
      const dir = path.join(root, relative);
      fs.mkdirSync(dir, { recursive: true });
      fs.writeFileSync(path.join(dir, 'page.tsx'), 'export default function Page() {}\n');
    };
    try {
      page('(marketing)/about');
      page('(marketing)');
      page('plain');
      page('_private');
      page('@slot');
      expect(routeKeysOfTheTree(root)).toEqual(['/', '/about', '/plain']);
    } finally {
      fs.rmSync(root, { recursive: true, force: true });
    }
  });

  it('has no route under a dynamic first segment', () => {
    // The proxy matches literal paths. A route under a dynamic first segment
    // cannot be classified by name, so a visitor who opens it is sent to the
    // sign-in page whatever the list says.
    expect(dynamicFirstSegmentsOfTheTree()).toEqual([]);
  });

  it('sees a dynamic first segment inside a group', () => {
    // A group adds nothing to the path, so `(group)/[slug]` is a route whose
    // first segment is dynamic - and the report of it must say so.
    const root = fs.mkdtempSync(path.join(os.tmpdir(), 'public-routes-'));
    const dir = path.join(root, '(group)', '[slug]');
    fs.mkdirSync(dir, { recursive: true });
    fs.writeFileSync(path.join(dir, 'page.tsx'), 'export default function Page() {}\n');
    try {
      expect(dynamicFirstSegmentsOfTheTree(root)).toEqual(['/[slug]']);
    } finally {
      fs.rmSync(root, { recursive: true, force: true });
    }
  });

  it('is the module the proxy asks', () => {
    // The classification is only worth anything while the proxy reads it. A
    // second list inside the proxy would answer for the visitor and not for
    // the test, and the two would drift.
    const proxy = fs.readFileSync(PROXY_FILE, 'utf-8');
    expect(proxy).toMatch(/from\s+['"]@\/lib\/public-routes['"]/);
    expect(proxy).toMatch(/\bclassifyRoute\s*\(/);
  });

  it('sends the public journey to a visitor without an account', () => {
    const journey = [
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
    ];
    for (const route of journey) {
      expect(classifyRoute(route)).toBe('public');
    }
  });

  it('sends the pages under a public route to the same place', () => {
    expect(classifyRoute('/property/42')).toBe('public');
    expect(classifyRoute('/city-overview/krakow')).toBe('public');
    expect(classifyRoute('/settings/buyer-memory')).toBe('account');
    expect(classifyRoute('/admin/data-sources')).toBe('account');
  });

  it('reads a path that ends in a slash as the path without it', () => {
    // A visitor who typed the slash is not a visitor who must sign in.
    expect(classifyRoute('/search/')).toBe('public');
    expect(classifyRoute('/privacy/')).toBe('public');
    expect(classifyRoute('/favorites/')).toBe('account');
    expect(classifyRoute('/')).toBe('public');
  });

  it('keeps the account of the visitor behind the account', () => {
    for (const route of ACCOUNT_ROUTES) {
      expect(classifyRoute(route)).toBe('account');
    }
  });

  it('keeps the sign-in on the sign-in', () => {
    for (const route of AUTH_ROUTES) {
      expect(classifyRoute(route)).toBe('auth');
    }
    expect(classifyRoute('/auth/login')).toBe('auth');
    expect(classifyRoute('/auth/oauth/google')).toBe('auth');
  });

  it('does not let a route be two things at once', () => {
    const all = [...PUBLIC_ROUTES, ...ACCOUNT_ROUTES, ...AUTH_ROUTES];
    expect(new Set(all).size).toBe(all.length);
  });

  it('is the list the proxy served before the list moved out of it', () => {
    // The lists here are the lists the proxy held, unchanged - plus the two
    // legal pages the footer links to, which the old proxy answered with a
    // redirect to the sign-in. A route dropped from a list changes who may
    // see it, so the lists are held to what they are.
    expect([...PUBLIC_ROUTES]).toEqual([
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
    ]);
    expect([...ACCOUNT_ROUTES]).toEqual([
      '/favorites',
      '/saved-searches',
      '/documents',
      '/settings',
      '/leads',
      '/agent-analytics',
      '/usage',
      '/admin',
    ]);
    expect([...AUTH_ROUTES]).toEqual(['/auth']);
  });
});
