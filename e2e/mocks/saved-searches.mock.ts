/**
 * Saved searches API mock handlers for E2E tests.
 * Provides mock responses for saved-searches CRUD operations.
 */

import { Route } from '@playwright/test';
import { TEST_SAVED_SEARCHES } from '../fixtures/saved-searches';

/**
 * Mock GET /api/v1/saved-searches returning a list.
 */
export async function mockSavedSearchesList(route: Route): Promise<void> {
  await route.fulfill({
    status: 200,
    headers: {
      'Content-Type': 'application/json',
      'Access-Control-Allow-Origin': '*',
    },
    body: JSON.stringify({
      items: TEST_SAVED_SEARCHES,
      total: TEST_SAVED_SEARCHES.length,
    }),
  });
}

/**
 * Mock GET /api/v1/saved-searches returning an empty list.
 */
export async function mockSavedSearchesEmpty(route: Route): Promise<void> {
  await route.fulfill({
    status: 200,
    headers: {
      'Content-Type': 'application/json',
      'Access-Control-Allow-Origin': '*',
    },
    body: JSON.stringify({
      items: [],
      total: 0,
    }),
  });
}

/**
 * Mock POST /api/v1/saved-searches/:id/toggle-alert.
 * Returns the saved search with toggled is_active state.
 */
export async function mockToggleSavedSearchAlert(route: Route): Promise<void> {
  const url = route.request().url();
  const match = url.match(/\/saved-searches\/([^/]+)\/toggle-alert/);
  const id = match ? match[1] : 'ss-001';
  const search = TEST_SAVED_SEARCHES.find((s) => s.id === id) || TEST_SAVED_SEARCHES[0];

  // Parse enabled parameter from URL
  const enabledMatch = url.match(/enabled=(true|false)/);
  const enabled = enabledMatch ? enabledMatch[1] === 'true' : !search.is_active;

  await route.fulfill({
    status: 200,
    headers: {
      'Content-Type': 'application/json',
      'Access-Control-Allow-Origin': '*',
    },
    body: JSON.stringify({
      ...search,
      is_active: enabled,
    }),
  });
}

/**
 * Mock DELETE /api/v1/saved-searches/:id.
 */
export async function mockDeleteSavedSearch(route: Route): Promise<void> {
  await route.fulfill({
    status: 204,
    headers: {
      'Access-Control-Allow-Origin': '*',
    },
  });
}

/**
 * Mock GET /api/v1/saved-searches returning an error.
 */
export async function mockSavedSearchesError(
  route: Route,
  statusCode?: number,
  message?: string
): Promise<void> {
  // Playwright calls the handler with (route, request) - the second argument is
  // the request object and not the status code.
  const status = typeof statusCode === 'number' ? statusCode : 500;
  const text = typeof message === 'string' ? message : 'Failed to load saved searches';
  await route.fulfill({
    status,
    headers: {
      'Content-Type': 'application/json',
      'Access-Control-Allow-Origin': '*',
    },
    body: JSON.stringify({ detail: text }),
  });
}

/**
 * Mock GET /api/v1/saved-searches returning 401 unauthorized.
 */
export async function mockSavedSearchesUnauthorized(route: Route): Promise<void> {
  await route.fulfill({
    status: 401,
    headers: {
      'Content-Type': 'application/json',
      'Access-Control-Allow-Origin': '*',
    },
    body: JSON.stringify({ detail: 'Not authenticated' }),
  });
}
