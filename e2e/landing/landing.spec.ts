/**
 * The landing E2E tests.
 *
 * The landing is the open face of the project: it explains the thing and
 * gets the visitor into it. Its surfaces are new - the hero that searches,
 * the catalogue numbers that come from the API, the waitlist that notes an
 * address, and the studio strip that records the outbound click.
 *
 * Every assertion is on a stable handle - a test id, a route, a request -
 * and never on the shape of the page.
 */

import { test, expect } from '@playwright/test';
import { mockLandingApis } from '../mocks';

test.describe('The Landing', () => {
  test.beforeEach(async ({ page }) => {
    await mockLandingApis(page);
  });

  test('the hero sends the query to the search @smoke', async ({ page }) => {
    await page.goto('/en/');

    // The hero is a form: the query the visitor typed goes into the search
    // as the `q` parameter of the route.
    const query = page.locator('form input[name="q"]');
    await expect(query).toBeVisible({ timeout: 15000 });
    await query.fill('two-room flat in Kraków under 500k');
    await page.locator('form button[type="submit"]').first().click();

    await expect(page).toHaveURL(/\/en\/search\?q=/, { timeout: 15000 });
  });

  test('the catalogue numbers come from the API', async ({ page }) => {
    await page.goto('/en/');

    // The mock answers with 250 properties and 15 agents - the page states
    // what the API said, so a hard-coded number would not show up here.
    await expect(page.getByText(/250 properties · 15 agents/).first()).toBeVisible({
      timeout: 15000,
    });
    await expect(page.getByText('Kraków').first()).toBeVisible();
  });

  test('the waitlist posts a visitor', async ({ page }) => {
    const posted: string[] = [];
    // The route is registered after the shared mock, so it answers the
    // request and keeps the body for the assertion.
    await page.route('**/api/v1/leads/visitor', async (route) => {
      posted.push(route.request().postData() ?? '');
      await route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: 'lead-mock-visitor', visitor_id: 'visitor-mock' }),
      });
    });

    await page.goto('/en/');

    const field = page.locator('#waitlist-email');
    await expect(field).toBeVisible({ timeout: 15000 });
    await field.fill('visitor@example.com');
    await field.locator('xpath=..').locator('button[type="submit"]').click();

    await expect.poll(() => posted.length, { timeout: 15000 }).toBeGreaterThan(0);
    expect(posted.join(' ')).toContain('propvector_waitlist');
    expect(posted.join(' ')).toContain('visitor@example.com');
  });

  test('the studio strip records the outbound click', async ({ page }) => {
    // The outbound link leaves the site; the request it fires on the way
    // out is the measurement.
    const reported: string[] = [];
    await page.route('**/api/v1/analytics/outbound', async (route) => {
      reported.push(route.request().postData() ?? '');
      await route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tracked: true }),
      });
    });
    // The link opens the studio's own site in a new tab; the test does not
    // follow it out.
    await page.route('**propvectorai.com/**', (route) => route.abort());

    await page.goto('/en/');

    const studioLink = page.getByRole('link', { name: /PropVector AI/ }).first();
    await expect(studioLink).toBeVisible({ timeout: 15000 });
    await studioLink.click();

    await expect.poll(() => reported.length, { timeout: 15000 }).toBeGreaterThan(0);
    expect(reported.join(' ')).toContain('propvector');
  });
});
