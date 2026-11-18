/**
 * The accessibility of the routes.
 *
 * The unit suites run axe over the shared primitives; nothing proved the
 * assembled route. This walks the routes in a browser and runs axe-core over
 * what is actually rendered - the chrome, the forms, the ledgers and the
 * empty states - at the WCAG 2.2 A/AA level.
 *
 * The rules the scan applies are the WCAG 2.2 A and AA ones (`wcag2a`,
 * `wcag2aa`, `wcag21a`, `wcag21aa`, `wcag22aa`). The rules about the
 * keyboard that no scanner can check - the focus order, the focus that is
 * visible, the way the dialog takes and gives the focus back - are the
 * manual half of the accessibility work, and they live in ACCESSIBILITY.md.
 *
 * The API is mocked, so the scan is the same in CI and on a workstation:
 * the page renders its shell and its empty states, which is what a scanner
 * can read.
 */

import AxeBuilder from '@axe-core/playwright';
import { test, expect, type Page } from '@playwright/test';

import { mockLandingApis } from '../mocks';

/** The routes the scan walks: the public ones and one account route. */
const ROUTES = [
  { name: 'landing', url: '/en', mock: mockLandingApis },
  { name: 'search', url: '/en/search?q=apartment+in+Krakow' },
  { name: 'chat', url: '/en/chat' },
  { name: 'tools', url: '/en/tools' },
  { name: 'analytics', url: '/en/analytics' },
  { name: 'market-trends', url: '/en/market-trends' },
  { name: 'city-overview', url: '/en/city-overview' },
  { name: 'valuation', url: '/en/valuation' },
  { name: 'cma', url: '/en/cma' },
  { name: 'knowledge', url: '/en/knowledge' },
  { name: 'showcase', url: '/en/showcase' },
  { name: 'agents', url: '/en/agents' },
  { name: 'favorites', url: '/en/favorites' },
  { name: 'saved-searches', url: '/en/saved-searches' },
  { name: 'documents', url: '/en/documents' },
  { name: 'usage', url: '/en/usage' },
  { name: 'settings', url: '/en/settings' },
  { name: 'auth-login', url: '/en/auth/login' },
  { name: 'auth-register', url: '/en/auth/register' },
];

/** The WCAG levels the product holds itself to. */
const TAGS = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'];

/** The two themes the product ships. The studio's own materials are dark, so
 *  the dark theme is not the optional half of the pair. */
const THEMES = ['light', 'dark'];

/**
 * The API answers empty for the calls the routes make, so a page renders its
 * shell and its empty state instead of an error. The landing has its own
 * mocks - the catalogue and the capabilities are what it is about.
 */
async function mockEmptyApi(page: Page): Promise<void> {
  await page.route('**/api/v1/**', async (route) => {
    const request = route.request();
    if (request.method() === 'OPTIONS') {
      await route.fulfill({ status: 204, headers: { 'Access-Control-Allow-Origin': '*' } });
      return;
    }
    const url = request.url();
    const body = url.includes('/auth/me')
      ? { id: 'a11y-user', email: 'a11y@example.com', role: 'user', is_active: true }
      : url.includes('/catalogue/stats')
        ? { total: 250, agents: 15, cities: [], currencies: ['PLN'] }
        : url.includes('/capabilities')
          ? {
              auth: { jwt_enabled: true, demo_user_bypass: false, oauth: { google: false } },
              email: { enabled: false, provider: 'dummy' },
              llm: { demo_mode: true, mode: 'local-model', provider: 'minimax', model: 'demo' },
              lead_capture: { waitlist_enabled: false },
            }
          : url.includes('/search')
            ? { results: [], total: 0 }
            : [];
    await route.fulfill({
      status: 200,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
  });
}

test.describe('The accessibility of the routes', () => {
  for (const route of ROUTES) {
    for (const theme of THEMES) {
      test(`${route.name} has no WCAG 2.2 A/AA violation in ${theme}`, async ({ page }) => {
        // The theme is set the way the application sets it: the `theme` key in
        // localStorage, read by the application's own script before it paints.
        await page.addInitScript((wanted) => {
          try {
            localStorage.setItem('theme', wanted);
            localStorage.setItem('onboarding-tour-dismissed-v1', '1');
          } catch {}
        }, theme);

        // The mock is registered before the route's own mocks, so the route's
        // own answer is the one that lands.
        await mockEmptyApi(page);
        if (route.mock) await route.mock(page);

        await page.goto(route.url, { waitUntil: 'domcontentloaded' });
        // The page paints, the API answers, and the reader's tour is not in
        // the way of the scan.
        await page.waitForTimeout(1500);

        const results = await new AxeBuilder({ page })
          .withTags(TAGS)
          .analyze();

        const violations = results.violations.map((violation) => ({
          id: violation.id,
          impact: violation.impact,
          help: violation.help,
          nodes: violation.nodes.map((node) => node.target.join(' ')),
        }));

        expect(
          violations,
          `${route.name} (${theme}): ${violations
            .map((v) => `${v.id} (${v.impact}) - ${v.help} [${v.nodes.join(', ')}]`)
            .join(' | ')}`
        ).toEqual([]);
      });
    }
  }
});
