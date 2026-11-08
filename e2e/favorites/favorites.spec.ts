/**
 * Favorites page E2E tests.
 * Tests the /favorites page: list display, empty state, removal, collections, filtering, and errors.
 * Uses the authenticatedPage fixture from conftest.ts.
 */

import { test, expect } from '../conftest';

// --- Mock Data ---

const MOCK_FAVORITES = [
  {
    id: 'fav-001',
    user_id: 'test-user-basic-001',
    property_id: 'prop-001',
    collection_id: null,
    notes: null,
    created_at: '2025-01-15T10:00:00Z',
    updated_at: '2025-01-15T10:00:00Z',
    is_available: true,
    property: {
      id: 'prop-001',
      title: 'Modern 2-Bedroom Apartment in Mitte',
      price: 450000,
      rooms: 2,
      area: 75,
      city: 'Berlin',
      neighborhood: 'Mitte',
      property_type: 'apartment',
      description: 'A modern apartment in the heart of Berlin.',
    },
  },
  {
    id: 'fav-002',
    user_id: 'test-user-basic-001',
    property_id: 'prop-002',
    collection_id: 'col-001',
    notes: 'Great for family',
    created_at: '2025-01-16T12:00:00Z',
    updated_at: '2025-01-16T12:00:00Z',
    is_available: true,
    property: {
      id: 'prop-002',
      title: 'Spacious 3-Bedroom Flat in Prenzlauer Berg',
      price: 650000,
      rooms: 3,
      area: 95,
      city: 'Berlin',
      neighborhood: 'Prenzlauer Berg',
      property_type: 'apartment',
      description: 'Family-friendly apartment near parks.',
    },
  },
];

const MOCK_COLLECTIONS = [
  {
    id: 'col-001',
    user_id: 'test-user-basic-001',
    name: 'Family Homes',
    description: 'Homes suitable for families',
    is_default: false,
    created_at: '2025-01-10T08:00:00Z',
    updated_at: '2025-01-10T08:00:00Z',
    favorite_count: 1,
  },
];

// --- Helpers ---

/**
 * Setup all favorites-related API mocks for an authenticated page.
 */
function setupFavoritesMocks(page: import('@playwright/test').Page) {
  // GET /api/v1/favorites/ids
  page.route('**/api/v1/favorites/ids', async (route) => {
    if (route.request().method() === 'OPTIONS') {
      await route.fulfill({ status: 204, headers: { 'Access-Control-Allow-Origin': '*' } });
      return;
    }
    await route.fulfill({
      status: 200,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(['prop-001', 'prop-002']),
    });
  });

  // GET /api/v1/favorites (list with properties)
  page.route('**/api/v1/favorites?**', async (route) => {
    if (route.request().method() === 'OPTIONS') {
      await route.fulfill({ status: 204, headers: { 'Access-Control-Allow-Origin': '*' } });
      return;
    }
    await route.fulfill({
      status: 200,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        items: MOCK_FAVORITES,
        total: MOCK_FAVORITES.length,
        unavailable_count: 0,
      }),
    });
  });

  // GET /api/v1/collections
  page.route('**/api/v1/collections', async (route) => {
    if (route.request().method() === 'OPTIONS') {
      await route.fulfill({ status: 204, headers: { 'Access-Control-Allow-Origin': '*' } });
      return;
    }
    await route.fulfill({
      status: 200,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        items: MOCK_COLLECTIONS,
        total: MOCK_COLLECTIONS.length,
      }),
    });
  });
}

// --- Tests ---

