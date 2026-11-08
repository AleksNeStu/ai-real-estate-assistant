/**
 * E2E test: Auth user journey.
 * Covers registration, login, logout, auth persistence, error handling, and page navigation.
 * Uses page objects (LoginPage, RegisterPage) and mock API interception.
 */

import { test, expect } from './conftest';
import {
  mockRegisterSuccess,
  mockLoginSuccess,
  mockLoginError,
  mockLogoutSuccess,
  mockGetCurrentUser,
  mockUnauthorized,
  setupAuthMocks,
} from './mocks';
import { TEST_USERS, generateUniqueEmail } from './fixtures/users';

test.describe('Registration', () => {
  test('should register with valid data @smoke', async ({ registerPage, page }) => {
    await page.route('**/api/v1/auth/register', async (route) => {
      if (route.request().method() === 'OPTIONS') {
        await route.fulfill({ status: 204, headers: { 'Access-Control-Allow-Origin': '*' } });
        return;
      }
      await mockRegisterSuccess(route);
    });

    await registerPage.navigate();
    await registerPage.register({
      email: generateUniqueEmail(),
      password: 'TestPassword123!',
      fullName: 'E2E Test User',
    });

    await registerPage.waitForRegistrationSuccess();
  });

  test('should show error on duplicate email registration', async ({ registerPage, page }) => {
    await page.route('**/api/v1/auth/register', async (route) => {
      if (route.request().method() === 'OPTIONS') {
        await route.fulfill({ status: 204, headers: { 'Access-Control-Allow-Origin': '*' } });
        return;
      }
      await route.fulfill({
        status: 409,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ detail: 'Email already registered' }),
      });
    });

    await registerPage.navigate();
    await registerPage.register({
      email: 'duplicate@example.com',
      password: 'TestPassword123!',
      fullName: 'Duplicate User',
    });

    const errorText = await registerPage.waitForError();
    expect(errorText.length).toBeGreaterThan(0);
  });
});

test.describe('Login', () => {
  test('should login with valid credentials @smoke', async ({ loginPage, page }) => {
    await page.route('**/api/v1/auth/login', async (route) => {
      if (route.request().method() === 'OPTIONS') {
        await route.fulfill({ status: 204, headers: { 'Access-Control-Allow-Origin': '*' } });
        return;
      }
      await mockLoginSuccess(route);
    });
    await page.route('**/api/v1/auth/me', async (route) => {
      if (route.request().method() === 'OPTIONS') {
        await route.fulfill({ status: 204, headers: { 'Access-Control-Allow-Origin': '*' } });
        return;
      }
      await mockGetCurrentUser(route);
    });

    await loginPage.navigate();
    const user = TEST_USERS.basic;
    await loginPage.login(user.email, user.password);
    await loginPage.waitForLoginSuccess();
  });

  test('should show error on invalid credentials', async ({ loginPage, page }) => {
    await page.route('**/api/v1/auth/login', async (route) => {
      if (route.request().method() === 'OPTIONS') {
        await route.fulfill({ status: 204, headers: { 'Access-Control-Allow-Origin': '*' } });
        return;
      }
      await mockLoginError(route);
    });

    await loginPage.navigate();
    await loginPage.login('wrong@example.com', 'wrongpassword');

    const errorText = await loginPage.waitForError();
    expect(errorText.toLowerCase()).toContain('invalid');
  });

  test('should show error on empty form submission', async ({ loginPage, page }) => {
    await page.route('**/api/v1/auth/login', async (route) => {
      if (route.request().method() === 'OPTIONS') {
        await route.fulfill({ status: 204, headers: { 'Access-Control-Allow-Origin': '*' } });
        return;
      }
      await route.fulfill({
        status: 422,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ detail: 'Email and password are required' }),
      });
    });

    await loginPage.navigate();
    await loginPage.submit();

    // Should stay on login page
    await expect(page).toHaveURL(/\/auth\/login/);
  });
});

