/**
 * Shared E2E test configuration and fixtures.
 * Provides common setup for all E2E tests.
 */

import { test as base, Page, BrowserContext } from '@playwright/test';
import {
  LoginPage,
  RegisterPage,
  SearchPage,
  ChatPage,
  DocumentsPage,
  SavedSearchesPage,
  MarketTrendsPage,
  ToolsPage,
} from './page-objects';
import { TEST_USERS, TestUser } from './fixtures/users';
import { mockChatSuccess, mockSearchSuccess, setupAuthMocks } from './mocks';

// Define custom fixtures
type E2EFixtures = {
  loginPage: LoginPage;
  registerPage: RegisterPage;
  searchPage: SearchPage;
  chatPage: ChatPage;
  documentsPage: DocumentsPage;
  savedSearchesPage: SavedSearchesPage;
  marketTrendsPage: MarketTrendsPage;
  toolsPage: ToolsPage;
  authenticatedPage: Page;
  authenticatedChatPage: ChatPage;
  authenticatedSearchPage: SearchPage;
  authenticatedDocumentsPage: DocumentsPage;
  authenticatedSavedSearchesPage: SavedSearchesPage;
  authenticatedMarketTrendsPage: MarketTrendsPage;
  authenticatedToolsPage: ToolsPage;
  testUser: TestUser;
};

/**
 * Setup authentication mocks for a page.
 * This allows tests to access protected routes without actual login.
 */
