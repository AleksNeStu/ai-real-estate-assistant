/**
 * The Gate E2E tests.
 *
 * The account routes answer an anonymous visitor with the wall: what an
 * account gives, and the two ways in. A signed-in visitor gets the page.
 *
 * The gate decides from the backend's capabilities, so the tests answer the
 * capabilities endpoint and say what the deployment can do.
 */

import { test, expect } from '@playwright/test';

const GATE_ROUTE = '/en/favorites';

/**
 * The capabilities of a deployment that has accounts and asks for them.
 */
function capabilities(emailEnabled = false) {
  return {
    auth: {
      jwt_enabled: true,
      demo_user_bypass: false,
      oauth: { google: false, apple: false },
    },
    email: { enabled: emailEnabled, provider: emailEnabled ? 'smtp' : 'dummy' },
    llm: { demo_mode: true, mode: 'local-model', provider: 'ollama', model: 'demo' },
    lead_capture: { waitlist_enabled: emailEnabled },
    observability: { error_tracking: false },
  };
}

test.describe('The Gate', () => {
  test('a signed-out visitor gets the wall with its two actions', async ({ page }) => {
    await page.route('**/api/v1/capabilities', async (route) => {
      await route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(capabilities()),
      });
    });
    // No user: the visitor is anonymous.
    await page.route('**/api/v1/auth/me', async (route) => {
      await route.fulfill({
        status: 401,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ detail: 'Not authenticated' }),
      });
    });

    await page.goto(GATE_ROUTE);

    // The wall says what the route is about and offers the two ways in.
    // The scope is the page: the bar carries a sign-in of its own.
    const wall = page.getByRole('main');
    const signIn = wall.getByRole('link', { name: /sign in/i }).first();
    const register = wall.getByRole('link', { name: /create an account/i }).first();
    await expect(signIn).toBeVisible({ timeout: 15000 });
    await expect(register).toBeVisible();

    // The two ways in carry the route back, so the visitor lands where they
    // were going once the account exists.
    await expect(signIn).toHaveAttribute('href', /\/auth\/login\?redirect=/);
    await expect(register).toHaveAttribute('href', /\/auth\/register\?redirect=/);

    // The account content itself is not there.
    await expect(page.getByTestId('favorite-card')).toHaveCount(0);
  });

  test('a signed-in visitor gets the content', async ({ page }) => {
    await page.route('**/api/v1/capabilities', async (route) => {
      await route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(capabilities()),
      });
    });
    await page.route('**/api/v1/auth/me', async (route) => {
      await route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          id: 'test-user-001',
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
        sameSite: 'Lax',
      },
    ]);
    await page.route('**/api/v1/favorites*', async (route) => {
      await route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ items: [], total: 0 }),
      });
    });
    await page.route('**/api/v1/collections*', async (route) => {
      await route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ items: [] }),
      });
    });

    await page.goto(GATE_ROUTE);

    // The wall is gone: the route's own heading is there.
    const wall = page.getByRole('main');
    await expect(wall.getByRole('heading', { name: /favorites/i }).first()).toBeVisible({
      timeout: 15000,
    });
    await expect(wall.getByRole('link', { name: /sign in/i }).first()).toHaveCount(0);
  });
});