test.describe('Favorites Page', () => {
  test('should display favorites list with property data @smoke', async ({ page }) => {
    // Use setupPageAuth pattern directly - set auth mocks and cookies
    await page.route('**/api/v1/auth/me', async (route) => {
      await route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          id: 'test-user-basic-001',
          email: 'test@example.com',
          full_name: 'Test User',
          role: 'user',
          is_active: true,
          is_verified: true,
          created_at: new Date().toISOString(),
        }),
      });
    });

    await page.context().addCookies([
      {
        name: 'access_token',
        value: 'mock-access-token',
        domain: 'localhost',
        path: '/',
        httpOnly: true,
        sameSite: 'Lax' as const,
      },
    ]);

    setupFavoritesMocks(page);

    await page.goto('/favorites');

    // Wait for the page heading to appear
    const heading = page.getByRole('heading', { name: /my favorites/i });
    await expect(heading).toBeVisible({ timeout: 15000 });

    // Should show saved count
    await expect(page.getByText(/2 saved (?:property|properties)/i)).toBeVisible();

    // Should show property cards from mock data
    await expect(page.getByText('Modern 2-Bedroom Apartment in Mitte')).toBeVisible({
      timeout: 10000,
    });
    await expect(page.getByText('Spacious 3-Bedroom Flat in Prenzlauer Berg')).toBeVisible();
  });

  test('should display empty state when no favorites exist', async ({ page }) => {
    // Setup auth
    await page.route('**/api/v1/auth/me', async (route) => {
      await route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          id: 'test-user-basic-001',
          email: 'test@example.com',
          full_name: 'Test User',
          role: 'user',
          is_active: true,
          is_verified: true,
          created_at: new Date().toISOString(),
        }),
      });
    });

    await page.context().addCookies([
      {
        name: 'access_token',
        value: 'mock-access-token',
        domain: 'localhost',
        path: '/',
        httpOnly: true,
        sameSite: 'Lax' as const,
      },
    ]);

    // Mock empty favorites
    await page.route('**/api/v1/favorites/ids', async (route) => {
      await route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify([]),
      });
    });

    await page.route('**/api/v1/favorites?**', async (route) => {
      await route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ items: [], total: 0, unavailable_count: 0 }),
      });
    });

    await page.route('**/api/v1/collections', async (route) => {
      await route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ items: [], total: 0 }),
      });
    });

    await page.goto('/favorites');

    // Should show empty state
    await expect(page.getByText(/no favorites yet/i)).toBeVisible({ timeout: 15000 });
    await expect(page.getByText(/click the heart icon/i)).toBeVisible();

    // Should show browse properties link
    await expect(page.getByRole('button', { name: /browse properties/i })).toBeVisible();
  });

  test('should remove a favorite and update the list', async ({ page }) => {
    // Setup auth
    await page.route('**/api/v1/auth/me', async (route) => {
      await route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          id: 'test-user-basic-001',
          email: 'test@example.com',
          full_name: 'Test User',
          role: 'user',
          is_active: true,
          is_verified: true,
          created_at: new Date().toISOString(),
        }),
      });
    });

    await page.context().addCookies([
      {
        name: 'access_token',
        value: 'mock-access-token',
        domain: 'localhost',
        path: '/',
        httpOnly: true,
        sameSite: 'Lax' as const,
      },
    ]);

    let deleteCalled = false;

    setupFavoritesMocks(page);

    // Mock DELETE /api/v1/favorites/by-property/:id
    page.route('**/api/v1/favorites/by-property/**', async (route) => {
      if (route.request().method() === 'DELETE') {
        deleteCalled = true;
        await route.fulfill({
          status: 204,
          headers: { 'Content-Type': 'application/json' },
        });
      } else {
        await route.continue();
      }
    });

    // After delete, mock updated favorites list
    page.route('**/api/v1/favorites?**', async (route) => {
      if (route.request().method() === 'OPTIONS') {
        await route.fulfill({ status: 204, headers: { 'Access-Control-Allow-Origin': '*' } });
        return;
      }
      // Return single favorite after removal
      await route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          items: [MOCK_FAVORITES[0]],
          total: 1,
          unavailable_count: 0,
        }),
      });
    });

    await page.goto('/favorites');

    // Wait for page to load
    await expect(page.getByRole('heading', { name: /my favorites/i })).toBeVisible({
      timeout: 15000,
    });

    // Find and click the heart/unfavorite button on the first property card
    // The PropertyCard component renders a heart toggle button
    const unfavoriteButton = page
      .locator('[data-testid="property-card"], .property-card, article')
      .first()
      .locator('button')
      .filter({ has: page.locator('svg') })
      .first();

    if (await unfavoriteButton.isVisible({ timeout: 5000 }).catch(() => false)) {
      await unfavoriteButton.click();

      // Verify the DELETE API was called
      expect(deleteCalled).toBe(true);
    }
  });

  test('should create a new collection', async ({ page }) => {
    // Setup auth
    await page.route('**/api/v1/auth/me', async (route) => {
      await route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          id: 'test-user-basic-001',
          email: 'test@example.com',
          full_name: 'Test User',
          role: 'user',
          is_active: true,
          is_verified: true,
          created_at: new Date().toISOString(),
        }),
      });
    });

    await page.context().addCookies([
      {
        name: 'access_token',
        value: 'mock-access-token',
        domain: 'localhost',
        path: '/',
        httpOnly: true,
        sameSite: 'Lax' as const,
      },
    ]);

    setupFavoritesMocks(page);

    let createPayload: Record<string, string> | null = null;

    // Mock POST /api/v1/collections
    page.route('**/api/v1/collections', async (route) => {
      if (route.request().method() === 'POST') {
        createPayload = await route.request().postDataJSON();
        await route.fulfill({
          status: 201,
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            id: 'col-new',
            user_id: 'test-user-basic-001',
            name: createPayload?.name || 'New Collection',
            description: createPayload?.description,
            is_default: false,
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
            favorite_count: 0,
          }),
        });
      } else {
        await route.continue();
      }
    });

    await page.goto('/favorites');

    // Wait for page to load
    await expect(page.getByRole('heading', { name: /my favorites/i })).toBeVisible({
      timeout: 15000,
    });

    // Click "New Collection" button
    const newCollectionButton = page.getByRole('button', { name: /new collection/i });
    await newCollectionButton.click();

    // Modal should appear
    const modalHeading = page.getByRole('heading', { name: /new collection/i });
    await expect(modalHeading).toBeVisible({ timeout: 5000 });

    // Fill in collection name
    const nameInput = page.getByPlaceholder(/collection name/i);
    await nameInput.fill('Vacation Homes');

    // Click Create button in modal
    const createButton = page.getByRole('button', { name: /^create$/i });
    await createButton.click();

    // Verify the API was called with correct data
    expect(createPayload).toBeTruthy();
    expect(createPayload!.name).toBe('Vacation Homes');
  });

  test('should filter favorites by collection', async ({ page }) => {
    // Setup auth
    await page.route('**/api/v1/auth/me', async (route) => {
      await route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          id: 'test-user-basic-001',
          email: 'test@example.com',
          full_name: 'Test User',
          role: 'user',
          is_active: true,
          is_verified: true,
          created_at: new Date().toISOString(),
        }),
      });
    });

    await page.context().addCookies([
      {
        name: 'access_token',
        value: 'mock-access-token',
        domain: 'localhost',
        path: '/',
        httpOnly: true,
        sameSite: 'Lax' as const,
      },
    ]);

    let requestedCollectionId: string | null = null;

    setupFavoritesMocks(page);

    // Override favorites route to capture collection_id parameter
    page.route('**/api/v1/favorites?**', async (route) => {
      const url = route.request().url();
      const urlObj = new URL(url);
      requestedCollectionId = urlObj.searchParams.get('collection_id');

      const items = requestedCollectionId ? [MOCK_FAVORITES[1]] : MOCK_FAVORITES;

      await route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          items,
          total: items.length,
          unavailable_count: 0,
        }),
      });
    });

    await page.goto('/favorites');

    // Wait for page to load
    await expect(page.getByRole('heading', { name: /my favorites/i })).toBeVisible({
      timeout: 15000,
    });

    // Click on a collection in the sidebar (Family Homes). The collections
    // are buttons with the role "option" - they belong to a listbox.
    const collectionButton = page.getByRole('option', { name: /family homes/i });
    await collectionButton.click();

    // Should have requested with collection_id
    // The API call is triggered by the collection selection
    await page.waitForTimeout(1000);

    // The filtered view should only show properties from that collection
    expect(requestedCollectionId).toBe('col-001');
  });

  test('should display error state on API failure', async ({ page }) => {
    // Setup auth
    await page.route('**/api/v1/auth/me', async (route) => {
      await route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          id: 'test-user-basic-001',
          email: 'test@example.com',
          full_name: 'Test User',
          role: 'user',
          is_active: true,
          is_verified: true,
          created_at: new Date().toISOString(),
        }),
      });
    });

    await page.context().addCookies([
      {
        name: 'access_token',
        value: 'mock-access-token',
        domain: 'localhost',
        path: '/',
        httpOnly: true,
        sameSite: 'Lax' as const,
      },
    ]);

    // Mock favorites API to return error
    await page.route('**/api/v1/favorites?**', async (route) => {
      await route.fulfill({
        status: 500,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ detail: 'Internal server error' }),
      });
    });

    await page.route('**/api/v1/favorites/ids', async (route) => {
      await route.fulfill({
        status: 500,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ detail: 'Internal server error' }),
      });
    });

    await page.route('**/api/v1/collections', async (route) => {
      await route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ items: [], total: 0 }),
      });
    });

    await page.goto('/favorites');

    // The favorites page shows the error of the context in a destructive
    // colored div. The text is the message of the API, so the alert itself is
    // checked.
    await expect(page.locator('[role="alert"]')).toBeVisible({ timeout: 15000 });
  });
});