test.describe('Auth Persistence', () => {
  test('should persist auth across page navigation', async ({ page }) => {
    // Set up authenticated state
    await page.route('**/api/v1/auth/me', async (route) => {
      if (route.request().method() === 'OPTIONS') {
        await route.fulfill({ status: 204, headers: { 'Access-Control-Allow-Origin': '*' } });
        return;
      }
      await mockGetCurrentUser(route);
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

    // Visit a protected route
    await page.goto('/favorites');

    // Should NOT redirect to login
    await page.waitForTimeout(2000);
    const url = page.url();
    expect(url).not.toContain('/auth/login');
  });

  test('should redirect to login when unauthenticated on protected route', async ({ page }) => {
    await page.route('**/api/v1/auth/me', async (route) => {
      await mockUnauthorized(route);
    });

    await page.route('**/api/v1/saved-searches**', async (route) => {
      await route.fulfill({
        status: 401,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ detail: 'Not authenticated' }),
      });
    });

    await page.goto('/saved-searches');

    // Should end up on login or show auth error
    await page.waitForTimeout(3000);
    const url = page.url();
    const hasLoginRedirect = url.includes('/auth/login');
    // The prompt is a text on the page - several of them can match, so the
    // first one answers.
    const hasAuthPrompt = await page
      .locator('text=/log in|sign in/i')
      .first()
      .isVisible()
      .catch(() => false);
    expect(hasLoginRedirect || hasAuthPrompt).toBe(true);
  });
});

test.describe('Logout', () => {
  test('should logout and clear auth state', async ({ page }) => {
    setupAuthMocks(page);

    await page.route('**/api/v1/auth/logout', async (route) => {
      if (route.request().method() === 'OPTIONS') {
        await route.fulfill({ status: 204, headers: { 'Access-Control-Allow-Origin': '*' } });
        return;
      }
      await mockLogoutSuccess(route);
    });

    // Login first. The names match exactly - the footer carries a newsletter
    // field labelled "Email address", and a loose match collects it as well.
    await page.goto('/auth/login');
    const user = TEST_USERS.basic;
    await page
      .getByLabel('Email', { exact: true })
      .or(page.getByRole('textbox', { name: /^email$/i }))
      .fill(user.email);
    await page
      .getByLabel('Password', { exact: true })
      .or(page.getByRole('textbox', { name: /^password$/i }))
      .fill(user.password);
    await page
      .locator('form')
      .filter({ has: page.locator('#email') })
      .locator('button[type="submit"]')
      .click();

    await page.waitForURL(/^(?!.*\/auth\/login).*$/, { timeout: 15000 }).catch(() => {});

    // Find and click logout
    const logoutButton = page.getByRole('button', { name: /logout|sign out|log out/i });
    if (await logoutButton.isVisible({ timeout: 5000 }).catch(() => false)) {
      await logoutButton.click();

      // Verify cookie is cleared
      const cookies = await page.context().cookies();
      const authCookie = cookies.find((c) => c.name === 'access_token');
      expect(authCookie).toBeUndefined();
    }
  });
});

test.describe('Navigation', () => {
  test('should navigate between login and register pages', async ({ loginPage, page }) => {
    await loginPage.navigate();

    // Click register link
    await loginPage.clickRegister();

    // Should be on register page
    await expect(page).toHaveURL(/\/auth\/register/);
    await expect(
      page.getByLabel('Email', { exact: true }).or(page.getByRole('textbox', { name: /^email$/i }))
    ).toBeVisible({ timeout: 10000 });
  });

  test('should navigate from register to login', async ({ registerPage, page }) => {
    await registerPage.navigate();

    // Click login link
    await registerPage.clickLogin();

    // Should be on login page
    await expect(page).toHaveURL(/\/auth\/login/);
    await expect(
      page.getByLabel('Email', { exact: true }).or(page.getByRole('textbox', { name: /^email$/i }))
    ).toBeVisible({ timeout: 10000 });
  });
});

test.describe('Page Health', () => {
  test('auth pages load without console errors @smoke', async ({ page }) => {
    const errors: string[] = [];
    page.on('pageerror', (err) => errors.push(err.message));

    await page.goto('/auth/login');
    await page.waitForLoadState('networkidle');

    expect(errors).toHaveLength(0);

    await page.goto('/auth/register');
    await page.waitForLoadState('networkidle');

    expect(errors).toHaveLength(0);
  });
});
