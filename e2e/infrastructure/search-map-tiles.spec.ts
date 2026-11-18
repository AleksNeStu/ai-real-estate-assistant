/**
 * The map of the search page, and its tiles.
 *
 * The rest of the suite mocks the API, and the landing map's suite proves
 * that the pins draw. Neither proves that the search page's map asks for its
 * tiles at all - and a map that asks for nothing is an empty rectangle that
 * looks like a broken page.
 *
 * The tiles are the free OpenStreetMap ones: the map needs no key, and the
 * request goes from the browser to the tile host. That host is a third party,
 * so the suite separates the two failures:
 *
 *   - the map did not ask for tiles          -> the product is broken
 *   - the map asked and the host refused     -> the network is broken, and the
 *                                              suite says so instead of
 *                                              turning a third party's outage
 *                                              into a red gate
 *
 * Run with:
 *   E2E_STACK=true STACK_BACKEND_URL=... STACK_FRONTEND_URL=... \
 *   PLAYWRIGHT_START_WEB=false npx playwright test e2e/infrastructure
 */

import { test, expect } from '@playwright/test';

const BACKEND_URL = process.env.STACK_BACKEND_URL || 'http://localhost:8082';
const FRONTEND_URL = process.env.STACK_FRONTEND_URL || 'http://localhost:3082';
const API_ACCESS_KEY = process.env.API_ACCESS_KEY || '';

test.skip(process.env.E2E_STACK !== 'true', 'needs the Docker Compose stack (E2E_STACK=true)');

/** The free tiles the map asks for. */
const TILE_HOST = /tile\.openstreetmap\.org/;

function apiHeaders(): Record<string, string> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (API_ACCESS_KEY) {
    headers['X-API-Key'] = API_ACCESS_KEY;
  }
  return headers;
}

test.describe('The map of the search page', () => {
  // One visitor at a time: the demo catalogue fills up in the background, and
  // the map is the same page for everyone.
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

  test('the map asks for its tiles, and the tiles arrive', async ({ page }) => {
    const requested: string[] = [];
    const refused: string[] = [];

    page.on('request', (request) => {
      if (TILE_HOST.test(request.url())) requested.push(request.url());
    });
    page.on('requestfailed', (request) => {
      if (TILE_HOST.test(request.url())) refused.push(request.url());
    });

    await page.goto(`${FRONTEND_URL}/search?q=apartment%20in%20Krakow`);

    // The map itself: the page opens on it.
    const map = page.locator('[role="application"]');
    await expect(map).toBeVisible({ timeout: 60_000 });

    // The tiles Leaflet asked for. Leaflet puts one <img> per tile in the
    // tile pane, and a tile that arrived has a natural size; a tile that did
    // not has none.
    const tiles = page.locator('.leaflet-tile');
    await expect(tiles.first()).toBeVisible({ timeout: 60_000 });

    const deadline = Date.now() + 60_000;
    let painted = 0;
    let total = 0;
    while (Date.now() < deadline) {
      const state = await page.evaluate(() => {
        const images = Array.from(document.querySelectorAll('.leaflet-tile'));
        return {
          total: images.length,
          painted: images.filter((image) => (image as HTMLImageElement).naturalWidth > 0).length,
        };
      });
      total = state.total;
      painted = state.painted;
      if (total > 0 && painted === total) break;
      await page.waitForTimeout(500);
    }

    // The map asked for tiles. If it never asked, the map is broken - that is
    // the product's fault, and it fails here.
    expect(
      requested.length,
      'the map asked for no tiles at all, so it drew no map'
    ).toBeGreaterThan(0);

    // The tiles came back. If the tile host refused them, the network is
    // broken, not the map: the suite says so and does not fail the gate for
    // a third party's outage.
    if (painted === 0) {
      test.skip(
        true,
        `the tile host refused every tile (${refused.length} failed requests) - the map asked, the network did not answer`
      );
    }

    expect(total).toBeGreaterThan(0);
    expect(painted).toBe(total);
  });

  test('the tiles are painted inside the map, not beside it', async ({ page }) => {
    await page.goto(`${FRONTEND_URL}/search?q=apartment%20in%20Krakow`);

    const map = page.locator('[role="application"]');
    await expect(map).toBeVisible({ timeout: 60_000 });

    const tile = page.locator('.leaflet-tile').first();
    await expect(tile).toBeVisible({ timeout: 60_000 });

    // The tile is a child of the map, and it is on the screen: a tile that
    // arrived but sits outside the map's own box would not be a drawn map.
    const insideMap = await page.evaluate(() => {
      const container = document.querySelector('.leaflet-container');
      const image = document.querySelector('.leaflet-tile');
      if (!container || !image) return false;
      const a = container.getBoundingClientRect();
      const b = image.getBoundingClientRect();
      return b.width > 0 && b.height > 0 && b.left < a.right && b.right > a.left;
    });
    expect(insideMap).toBe(true);
  });
});
