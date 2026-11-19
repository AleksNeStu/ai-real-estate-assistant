/**
 * The buyer memory in the account area (Task #88).
 *
 * The legal pages promise the visitor that the memory can be seen and deleted
 * "through your account". This spec drives that promise end to end: the
 * visitor signs in, opens the account, deletes the memory and sees it gone.
 *
 * The endpoint is mocked, because the erasure belongs to a real account and a
 * real JWT - the spec drives the SURFACE, not the database.
 */

import { test, expect } from '../conftest';

// --- Mock Data ---

const MOCK_FACTS = [
  {
    id: 'fact-budget',
    kind: 'budget',
    content: 'up to 500,000 PLN',
    listing_id: null,
    confidence: 0.9,
    source: 'chat',
    created_at: '2026-11-01T10:00:00Z',
    expires_at: '2027-11-01T10:00:00Z',
  },
  {
    id: 'fact-disliked',
    kind: 'disliked',
    content: 'the flat with the balcony',
    listing_id: 'prop-001',
    confidence: 0.8,
    source: 'chat',
    created_at: '2026-11-02T10:00:00Z',
    expires_at: '2027-11-02T10:00:00Z',
  },
];

/**
 * Sign the visitor in and mock the account endpoint the memory lives on.
 *
 * The facts are held in the mock, so a delete really removes them from what
 * the next read returns - the spec can therefore see the memory gone.
 */
async function setupAccount(page: import('@playwright/test').Page) {
  let facts = [...MOCK_FACTS];

  await page.addInitScript(() => {
    window.localStorage.setItem('userEmail', 'test@example.com');
  });

  // Auth mock
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

  // The buyer memory endpoint: the read lists the facts, the delete erases
  // them and reports how many went.
  await page.route('**/api/v1/me/buyer-memory*', async (route) => {
    const request = route.request();

    if (request.method() === 'DELETE') {
      const deleted = facts.length;
      facts = [];
      await route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ deleted }),
      });
      return;
    }

    await route.fulfill({
      status: 200,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ facts, count: facts.length }),
    });
  });

  // The model catalogue the settings screen reads on mount.
  await page.route('**/api/v1/settings/models', async (route) => {
    await route.fulfill({
      status: 200,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify([]),
    });
  });

  // Model preferences. The system defaults live under the same path and have
  // their own shape - the two answers are told apart by the URL.
  await page.route('**/api/v1/model-preferences**', async (route) => {
    if (route.request().url().includes('/system/defaults')) {
      await route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ defaults: [], available_providers: [], available_models: [] }),
      });
      return;
    }
    await route.fulfill({
      status: 200,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ items: [], total: 0 }),
    });
  });
}

// --- Tests ---

test.describe('The buyer memory in the account area', () => {
  test('the visitor sees what is remembered about them @smoke', async ({ page }) => {
    await setupAccount(page);

    await page.goto('/settings');

    const privacyTab = page.getByRole('tab', { name: /^privacy$/i });
    await expect(privacyTab).toBeVisible({ timeout: 15000 });
    await privacyTab.click();

    // The facts are listed, one per row, with the kind named. The kind is read
    // exactly: the panel's own description mentions a budget in a sentence.
    await expect(page.getByText('up to 500,000 PLN')).toBeVisible({ timeout: 15000 });
    await expect(page.getByText('the flat with the balcony')).toBeVisible();
    await expect(page.getByText('Budget', { exact: true })).toBeVisible();
    await expect(page.getByText('Listing you disliked', { exact: true })).toBeVisible();
  });

  test('the visitor deletes the memory and sees it gone', async ({ page }) => {
    await setupAccount(page);

    await page.goto('/settings');

    const privacyTab = page.getByRole('tab', { name: /^privacy$/i });
    await expect(privacyTab).toBeVisible({ timeout: 15000 });
    await privacyTab.click();

    await expect(page.getByText('up to 500,000 PLN')).toBeVisible({ timeout: 15000 });

    // The delete asks first.
    await page.getByRole('button', { name: /delete the memory/i }).click();
    await expect(page.getByText('Delete the buyer memory?')).toBeVisible();

    await page.getByRole('button', { name: 'Delete it' }).click();

    // The facts are gone and the account says so.
    await expect(page.getByText('up to 500,000 PLN')).toBeHidden({ timeout: 15000 });
    await expect(page.getByText('Nothing is remembered about you.')).toBeVisible();
    await expect(page.getByText('2 facts deleted')).toBeVisible();
  });

  test('cancelling the confirmation keeps the memory', async ({ page }) => {
    await setupAccount(page);

    await page.goto('/settings');

    const privacyTab = page.getByRole('tab', { name: /^privacy$/i });
    await expect(privacyTab).toBeVisible({ timeout: 15000 });
    await privacyTab.click();

    await expect(page.getByText('up to 500,000 PLN')).toBeVisible({ timeout: 15000 });

    await page.getByRole('button', { name: /delete the memory/i }).click();
    await expect(page.getByText('Delete the buyer memory?')).toBeVisible();
    await page.getByRole('button', { name: 'Cancel' }).click();

    // The question is closed and the memory is untouched.
    await expect(page.getByText('Delete the buyer memory?')).toBeHidden();
    await expect(page.getByText('up to 500,000 PLN')).toBeVisible();
  });
});
