/**
 * Settings page E2E tests.
 * Tests the /settings page: section visibility, notification toggles, model catalog, error handling.
 * Uses the authenticated page pattern from conftest.ts.
 */

import { test, expect } from '../conftest';

// --- Mock Data ---

const MOCK_NOTIFICATION_SETTINGS = {
  price_alerts_enabled: true,
  new_listings_enabled: true,
  saved_search_enabled: false,
  market_updates_enabled: false,
  alert_frequency: 'instant' as const,
  email_enabled: true,
  push_enabled: false,
  in_app_enabled: true,
  quiet_hours_start: null,
  quiet_hours_end: null,
  price_drop_threshold: 5,
  daily_digest_time: '09:00',
  weekly_digest_day: 'monday',
  expert_mode: false,
  marketing_emails: false,
  unsubscribe_token: null,
  unsubscribed_at: null,
  unsubscribed_types: [],
};

const MOCK_MODEL_CATALOG = [
  {
    name: 'openai',
    display_name: 'OpenAI',
    is_local: false,
    requires_api_key: true,
    models: [
      {
        id: 'gpt-4o',
        display_name: 'GPT-4o',
        context_window: 128000,
        capabilities: ['chat', 'tools'],
        pricing: {
          input_price_per_1m: 2.5,
          output_price_per_1m: 10.0,
          currency: 'USD',
        },
      },
    ],
  },
  {
    name: 'ollama',
    display_name: 'Ollama (Local)',
    is_local: true,
    requires_api_key: false,
    runtime_available: true,
    available_models: ['llama3.3:8b'],
    models: [
      {
        id: 'llama3.3:8b',
        display_name: 'Llama 3.3 8B',
        context_window: 8192,
        capabilities: ['chat'],
      },
    ],
  },
];

// --- Helpers ---

/**
 * Setup auth and common settings mocks.
 */
async function setupSettingsPage(page: import('@playwright/test').Page) {
  // The settings of the notification section belong to a user and are read
  // from the local storage - without the email the section only shows a hint
  // that an email is required.
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

  // Notification settings mock
  await page.route('**/api/v1/settings/notifications', async (route) => {
    if (route.request().method() === 'OPTIONS') {
      await route.fulfill({ status: 204, headers: { 'Access-Control-Allow-Origin': '*' } });
      return;
    }

    if (route.request().method() === 'PUT') {
      // Return the same settings (simulating a successful save)
      const body = await route.request().postDataJSON();
      await route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...MOCK_NOTIFICATION_SETTINGS, ...body }),
      });
      return;
    }

    await route.fulfill({
      status: 200,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(MOCK_NOTIFICATION_SETTINGS),
    });
  });

  // Model catalog mock
  await page.route('**/api/v1/settings/models', async (route) => {
    await route.fulfill({
      status: 200,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(MOCK_MODEL_CATALOG),
    });
  });

  // Model preferences mock
  await page.route('**/api/v1/settings/model-preferences', async (route) => {
    if (route.request().method() === 'OPTIONS') {
      await route.fulfill({ status: 204, headers: { 'Access-Control-Allow-Origin': '*' } });
      return;
    }
    await route.fulfill({
      status: 200,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        provider: 'openai',
        model: 'gpt-4o',
        fallback_provider: null,
        fallback_model: null,
      }),
    });
  });

  // Per-task model preferences mock
  await page.route('**/api/v1/model-preferences**', async (route) => {
    // The system defaults live under the same path and have their own shape.
    if (route.request().url().includes('/system/defaults')) {
      await route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          defaults: [],
          available_providers: ['openai', 'ollama'],
          available_models: { openai: ['gpt-4o'], ollama: ['llama3.3:8b'] },
        }),
      });
      return;
    }
    await route.fulfill({
      status: 200,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ items: [], total: 0 }),
    });
  });

  // Model runtime test mock
  await page.route('**/api/v1/settings/test-runtime**', async (route) => {
    await route.fulfill({
      status: 200,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        provider: 'ollama',
        is_local: true,
        runtime_available: true,
        available_models: ['llama3.3:8b'],
      }),
    });
  });
}

// --- Tests ---

