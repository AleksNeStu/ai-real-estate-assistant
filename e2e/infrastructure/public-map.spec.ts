/**
 * The map of the public demo, for an anonymous visitor.
 *
 * The rest of the suite mocks the API, so nothing proves that the map of the
 * public version actually draws anything. This suite talks to the running
 * stack: it waits for the demo catalogue to fill up, searches as an
 * anonymous visitor would, and asserts that the map draws the listings as
 * pins that state their price and open the listing.
 *
 * The map needs no paid provider: the default path is Leaflet over the free
 * OpenStreetMap tiles. The enhanced path (Mapbox) needs a token, so the
 * switch is only offered where the token exists - a switch that opens a map
 * the provider refuses to serve would show a grey rectangle.
 *
 * Run with:
 *   E2E_STACK=true STACK_BACKEND_URL=... STACK_FRONTEND_URL=... \
 *   PLAYWRIGHT_START_WEB=false npx playwright test e2e/infrastructure
 */

import { test, expect } from '@playwright/test';

// The ports the compose file publishes. The names are STACK_* on purpose: a
// project's own .env already carries a FRONTEND_URL for the local
// development stack, and npm loads that file into the test process, so a
// generic name silently points the probe at the wrong host.
const BACKEND_URL = process.env.STACK_BACKEND_URL || 'http://localhost:8082';
const FRONTEND_URL = process.env.STACK_FRONTEND_URL || 'http://localhost:3082';
const API_ACCESS_KEY = process.env.API_ACCESS_KEY || '';

test.skip(process.env.E2E_STACK !== 'true', 'needs the Docker Compose stack (E2E_STACK=true)');

function apiHeaders(): Record<string, string> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (API_ACCESS_KEY) {
    headers['X-API-Key'] = API_ACCESS_KEY;
  }
  return headers;
}

test.describe('The map of the public demo', () => {
  // One visitor at a time: the demo catalogue fills up in the background,
  // and the map is the same page for everyone.
  test.describe.configure({ mode: 'serial' });

  // The catalogue is seeded when the backend starts, and the seeding embeds
  // every listing - a minute or two of work on a CI runner.
  test.setTimeout(300_000);

  test('the demo catalogue fills up, so the map has listings to draw', async ({ request }) => {
    const deadline = Date.now() + 240_000;

    while (Date.now() < deadline) {
      const response = await request.post(`${BACKEND_URL}/api/v1/search`, {
        headers: apiHeaders(),
        data: { query: 'apartment in Krakow' },
        timeout: 60_000,
      });

      if (response.ok()) {
        const body = (await response.json()) as { results?: unknown[] };
        if ((body.results ?? []).length > 0) {
          return;
        }
      }

      await new Promise((resolve) => setTimeout(resolve, 5000));
    }

    throw new Error('the demo catalogue never filled up');
  });

  test('an anonymous visitor sees the listings as pins that state their price', async ({ page }) => {
    const errors: string[] = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') errors.push(msg.text());
    });

    await page.goto(`${FRONTEND_URL}/search?q=apartment%20in%20Krakow`);

    // The map itself: the page opens on it, and the tiles are the free ones.
    const map = page.locator('[role="application"]');
    await expect(map).toBeVisible({ timeout: 60_000 });

    // The pins: Leaflet draws a marker per listing.
    const pins = page.locator('.leaflet-marker-icon');
    await expect(pins.first()).toBeVisible({ timeout: 60_000 });

    // The pin states the price - that is what makes the map worth reading.
    await expect(pins.first()).toContainText(/\d/);

    // The popup opens on the pin and links to the listing. The map carries a
    // floating card over its top-left corner, so a pin that happens to sit
    // under it cannot be clicked - the test opens the first pin that is
    // reachable, the way a visitor would.
    const count = await pins.count();
    let opened = false;
    for (let index = 0; index < count; index += 1) {
      const pin = pins.nth(index);
      if (!(await pin.isVisible())) continue;
      try {
        await pin.click({ timeout: 3000 });
        opened = true;
        break;
      } catch {
        // This one sits under the floating card; try the next.
      }
    }
    expect(opened, 'no pin on the map could be clicked').toBe(true);

    const popup = page.locator('.leaflet-popup-content');
    await expect(popup).toBeVisible();
    await expect(popup).toContainText(/\d/);
    await expect(popup.locator('a')).toHaveAttribute('href', /\/property\//);

    // The map logs nothing of its own. A tile that the runner's network
    // refused is not the map's fault; a Mapbox style request without a
    // token is.
    const mapErrors = errors.filter((text) => /mapbox|leaflet/i.test(text));
    expect(mapErrors).toEqual([]);
  });

  test('the map is offered without the enhanced switch when there is no token', async ({ page }) => {
    await page.goto(`${FRONTEND_URL}/search?q=apartment%20in%20Krakow`);

    const map = page.locator('[role="application"]');
    await expect(map).toBeVisible({ timeout: 60_000 });

    // The stack carries no Mapbox token, so the switch that opens a map the
    // provider refuses to serve is not offered at all.
    await expect(page.getByLabel(/mapbox/i)).toHaveCount(0);
  });
});
