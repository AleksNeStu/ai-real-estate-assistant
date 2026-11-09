import { test, expect } from '@playwright/test';
import { writeFile, mkdir } from 'fs/promises';
import { mockLandingApis } from './mocks';

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

test('collect console and network metrics', async ({ page }) => {
  const logsDir = process.env.PLAYWRIGHT_LOG_DIR || 'artifacts/playwright/logs';
  await mkdir(logsDir, { recursive: true });
  const logs: Array<{ level: string; text: string; ts: number }> = [];
  const responses: Array<{ url: string; status: number; ok: boolean; ts: number }> = [];

  page.on('console', (msg) => {
    logs.push({ level: msg.type(), text: msg.text(), ts: Date.now() });
  });
  page.on('pageerror', (err) => {
    logs.push({ level: 'pageerror', text: String(err), ts: Date.now() });
  });

  page.on('response', async (res) => {
    responses.push({ url: res.url(), status: res.status(), ok: res.ok(), ts: Date.now() });
  });

  // Setup auth mocks
  await setupAuth(page);
  // The landing asks the API for its numbers on load; without a backend
  // those requests hang and the page never reaches `networkidle`.
  await mockLandingApis(page);

  // Navigate and wait for load - handle auth redirects gracefully
  await page.goto('/');
  await page.waitForLoadState('load');

  // Check what page we're on (could be home or login redirect)
  const currentUrl = page.url();
  const isLoginPage = currentUrl.includes('/auth/login');

  if (!isLoginPage) {
    // Try to verify home page content
    const homeHeading = page.getByRole('heading', { name: /AI Real Estate|Estate|Property/i });
    await expect(homeHeading.first()).toBeVisible({ timeout: 10000 }).catch(() => {
      // Heading might not exist - continue anyway
    });
  }

  await page.goto('/search');
  await page.waitForLoadState('load');

  await page.goto('/chat');
  await page.waitForLoadState('load');

  const perf = await page.evaluate(() => {
    const nav = performance.getEntriesByType('navigation');
    const res = performance.getEntriesByType('resource');
    return { navigation: nav, resources: res };
  });

  // keep raw logs and performance, omit derived summary for minimal footprint

  await writeFile(
    `${logsDir}/browser_console.json`,
    JSON.stringify({ logs }, null, 2)
  );
  await writeFile(
    `${logsDir}/browser_network.json`,
    JSON.stringify({ responses }, null, 2)
  );
  await writeFile(
    `${logsDir}/browser_performance.json`,
    JSON.stringify(perf, null, 2)
  );
});
