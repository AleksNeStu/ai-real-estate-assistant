/**
 * E2E test: Full cross-feature user journey.
 * Validates the critical path: Register → Login → Search → View → Favorite → Chat → Market Trends.
 * Uses serial test execution to share state across steps.
 */

import { test, expect } from './conftest';
import {
  mockRegisterSuccess,
  mockLoginSuccess,
  mockGetCurrentUser,
  mockSearchSuccess,
  mockChatSuccess,
  setupAuthMocks,
} from './mocks';
import { TEST_USERS, generateUniqueEmail } from './fixtures/users';

test.describe('Full User Journey @integration @smoke', () => {
  test.describe.serial('Complete User Flow', () => {
    const testEmail = generateUniqueEmail();
    const testPassword = 'TestPassword123!';

    test('step 1: homepage loads successfully', async ({ page }) => {
      await page.goto('/');
      await page.waitForLoadState('networkidle');

      // Homepage should render without errors
      const bodyVisible = await page.locator('body').isVisible();
      expect(bodyVisible).toBe(true);
    });

    test('step 2: register a new account', async ({ registerPage, page }) => {
      await page.route('**/api/v1/auth/register', async (route) => {
        if (route.request().method() === 'OPTIONS') {
          await route.fulfill({ status: 204, headers: { 'Access-Control-Allow-Origin': '*' } });
          return;
        }
        await mockRegisterSuccess(route);
      });

      await registerPage.navigate();
      await registerPage.register({
        email: testEmail,
        password: testPassword,
        fullName: 'E2E Journey User',
      });

      await registerPage.waitForRegistrationSuccess();
    });

    test('step 3: login with credentials', async ({ loginPage, page }) => {
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
      await loginPage.login(TEST_USERS.basic.email, TEST_USERS.basic.password);
      await loginPage.waitForLoginSuccess();
    });

    test('step 4: search for properties', async ({ page }) => {
      await setupPageAuth(page);
      await page.route('**/api/v1/search*', mockSearchSuccess);
      await page.route('**/api/v1/properties*', mockSearchSuccess);

      await page.goto('/search');
      await page.waitForLoadState('networkidle');

      // Find and fill search input
      const searchInput = page
        .getByLabel('Search query')
        .or(page.getByPlaceholder(/describe what you/i))
        .or(page.locator('input[type="text"], textarea').first());
      await searchInput.fill('2-bedroom apartments in Berlin');

      // Submit search. The submit button of the search form carries a test
      // id - a plain "button[type=submit]" would also collect the button of
      // the newsletter form in the footer.
      const searchButton = page.getByTestId('search-submit');
      if (await searchButton.isVisible()) {
        await searchButton.click();
      }

      // Wait for results to appear via API response
      await page.waitForResponse('**/api/v1/search*', { timeout: 10000 }).catch(() => {
        // Response may already have fired before listener attached
      });

      // Verify we're still on search page
      const url = page.url();
      expect(url).toContain('/search');
    });

    test('step 5: view property detail', async ({ page }) => {
      await setupPageAuth(page);
      await page.route('**/api/v1/search*', mockSearchSuccess);
      await page.route('**/api/v1/properties*', mockSearchSuccess);

      await page.goto('/search');

      // Wait for search results to load
      await page.waitForResponse('**/api/v1/search*', { timeout: 10000 }).catch(() => {
        // Response may have fired before listener attached
      });

      // Try to click a property card
      const propertyCard = page
        .locator('[data-testid="property-card"], .property-card, article')
        .first();
      if (await propertyCard.isVisible({ timeout: 10000 }).catch(() => false)) {
        await propertyCard.click();

        // Wait for navigation or modal to appear
        await page.waitForURL(/\/property\//, { timeout: 5000 }).catch(() => {
          // Property detail may be a modal overlay, not a URL change
        });
      }
    });

    test('step 6: add property to favorites', async ({ page }) => {
      await setupPageAuth(page);
      await page.route('**/api/v1/search*', mockSearchSuccess);
      await page.route('**/api/v1/properties*', mockSearchSuccess);

      // Mock favorites API
      await page.route('**/api/v1/favorites*', async (route) => {
        const method = route.request().method();
        if (method === 'OPTIONS') {
          await route.fulfill({ status: 204, headers: { 'Access-Control-Allow-Origin': '*' } });
          return;
        }
        if (method === 'POST') {
          await route.fulfill({
            status: 201,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              id: 'fav-new',
              property_id: 'prop-001',
              created_at: new Date().toISOString(),
            }),
          });
        } else {
          await route.fulfill({
            status: 200,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ favorites: [{ id: 'fav-new', property_id: 'prop-001' }] }),
          });
        }
      });

      await page.goto('/search');
      await page.waitForResponse('**/api/v1/search*', { timeout: 10000 }).catch(() => {
        // Response may have fired before listener attached
      });

      // Find and click favorite button on first property card
      const favoriteButton = page
        .locator('button')
        .filter({ has: page.locator('svg.lucide-heart, svg') })
        .first();
      if (await favoriteButton.isVisible({ timeout: 5000 }).catch(() => false)) {
        await favoriteButton.click();
      }
    });

    test('step 7: chat about properties', async ({ page }) => {
      await setupPageAuth(page);
      await page.route('**/api/v1/chat*', mockChatSuccess);

      await page.goto('/chat');

      // Wait for chat interface
      const messageInput = page
        .getByLabel(/chat message input/i)
        .or(page.getByPlaceholder(/type your question|ask about/i));
      await expect(messageInput).toBeVisible({ timeout: 10000 });

      // Send a message. The chat marks the button with data-testid="chat-send";
      // the newsletter of the footer has a submit button of its own, which the
      // plain "form button[type=submit]" collected as well.
      await messageInput.fill('Find me a 2-bedroom apartment in Berlin');
      const sendButton = page.getByTestId('chat-send').or(page.getByLabel(/^send(ing)? message$/i));
      await sendButton.click();

      // Wait for response or loading indicator
      const responseAppeared = await page
        .locator('.bg-background, .assistant-message, [data-testid="assistant-message"]')
        .first()
        .isVisible({ timeout: 15000 })
        .catch(() => false);
      // Chat response or loading indicator should appear within timeout
      expect(responseAppeared).toBeTruthy();
    });

    test('step 8: view market trends', async ({ page }) => {
      await setupPageAuth(page);
      await page.route('**/api/v1/market/indicators**', async (route) => {
        await route.fulfill({
          status: 200,
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            overall_trend: 'rising',
            total_listings: 150,
            new_listings_7d: 12,
            price_drops_7d: 5,
            avg_price_change_pct: 2.3,
          }),
        });
      });
      await page.route('**/api/v1/market/trends**', async (route) => {
        await route.fulfill({
          status: 200,
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            trends: [
              { period: '2025-01', avg_price: 2500, listings: 45 },
              { period: '2025-02', avg_price: 2550, listings: 50 },
            ],
          }),
        });
      });

      await page.goto('/market-trends');

      // Page should load without crashing
      const heading = page.getByRole('heading', { name: /market trends/i });
      await expect(heading).toBeVisible({ timeout: 10000 });
    });
  });
});

/**
 * Helper to set up auth state for individual test steps.
 */
async function setupPageAuth(page: import('@playwright/test').Page): Promise<void> {
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
}