test.describe('Settings Page', () => {
  test('should display all settings sections @smoke', async ({ page }) => {
    await setupSettingsPage(page);

    await page.goto('/settings');

    // Wait for main heading
    const mainHeading = page.getByRole('heading', { name: /^settings$/i });
    await expect(mainHeading).toBeVisible({ timeout: 15000 });

    // The screen carries five tabs and shows one of them at a time, so every
    // section is reached through its tab.
    for (const tab of ['Identity', 'Models', 'Notifications', 'Profile', 'Privacy']) {
      await page.getByRole('tab', { name: new RegExp(`^${tab}$`, 'i') }).click();
      await expect(
        page.getByRole('tab', { name: new RegExp(`^${tab}$`, 'i') })
      ).toHaveAttribute('aria-selected', 'true');
    }
  });

  test('should display current user identity settings', async ({ page }) => {
    await setupSettingsPage(page);

    await page.goto('/settings');

    // Wait for page to load, then open the tab that carries the identity
    await expect(page.getByRole('tab', { name: /^identity$/i })).toBeVisible({
      timeout: 15000,
    });
    await page.getByRole('tab', { name: /^identity$/i }).click();

    // The IdentitySettings card should have the email input. Only the id is
    // used: the footer of the site carries a newsletter field labelled
    // "Email address" as well, and a loose label match collects both.
    const emailInput = page.locator('#settings_user_email');
    await expect(emailInput).toBeVisible({ timeout: 10000 });

    // Should show the hint of the Identity card
    await expect(page.getByText(/stored locally in your browser/i)).toBeVisible();
  });

  test('should toggle notification setting and save', async ({ page }) => {
    await setupSettingsPage(page);

    await page.goto('/settings');

    // Wait for notifications section to be visible
    await page.getByRole('tab', { name: /^notifications$/i }).click();
    await expect(page.getByRole('heading', { name: /^notifications$/i })).toBeVisible({
      timeout: 15000,
    });

    // Find the "Price Alerts" checkbox
    const priceAlertsCheckbox = page.locator('#price_alerts');

    await expect(priceAlertsCheckbox).toBeVisible({ timeout: 10000 });

    // Verify initial state is checked
    await expect(priceAlertsCheckbox).toBeChecked();

    // Toggle the checkbox
    await priceAlertsCheckbox.uncheck();

    // The checkbox should now be unchecked
    await expect(priceAlertsCheckbox).not.toBeChecked();

    // Click "Save Preferences" button
    const saveButton = page.getByRole('button', { name: /save preferences/i });
    await saveButton.click();

    // Should show success message
    await expect(page.getByText(/settings saved successfully/i)).toBeVisible({ timeout: 10000 });
  });

  test('should display model catalog with providers', async ({ page }) => {
    await setupSettingsPage(page);

    await page.goto('/settings');

    // Wait for models section
    await page.getByRole('tab', { name: /^models$/i }).click();
    await expect(page.getByRole('heading', { name: /model catalogue/i })).toBeVisible({
      timeout: 15000,
    });

    // Should show model providers from the catalog. The names also appear in
    // the provider selection of the model settings - there they are options
    // of a closed list and therefore not visible. The catalog itself is
    // rendered in the table of the models section.
    const modelsSection = page.locator('section').filter({
      has: page.getByRole('heading', { name: /model catalogue/i }),
    });
    await expect(
      modelsSection.getByText('OpenAI', { exact: true }).locator('visible=true')
    ).toBeVisible({ timeout: 10000 });
    await expect(
      modelsSection.getByText('Ollama (Local)', { exact: true }).locator('visible=true')
    ).toBeVisible();

    // Should show model details
    await expect(modelsSection.getByText('GPT-4o').first()).toBeVisible();
    await expect(modelsSection.getByText('128k').first()).toBeVisible(); // context window

    // Should show the Refresh Catalog button
    await expect(page.getByRole('button', { name: /refresh catalog/i })).toBeVisible();
  });

  test('should handle error when notification settings save fails', async ({ page }) => {
    // The notification settings belong to a user - the email is read from the
    // local storage.
    await page.addInitScript(() => {
      window.localStorage.setItem('userEmail', 'test@example.com');
    });

    // Setup auth
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

    // GET returns settings normally
    await page.route('**/api/v1/settings/notifications', async (route) => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          status: 200,
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(MOCK_NOTIFICATION_SETTINGS),
        });
      } else if (route.request().method() === 'PUT') {
        // Simulate save failure
        await route.fulfill({
          status: 500,
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ detail: 'Internal server error' }),
        });
      }
    });

    // Model catalog mock (return empty to avoid errors)
    await page.route('**/api/v1/settings/models', async (route) => {
      await route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify([]),
      });
    });

    await page.route('**/api/v1/settings/model-preferences', async (route) => {
      await route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ provider: 'openai', model: 'gpt-4o' }),
      });
    });

    await page.route('**/api/v1/model-preferences**', async (route) => {
      // The system defaults live under the same path and have their own shape.
      if (route.request().url().includes('/system/defaults')) {
        await route.fulfill({
          status: 200,
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            defaults: [],
            available_providers: ['openai', 'ollama'],
            available_models: { openai: ['gpt-4o'], ollama: ['llama3.3:8b'] },
          }),
        });
        return;
      }
      await route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ items: [], total: 0 }),
      });
    });

    await page.goto('/settings');

    // Wait for notifications section
    await page.getByRole('tab', { name: /^notifications$/i }).click();
    await expect(page.getByRole('heading', { name: /^notifications$/i })).toBeVisible({
      timeout: 15000,
    });

    // Wait for settings to load
    const priceAlertsCheckbox = page.locator('#price_alerts');
    await expect(priceAlertsCheckbox).toBeVisible({ timeout: 10000 });

    // Click Save Preferences (settings are already loaded, just trigger save)
    const saveButton = page.getByRole('button', { name: /save preferences/i });
    await saveButton.click();

    // Should display error message
    await expect(page.getByText(/failed to save settings/i)).toBeVisible({ timeout: 10000 });
  });
});
