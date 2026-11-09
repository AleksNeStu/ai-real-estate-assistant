import { test, expect } from '@playwright/test';
import { mkdir } from 'fs/promises';
import { mockLandingApis } from './mocks';

const SCREENSHOT_DIR = process.env.PLAYWRIGHT_SCREENSHOT_DIR || 'artifacts/playwright/screenshots';

async function ensureScreenshotDir(): Promise<void> {
  await mkdir(SCREENSHOT_DIR, { recursive: true });
}

/**
 * Setup authentication mocks for a page.
 * This allows tests to bypass authentication.
 */
async function setupAuth(page: import('@playwright/test').Page): Promise<void> {
  // Mock /auth/me to return authenticated user
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

  // Set auth cookie to simulate logged-in state
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
}

test.describe('UI Smoke', () => {
  test('home renders and navigation is available @smoke', async ({ page }) => {
    await ensureScreenshotDir();
    await setupAuth(page);
    // The landing asks the API for the catalogue numbers, for the state of
    // the deployment and for a live slice of the catalogue. Without a
    // backend those requests hang and the page never settles, so they are
    // answered here.
    await mockLandingApis(page);
    await page.goto('/');
    // Wait for page to load - either home or login redirect
    await page.waitForLoadState('load');

    // Check if we're on login page - if so, we need to skip auth requirement
    const isLoginPage = page.url().includes('/auth/login');
    if (isLoginPage) {
      // App requires auth - test the login page instead
      await expect(page.getByRole('heading', { name: /sign in|log in/i })).toBeVisible({ timeout: 10000 });
    } else {
      // On the landing - the navigation carries the sections of the page
      // (the app links are on the app pages, not on the landing). The
      // assertions name the anchors, not the labels: the landing is
      // localized and the default locale is Polish.
      const nav = page.getByRole('navigation').first();
      await expect(nav.locator('a[href="#features"]')).toBeVisible();
      await expect(nav.locator('a[href="#faq"]')).toBeVisible();
    }
    await page.screenshot({ path: `${SCREENSHOT_DIR}/home.png`, fullPage: true });
  });

  test('chat streams assistant response @smoke', async ({ page }) => {
    await ensureScreenshotDir();
    await setupAuth(page);

    await page.route('**/api/v1/chat', async (route) => {
      if (route.request().method() === 'OPTIONS') {
        await route.fulfill({
          status: 204,
          headers: {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, X-API-Key, X-User-Email',
            'Access-Control-Expose-Headers': 'X-Request-ID',
          },
          body: '',
        });
        return;
      }
      await route.fulfill({
        status: 200,
        headers: {
          'Content-Type': 'text/event-stream',
          'Cache-Control': 'no-cache',
          'Access-Control-Allow-Origin': '*',
          'Access-Control-Expose-Headers': 'X-Request-ID',
          'X-Request-ID': 'req-stream-ok',
        },
        body: 'data: STREAM_OK\n\ndata: [DONE]\n\n',
      });
    });

    await page.goto('/chat');
    await page.waitForLoadState('networkidle');

    // Check if redirected to login
    const isLoginPage = page.url().includes('/auth/login');
    if (isLoginPage) {
      // App requires auth - verify login page loads
      await expect(page.getByRole('heading', { name: /sign in|log in/i })).toBeVisible({ timeout: 10000 });
      await page.screenshot({ path: `${SCREENSHOT_DIR}/chat_redirect_login.png`, fullPage: true });
      return;
    }

    // On chat page - verify elements and test chat
    // Placeholder changes based on state - initial: "Type your question here..." or after first message: "Ask about properties..."
    const messageInput = page.getByPlaceholder(/Ask about|Type your question/i);
    await expect(messageInput).toBeVisible({ timeout: 10000 });
    await messageInput.fill('Test message');
    await page.getByRole('button', { name: /send message|send/i }).click();

    await expect(page.getByText('STREAM_OK')).toBeVisible({ timeout: 10000 });
    await page.screenshot({ path: `${SCREENSHOT_DIR}/chat_stream.png`, fullPage: true });
  });

  test('chat retry recovers after a failed stream @smoke', async ({ page }) => {
    await ensureScreenshotDir();
    await setupAuth(page);

    let attempt = 0;
    await page.route('**/api/v1/chat', async (route) => {
      if (route.request().method() === 'OPTIONS') {
        await route.fulfill({
          status: 204,
          headers: {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, X-API-Key, X-User-Email',
            'Access-Control-Expose-Headers': 'X-Request-ID',
          },
          body: '',
        });
        return;
      }
      attempt += 1;
      if (attempt === 1) {
        await route.fulfill({
          status: 500,
          headers: {
            'Content-Type': 'text/plain',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Expose-Headers': 'X-Request-ID',
            'X-Request-ID': 'req-stream-fail',
          },
          body: 'Simulated failure',
        });
        return;
      }
      await route.fulfill({
        status: 200,
        headers: {
          'Content-Type': 'text/event-stream',
          'Cache-Control': 'no-cache',
          'Access-Control-Allow-Origin': '*',
          'Access-Control-Expose-Headers': 'X-Request-ID',
          'X-Request-ID': 'req-stream-retry-ok',
        },
        body: 'data: RECOVERED_OK\n\ndata: [DONE]\n\n',
      });
    });

    await page.goto('/chat');
    await page.waitForLoadState('networkidle');

    // Check if redirected to login
    const isLoginPage = page.url().includes('/auth/login');
    if (isLoginPage) {
      // App requires auth - verify login page loads
      await expect(page.getByRole('heading', { name: /sign in|log in/i })).toBeVisible({ timeout: 10000 });
      await page.screenshot({ path: `${SCREENSHOT_DIR}/chat_retry_redirect_login.png`, fullPage: true });
      return;
    }

    // On chat page - test retry functionality
    // Placeholder changes based on state - initial: "Type your question here..." or after first message: "Ask about properties..."
    const messageInput = page.getByPlaceholder(/Ask about|Type your question/i);
    await expect(messageInput).toBeVisible({ timeout: 10000 });
    await messageInput.fill('Retry message');
    await page.getByRole('button', { name: /send message|send/i }).click();

    await expect(page.getByRole('button', { name: /retry/i })).toBeVisible({ timeout: 10000 });

    await page.getByRole('button', { name: /retry/i }).click();
    await expect(page.getByText('RECOVERED_OK')).toBeVisible({ timeout: 10000 });
    await page.screenshot({ path: `${SCREENSHOT_DIR}/chat_retry_recovered.png`, fullPage: true });
  });
});
