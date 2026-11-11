/**
 * The map popup E2E tests.
 *
 * A marker on the map is a listing, and a listing has a page of its own. The
 * popup is where a reader sees that a marker is a listing at all, so the
 * popup is where the link to the page belongs.
 *
 * The map is the Leaflet one - the Mapbox variant is behind a token that the
 * deployment does not carry.
 */

import { test, expect } from '@playwright/test';

import { mockSearchSuccess } from '../mocks';

test.describe('The map popup', () => {
  test('opens the property page of the listing it names', async ({ page }) => {
    await page.route('**/api/v1/search*', mockSearchSuccess);

    await page.goto('/en/search?q=Berlin');

    // The map is loaded on demand, so it takes a moment to be on the screen.
    const map = page.locator('[role="application"][aria-label="Property map"]');
    await expect(map).toBeVisible({ timeout: 15000 });

    const markers = page.locator('.leaflet-marker-icon');
    await expect.poll(async () => await markers.count(), { timeout: 15000 }).toBeGreaterThan(0);

    // A marker opens its popup; the popup names the listing and links to it.
    await markers.first().click();

    const link = page.locator('.leaflet-popup-content a[href*="/property/"]');
    await expect(link).toBeVisible({ timeout: 15000 });

    const href = await link.getAttribute('href');
    expect(href).toMatch(/\/en\/property\/prop-\d+/);
  });
});
