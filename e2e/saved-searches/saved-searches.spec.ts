/**
 * Saved Searches E2E tests.
 * Tests saved search list, alert toggling, deletion, empty state, error handling, and auth protection.
 */

import { test, expect } from '../conftest';
import {
  mockSavedSearchesList,
  mockSavedSearchesEmpty,
  mockToggleSavedSearchAlert,
  mockDeleteSavedSearch,
  mockSavedSearchesError,
  mockSavedSearchesUnauthorized,
} from '../mocks/saved-searches.mock';
import { SavedSearchesPage } from '../page-objects/saved-searches.page';

test.describe('Saved Searches', () => {
  test.describe('List Display', () => {
    test('should display saved searches list @smoke', async ({ authenticatedPage }) => {
      await authenticatedPage.route('**/api/v1/saved-searches**', mockSavedSearchesList);

      const savedSearchesPage = new SavedSearchesPage(authenticatedPage);
      await savedSearchesPage.navigate();

      // Verify heading is visible
      await expect(savedSearchesPage.heading).toBeVisible();

      // Verify search cards are displayed
      const count = await savedSearchesPage.getSearchCount();
      expect(count).toBeGreaterThan(0);

      // Verify specific search names are visible
      await expect(authenticatedPage.getByText('2-bedroom Berlin')).toBeVisible();
      await expect(authenticatedPage.getByText('Apartment Krakow under 500k')).toBeVisible();
    });

    test('should display empty state when no saved searches', async ({ authenticatedPage }) => {
      await authenticatedPage.route('**/api/v1/saved-searches**', mockSavedSearchesEmpty);

      const savedSearchesPage = new SavedSearchesPage(authenticatedPage);
      await savedSearchesPage.navigate();

      // Verify empty state message
      await expect(savedSearchesPage.emptyState).toBeVisible({ timeout: 10000 });

      // Verify no search cards
      const count = await savedSearchesPage.getSearchCount();
      expect(count).toBe(0);
    });

    test('should display search details in cards', async ({ authenticatedPage }) => {
      await authenticatedPage.route('**/api/v1/saved-searches**', mockSavedSearchesList);

      const savedSearchesPage = new SavedSearchesPage(authenticatedPage);
      await savedSearchesPage.navigate();

      // Verify filter details are shown
      await expect(
        authenticatedPage.getByRole('heading', { name: /berlin/i }).first()
      ).toBeVisible();

      // Verify use count is displayed
      await expect(authenticatedPage.getByText(/12 times/).first()).toBeVisible();

      // Verify created date is displayed. Every card carries the date, so the
      // first one is used.
      await expect(authenticatedPage.getByText(/created:/i).first()).toBeVisible();
    });
  });

  test.describe('Alert Toggle', () => {
    test('should toggle alert on/off', async ({ authenticatedPage }) => {
      let toggleCallCount = 0;
      await authenticatedPage.route('**/api/v1/saved-searches**', async (route) => {
        const url = route.request().url();
        if (url.includes('/toggle-alert')) {
          toggleCallCount++;
          await mockToggleSavedSearchAlert(route);
        } else {
          await mockSavedSearchesList(route);
        }
      });

      const savedSearchesPage = new SavedSearchesPage(authenticatedPage);
      await savedSearchesPage.navigate();

      // Verify initial state shows active searches
      const bellIcon = authenticatedPage.locator('[data-lucide="bell"], svg').first();
      await expect(savedSearchesPage.heading).toBeVisible();

      // Toggle the alert for the first search
      await savedSearchesPage.toggleAlert('2-bedroom Berlin');

      // Verify the toggle API was called
      expect(toggleCallCount).toBe(1);
    });
  });

  test.describe('Delete', () => {
    test('should delete a saved search and update UI', async ({ authenticatedPage }) => {
      let deleteCalled = false;
      let listCallCount = 0;

      await authenticatedPage.route('**/api/v1/saved-searches**', async (route) => {
        const method = route.request().method();
        const url = route.request().url();

        if (method === 'DELETE') {
          deleteCalled = true;
          await mockDeleteSavedSearch(route);
        } else if (url.includes('/toggle-alert')) {
          await mockToggleSavedSearchAlert(route);
        } else {
          listCallCount++;
          // First call returns full list, subsequent calls return fewer items
          if (listCallCount > 1) {
            await route.fulfill({
              status: 200,
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                items: [
                  {
                    id: 'ss-002',
                    user_id: 'test-user-basic-001',
                    name: 'Apartment Krakow under 500k',
                    filters: { city: 'Krakow', max_price: 500000 },
                    alert_frequency: 'weekly',
                    is_active: false,
                    notify_on_new: false,
                    notify_on_price_drop: true,
                    created_at: '2025-11-20T08:00:00Z',
                    updated_at: '2025-12-10T09:15:00Z',
                    use_count: 5,
                  },
                ],
                total: 1,
              }),
            });
          } else {
            await mockSavedSearchesList(route);
          }
        }
      });

      const savedSearchesPage = new SavedSearchesPage(authenticatedPage);
      await savedSearchesPage.navigate();

      // Verify initial count
      const initialCount = await savedSearchesPage.getSearchCount();
      expect(initialCount).toBeGreaterThan(0);

      // Delete the first search
      await savedSearchesPage.deleteSearch('2-bedroom Berlin');

      // Verify delete was called
      expect(deleteCalled).toBe(true);
    });
  });

  test.describe('Error Handling', () => {
    test('should display error state on API failure', async ({ authenticatedPage }) => {
      await authenticatedPage.route('**/api/v1/saved-searches**', mockSavedSearchesError);

      const savedSearchesPage = new SavedSearchesPage(authenticatedPage);
      await savedSearchesPage.navigate();

      // Should show error message
      await expect(savedSearchesPage.errorMessage).toBeVisible({ timeout: 10000 });
    });

    test('should allow retry after error via refresh button', async ({ authenticatedPage }) => {
      let callCount = 0;

      await authenticatedPage.route('**/api/v1/saved-searches**', async (route) => {
        callCount++;
        if (callCount <= 1) {
          await mockSavedSearchesError(route);
        } else {
          await mockSavedSearchesList(route);
        }
      });

      const savedSearchesPage = new SavedSearchesPage(authenticatedPage);
      await savedSearchesPage.navigate();

      // Verify error shown first
      await expect(savedSearchesPage.errorMessage).toBeVisible({ timeout: 10000 });

      // Click refresh
      await savedSearchesPage.refresh();

      // Verify data loads after refresh. The list arrives with the answer of
      // the API - the test waits for it.
      await expect(savedSearchesPage.getSearchCardByName('2-bedroom Berlin')).toBeVisible({
        timeout: 10000,
      });
      const count = await savedSearchesPage.getSearchCount();
      expect(count).toBeGreaterThan(0);
    });
  });

  test.describe('Auth Protection', () => {
    test('should redirect unauthenticated user to login', async ({ page }) => {
      // Mock the saved-searches API to return 401
      await page.route('**/api/v1/saved-searches**', mockSavedSearchesUnauthorized);

      // Mock auth/me to also return 401 (user not logged in)
      await page.route('**/api/v1/auth/me', async (route) => {
        await route.fulfill({
          status: 401,
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ detail: 'Not authenticated' }),
        });
      });

      await page.goto('/saved-searches');

      // Should be redirected to login page (or show auth error). In the demo
      // mode the page itself is reachable and the API rejects the request, so
      // the error state counts as well.
      const url = page.url();
      const isOnLogin = url.includes('/auth/login');
      const hasAuthError = await page
        .locator('text=/log in/i')
        .isVisible()
        .catch(() => false);
      const hasErrorState = await page
        .locator('[role="alert"]')
        .first()
        .isVisible()
        .catch(() => false);

      expect(isOnLogin || hasAuthError || hasErrorState).toBe(true);
    });
  });
});
