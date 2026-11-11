/**
 * The Property page E2E tests.
 *
 * A listing on its own page: the price, the numbers of the listing, the
 * neighbourhood in words and the comparables. The page is public - a visitor
 * who clicks a listing is nobody until they sign in - so the tests answer the
 * catalogue and read the page as an anonymous reader.
 */

import { test, expect } from '@playwright/test';

const PROPERTY_ROUTE = '/en/property/listing-1';

const LISTING = {
  id: 'listing-1',
  title: 'Bright two-room apartment',
  description: 'A sunny apartment close to the park.',
  city: 'Kraków',
  country: 'Poland',
  district: 'Stare Miasto',
  neighborhood: 'Kazimierz',
  address: 'Brzozowa 12',
  latitude: 50.0614,
  longitude: 19.9374,
  property_type: 'apartment',
  listing_type: 'rent',
  rooms: 2,
  bathrooms: 1,
  area_sqm: 54,
  floor: 3,
  total_floors: 6,
  year_built: 2015,
  energy_rating: 'B',
  price: 2800,
  currency: 'PLN',
  price_per_sqm: 51.85,
  has_parking: false,
  has_garden: false,
  has_pool: false,
  has_garage: false,
  has_bike_room: true,
  has_elevator: true,
  images: [],
  source_url: 'https://example.test/listing/listing-1',
  source_platform: 'demo-portal',
};

async function mockCatalogue(page: import('@playwright/test').Page) {
  await page.route('**/api/v1/properties/listing-1', async (route) => {
    await route.fulfill({
      status: 200,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(LISTING),
    });
  });

  await page.route('**/api/v1/properties/listing-1/related*', async (route) => {
    await route.fulfill({
      status: 200,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        properties: [
          {
            ...LISTING,
            id: 'listing-2',
            title: 'Similar flat nearby',
            price: 2900,
          },
        ],
        count: 1,
      }),
    });
  });

  await page.route('**/api/v1/tools/neighborhood-summary', async (route) => {
    await route.fulfill({
      status: 200,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ summary: 'Kazimierz is a walkable riverside quarter.', language: 'en' }),
    });
  });
}

test.describe('The Property page', () => {
  test.beforeEach(async ({ page }) => {
    await mockCatalogue(page);
  });

  test('shows the listing', async ({ page }) => {
    await page.goto(PROPERTY_ROUTE);

    await expect(page.getByRole('heading', { name: 'Bright two-room apartment' })).toBeVisible();
    // The address is in the header and, again, on the comparable card below.
    await expect(page.getByText(/Brzozowa 12/).first()).toBeVisible();
  });

  test('shows the price and the numbers of the listing', async ({ page }) => {
    await page.goto(PROPERTY_ROUTE);

    await expect(page.getByText(/2,800/)).toBeVisible();
    await expect(page.getByText(/54 m²/).first()).toBeVisible();
  });

  test('shows the neighbourhood one-liner', async ({ page }) => {
    await page.goto(PROPERTY_ROUTE);

    await expect(page.getByText(/Kazimierz is a walkable riverside quarter/)).toBeVisible();
  });

  test('shows the comparable listings', async ({ page }) => {
    await page.goto(PROPERTY_ROUTE);

    await expect(page.getByText('Similar flat nearby')).toBeVisible();
  });

  test('a listing the catalogue does not hold says so', async ({ page }) => {
    await page.route('**/api/v1/properties/missing', async (route) => {
      await route.fulfill({
        status: 404,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ detail: 'Property not found' }),
      });
    });

    await page.goto('/en/property/missing');

    // The Next route announcer also carries role="alert", so the refusal is
    // named rather than taken by whichever alert comes first.
    await expect(page.getByRole('alert').filter({ hasText: 'This listing is no longer' })).toBeVisible();
  });
});