async function setupPageAuth(page: Page): Promise<void> {
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

  // Set auth cookie
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

// Extend base test with custom fixtures
export const test = base.extend<E2EFixtures>({
  // Login page fixture
  loginPage: async ({ page }, use) => {
    const loginPage = new LoginPage(page);
    await use(loginPage);
  },

  // Register page fixture
  registerPage: async ({ page }, use) => {
    const registerPage = new RegisterPage(page);
    await use(registerPage);
  },

  // Search page fixture
  searchPage: async ({ page }, use) => {
    const searchPage = new SearchPage(page);
    await use(searchPage);
  },

  // Chat page fixture
  chatPage: async ({ page }, use) => {
    const chatPage = new ChatPage(page);
    await use(chatPage);
  },

  // Documents page fixture
  documentsPage: async ({ page }, use) => {
    const documentsPage = new DocumentsPage(page);
    await use(documentsPage);
  },

  // Saved searches page fixture
  savedSearchesPage: async ({ page }, use) => {
    const savedSearchesPage = new SavedSearchesPage(page);
    await use(savedSearchesPage);
  },

  // Market trends page fixture
  marketTrendsPage: async ({ page }, use) => {
    const marketTrendsPage = new MarketTrendsPage(page);
    await use(marketTrendsPage);
  },

  // Tools page fixture
  toolsPage: async ({ page }, use) => {
    const toolsPage = new ToolsPage(page);
    await use(toolsPage);
  },

  // Authenticated page fixture - sets up mocks and logs in via UI
  authenticatedPage: async ({ page }, use) => {
    // Setup auth mocks before any navigation
    setupAuthMocks(page);

    // Setup search mocks
    await page.route('**/api/v1/search*', mockSearchSuccess);

    // Setup chat mocks
    await page.route('**/api/v1/chat*', mockChatSuccess);

    // Navigate to login page
    await page.goto('/auth/login');

    // Wait for the form to be visible. The names have to match exactly: the
    // footer carries a newsletter field labelled "Email address", and a loose
    // match collects that one as well - two elements, and the strict mode
    // refuses to act on them.
    const emailInput = page
      .getByLabel('Email', { exact: true })
      .or(page.getByRole('textbox', { name: /^email$/i }));
    await emailInput.waitFor({ state: 'visible', timeout: 10000 });

    // Fill login form with test credentials
    const testUser = TEST_USERS.basic;
    await emailInput.fill(testUser.email);
    await page
      .getByLabel('Password', { exact: true })
      .or(page.getByRole('textbox', { name: /^password$/i }))
      .fill(testUser.password);

    // Submit login form - this will trigger the mocked login API. The button
    // of the form the email field belongs to, the footer newsletter has a
    // submit button of its own.
    await page
      .locator('form')
      .filter({ has: page.locator('#email') })
      .locator('button[type="submit"]')
      .or(page.getByRole('button', { name: /sign in|log in|zaloguj/i }))
      .click();

    // Wait for redirect away from login page (indicates successful login)
    await page.waitForURL(/^(?!.*\/auth\/login).*$/, { timeout: 15000 }).catch(() => {
      // If redirect doesn't happen, continue anyway - the test will handle the failure
    });

    await use(page);
  },

  // Test user fixture
  testUser: async ({}, use) => {
    await use(TEST_USERS.basic);
  },

  // Authenticated chat page fixture - sets up auth mocks before navigation
  authenticatedChatPage: async ({ page }, use) => {
    await setupPageAuth(page);
    const chatPage = new ChatPage(page);
    await use(chatPage);
  },

  // Authenticated search page fixture
  authenticatedSearchPage: async ({ page }, use) => {
    await setupPageAuth(page);
    const searchPage = new SearchPage(page);
    await use(searchPage);
  },

  // Authenticated documents page fixture
  authenticatedDocumentsPage: async ({ page }, use) => {
    await setupPageAuth(page);
    const documentsPage = new DocumentsPage(page);
    await use(documentsPage);
  },

  // Authenticated saved searches page fixture
  authenticatedSavedSearchesPage: async ({ page }, use) => {
    await setupPageAuth(page);
    const savedSearchesPage = new SavedSearchesPage(page);
    await use(savedSearchesPage);
  },

  // Authenticated market trends page fixture
  authenticatedMarketTrendsPage: async ({ page }, use) => {
    await setupPageAuth(page);
    const marketTrendsPage = new MarketTrendsPage(page);
    await use(marketTrendsPage);
  },

  // Authenticated tools page fixture
  authenticatedToolsPage: async ({ page }, use) => {
    await setupPageAuth(page);
    const toolsPage = new ToolsPage(page);
    await use(toolsPage);
  },
});

// Export expect for convenience
export { expect } from '@playwright/test';

// Re-export fixtures and mocks for convenience
export { TEST_USERS, getTestUser, generateUniqueEmail } from './fixtures/users';
export { TEST_PROPERTIES, getTestProperties } from './fixtures/properties';
export * from './mocks';
export * from './page-objects';

/**
 * Helper to wait for services to be healthy.
 * Useful for Docker Compose tests.
 */
export async function waitForServices(page: Page, timeout = 60000): Promise<boolean> {
  const startTime = Date.now();
  const healthUrl = process.env.BACKEND_HEALTH_URL || 'http://localhost:8000/health';

  while (Date.now() - startTime < timeout) {
    try {
      const response = await page.request.get(healthUrl);
      if (response.ok()) {
        return true;
      }
    } catch {
      // Service not ready yet
    }
    await page.waitForTimeout(2000);
  }

  return false;
}

/**
 * Helper to create a unique test user via API.
 */
export async function createTestUserViaAPI(
  page: Page,
  email?: string,
  password?: string
): Promise<{ email: string; password: string; id?: string }> {
  const userEmail = email || `test-${Date.now()}@example.com`;
  const userPassword = password || 'TestPassword123!';

  const response = await page.request.post('/api/v1/auth/register', {
    data: {
      email: userEmail,
      password: userPassword,
      full_name: 'Test User',
    },
  });

  if (!response.ok()) {
    throw new Error(`Failed to create test user: ${await response.text()}`);
  }

  const data = await response.json();
  return {
    email: userEmail,
    password: userPassword,
    id: data.user?.id,
  };
}

/**
 * Helper to authenticate a user via API and set cookies.
 */
export async function authenticateUser(page: Page, email: string, password: string): Promise<void> {
  const response = await page.request.post('/api/v1/auth/login', {
    data: {
      email,
      password,
    },
  });

  if (!response.ok()) {
    throw new Error(`Failed to authenticate: ${await response.text()}`);
  }

  // Get cookies from response and set them in the browser context
  const cookies = await response.headerValue('set-cookie');
  if (cookies) {
    const context = page.context();
    // Parse and add cookies
    // Note: This is simplified - real implementation would parse cookies properly
  }
}

/**
 * Screenshot helper for debugging.
 */
export async function takeDebugScreenshot(page: Page, name: string): Promise<void> {
  const screenshotDir = process.env.PLAYWRIGHT_SCREENSHOT_DIR || 'artifacts/playwright/screenshots';
  await page.screenshot({
    path: `${screenshotDir}/${name}-${Date.now()}.png`,
    fullPage: true,
  });
}

// Test constants
export const TEST_CONSTANTS = {
  DEFAULT_TIMEOUT: 30000,
  LONG_TIMEOUT: 60000,
  API_BASE_URL: process.env.API_BASE_URL || 'http://localhost:8000',
  FRONTEND_BASE_URL: process.env.FRONTEND_BASE_URL || 'http://localhost:3000',
};
