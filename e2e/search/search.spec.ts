/**
 * Search flow E2E tests.
 * Tests property search, filtering, map view, and export functionality.
 */

import { test, expect } from '../conftest';
import { mockSearchSuccess, mockSearchEmpty, mockExportSuccess } from '../mocks';

test.describe('Search Flows', () => {
  test.describe('Basic Search', () => {
    test('should display search interface @smoke', async ({ authenticatedSearchPage }) => {
      await authenticatedSearchPage.navigate();

      // Verify search elements are visible
      await expect(authenticatedSearchPage.searchInput).toBeVisible();
      await expect(authenticatedSearchPage.searchButton).toBeVisible();
    });

    test('should perform search and display results', async ({ authenticatedSearchPage, page }) => {
      // Mock search API
      await page.route('**/api/v1/search*', mockSearchSuccess);

      await authenticatedSearchPage.navigate();
      await authenticatedSearchPage.search('2 bedroom apartment in Berlin');

      // Verify results are displayed
      await expect(authenticatedSearchPage.resultsContainer).toBeVisible({ timeout: 15000 });
      expect(await authenticatedSearchPage.getResultCount()).toBeGreaterThan(0);
    });

    test('should display no results message for empty search', async ({
      authenticatedSearchPage,
      page,
    }) => {
      // Mock empty search results
      await page.route('**/api/v1/search*', mockSearchEmpty);

      await authenticatedSearchPage.navigate();
      await authenticatedSearchPage.search('nonexistent property xyz123');

      // Verify no results message
      await expect(authenticatedSearchPage.noResultsMessage).toBeVisible({ timeout: 10000 });
    });

    test('should display loading state during search', async ({
      authenticatedSearchPage,
      page,
    }) => {
      // Mock delayed search response
      await page.route('**/api/v1/search*', async (route) => {
        await new Promise((resolve) => setTimeout(resolve, 2000));
        await mockSearchSuccess(route);
      });

      await authenticatedSearchPage.navigate();

      // Start search
      await authenticatedSearchPage.searchInput.fill('apartment');
      await authenticatedSearchPage.searchButton.click();

      // Verify loading indicator appears
      await expect(authenticatedSearchPage.loadingSpinner).toBeVisible({ timeout: 2000 });

      // Wait for results
      await authenticatedSearchPage.waitForResults();
    });
  });

  test.describe('Filters', () => {
    test('should apply price range filter', async ({ authenticatedSearchPage, page }) => {
      await page.route('**/api/v1/search*', mockSearchSuccess);

      await authenticatedSearchPage.navigate();

      // Open filters panel if collapsed
      const filtersToggle = page.getByRole('button', { name: /filters|filter/i });
      if (await filtersToggle.isVisible()) {
        await filtersToggle.click();
      }

      // Set price range
      await authenticatedSearchPage.setPriceRange(500, 1500);

      // Apply filters
      await authenticatedSearchPage.applyFilters();

      // Verify search was triggered with filters
      await expect(authenticatedSearchPage.resultsContainer).toBeVisible({ timeout: 15000 });
    });

    test('should filter by minimum rooms', async ({ authenticatedSearchPage, page }) => {
      await page.route('**/api/v1/search*', mockSearchSuccess);

      await authenticatedSearchPage.navigate();

      // Open filters panel if collapsed
      const filtersToggle = page.getByRole('button', { name: /filters|filter/i });
      if (await filtersToggle.isVisible()) {
        await filtersToggle.click();
      }

      // Set minimum rooms
      await authenticatedSearchPage.setMinRooms(2);
      await authenticatedSearchPage.applyFilters();

      await expect(authenticatedSearchPage.resultsContainer).toBeVisible({ timeout: 15000 });
    });
  });

  test.describe('View Toggle', () => {
    test('should toggle between list and map view', async ({ authenticatedSearchPage, page }) => {
      await page.route('**/api/v1/search*', mockSearchSuccess);

      await authenticatedSearchPage.navigate();
      await authenticatedSearchPage.search('Berlin');

      // Check initial view (should be list by default)
      await expect(authenticatedSearchPage.listContainer).toBeVisible();

      // Switch to map view
      await authenticatedSearchPage.switchToMapView();
      await expect(authenticatedSearchPage.mapContainer).toBeVisible({ timeout: 5000 });

      // Switch back to list view
      await authenticatedSearchPage.switchToListView();
      await expect(authenticatedSearchPage.listContainer).toBeVisible({ timeout: 5000 });
    });

    test('should display property markers on map', async ({ authenticatedSearchPage, page }) => {
      await page.route('**/api/v1/search*', mockSearchSuccess);

      await authenticatedSearchPage.navigate();
      await authenticatedSearchPage.search('Berlin');
      await authenticatedSearchPage.switchToMapView();

      // The map is loaded on demand (dynamic import), so it takes a moment
      // until it is on the screen.
      const map = page.locator('[role="application"][aria-label="Property map"]');
      await expect(map).toBeVisible({ timeout: 15000 });

      // The map is drawn by Leaflet - every marker is an icon of the map.
      const markers = page.locator('.leaflet-marker-icon');
      await expect.poll(async () => await markers.count(), { timeout: 15000 }).toBeGreaterThan(0);
    });
  });

  test.describe('Export', () => {
    test('should export results to CSV', async ({ authenticatedSearchPage, page }) => {
      await page.route('**/api/v1/search*', mockSearchSuccess);
      await page.route('**/api/v1/export/properties', mockExportSuccess);

      await authenticatedSearchPage.navigate();
      await authenticatedSearchPage.search('Berlin');

      // Start export download
      const downloadPromise = page.waitForEvent('download');

      await authenticatedSearchPage.exportResults('csv');

      const download = await downloadPromise;
      expect(download.suggestedFilename()).toContain('.csv');
    });
  });

  test.describe('Property Details', () => {
    test('should display the property details in the result card', async ({
      authenticatedSearchPage,
      page,
    }) => {
      await page.route('**/api/v1/search*', mockSearchSuccess);

      await authenticatedSearchPage.navigate();
      await authenticatedSearchPage.search('Berlin');

      // The result card carries the details of the property. There is no
      // separate page for a single property in the product - the card is the
      // place where the details are shown.
      const propertyCards = await authenticatedSearchPage.getPropertyCards();
      expect(propertyCards.length).toBeGreaterThan(0);

      const firstCard = propertyCards[0];
      await expect(firstCard).toContainText(/Berlin/i);
      await expect(firstCard).toContainText(/\d/);
    });
  });

  test.describe('Error Handling', () => {
    test('should display error message on API failure', async ({
      authenticatedSearchPage,
      page,
    }) => {
      // Mock search API error
      await page.route('**/api/v1/search*', async (route) => {
        await route.fulfill({
          status: 500,
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ detail: 'Search failed' }),
        });
      });

      await authenticatedSearchPage.navigate();
      await authenticatedSearchPage.search('test');

      // Should show error message
      const errorMessage = authenticatedSearchPage.errorMessage;
      await expect(errorMessage).toBeVisible({ timeout: 10000 });
    });

    test('should show retry button on error', async ({ authenticatedSearchPage, page }) => {
      let failCount = 0;

      // Mock search API with retry behavior
      await page.route('**/api/v1/search*', async (route) => {
        failCount++;
        if (failCount <= 1) {
          await route.fulfill({
            status: 500,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ detail: 'Search failed' }),
          });
        } else {
          await mockSearchSuccess(route);
        }
      });

      await authenticatedSearchPage.navigate();
      await authenticatedSearchPage.search('test');

      // Should show retry button
      const retryButton = page.getByRole('button', { name: /retry|try again/i });
      await expect(retryButton).toBeVisible({ timeout: 10000 });

      // Click retry
      await retryButton.click();

      // Should show results after retry
      await expect(authenticatedSearchPage.resultsContainer).toBeVisible({ timeout: 15000 });
    });
  });
});
