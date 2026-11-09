/**
 * Integration E2E tests for cross-feature flows.
 * Tests that span multiple features to ensure they work together correctly.
 */

import { test, expect } from '../conftest';
import { mockChatSuccess } from '../mocks/llm.mock';
import { mockSearchSuccess } from '../mocks/api.mock';
import { generateUniqueEmail } from '../fixtures/users';

test.describe('Integration Flows', () => {
  // Setup authentication for all tests
  test.beforeEach(async ({ page }) => {
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
  });

  test.describe('Search to Favorite Flow', () => {
    test('should search, view, and add property to favorites @integration', async ({ page }) => {
      // Setup mocks
      await page.route('**/api/v1/search*', mockSearchSuccess);

      // 1. Search for properties
      await page.goto('/search');
      const searchInput = page.getByLabel('Search query');
      await searchInput.fill('apartment in Berlin');
      await page.getByTestId('search-submit').click();

      // Wait for results
      await expect(
        page.locator('[data-testid="property-card"], .property-card').first()
      ).toBeVisible({ timeout: 10000 });

      // 2. Click on a property to view details
      const propertyCard = page.locator('[data-testid="property-card"], .property-card').first();
      await propertyCard.click();

      // 3. Add to favorites
      const favoriteButton = page.getByTestId('favorite-toggle').first();
      if (await favoriteButton.isVisible()) {
        // Mock favorites API
        await page.route('**/api/v1/favorites*', async (route) => {
          const request = route.request();
          if (request.method() === 'POST') {
            await route.fulfill({
              status: 201,
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                id: 'fav-001',
                property_id: 'prop-001',
                created_at: new Date().toISOString(),
              }),
            });
          } else if (request.method() === 'GET') {
            await route.fulfill({
              status: 200,
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                favorites: [{ id: 'fav-001', property_id: 'prop-001' }],
              }),
            });
          }
        });

        await favoriteButton.click();

        // Verify it was added to favorites
        await expect(favoriteButton).toHaveAttribute('aria-pressed', 'true');
      }
    });

    test('should verify favorite appears in favorites list @integration', async ({ page }) => {
      // Setup mocks
      await page.route('**/api/v1/auth/me', async (route) => {
        await route.fulfill({
          status: 200,
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            id: 'test-user-001',
            email: 'test@example.com',
          }),
        });
      });

      await page.route('**/api/v1/favorites*', async (route) => {
        await route.fulfill({
          status: 200,
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            items: [
              {
                id: 'fav-001',
                user_id: 'test-user-001',
                property_id: 'prop-001',
                created_at: new Date().toISOString(),
                updated_at: new Date().toISOString(),
                property: {
                  id: 'prop-001',
                  title: 'Modern 2-Bedroom Apartment in Mitte',
                  city: 'Berlin',
                  property_type: 'apartment',
                  listing_type: 'rent',
                  price: 1200,
                  currency: 'EUR',
                  has_parking: false,
                  has_garden: false,
                  has_pool: false,
                  has_garage: false,
                  has_bike_room: false,
                },
              },
            ],
            total: 1,
            unavailable_count: 0,
          }),
        });
      });

      // Navigate to favorites page
      await page.goto('/favorites');

      // Verify favorite is displayed
      const favoriteCard = page
        .locator('[data-testid="property-card"], .favorite-card, .property-card')
        .first();
      await expect(favoriteCard).toBeVisible({ timeout: 5000 });
    });
  });

  test.describe('Chat to Property Flow', () => {
    test('should chat about properties and navigate to details @integration', async ({ page }) => {
      // Setup mocks
      await page.route('**/api/v1/chat*', mockChatSuccess);
      await page.route('**/api/v1/auth/me', async (route) => {
        await route.fulfill({
          status: 200,
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            id: 'test-user-001',
            email: 'test@example.com',
          }),
        });
      });

      // 1. Start a chat
      await page.goto('/chat');
      const chatInput = page.getByLabel(/chat message input/i);
      await expect(chatInput).toBeVisible({ timeout: 10000 });

      // 2. Send a message
      await chatInput.fill('Find me a 2-bedroom apartment in Berlin');
      await page.getByTestId('chat-send').click();

      // 3. Wait for response
      const assistantMessage = page.locator('div.w-full.items-start.bg-background').first();
      await expect(assistantMessage).toBeVisible({ timeout: 15000 });
    });
  });

  test.describe('Lead Capture Flow', () => {
    test('should track visitor behavior and link to user on registration @integration', async ({
      page,
    }) => {
      const email = generateUniqueEmail();

      // Mock visitor tracking
      await page.route('**/api/v1/leads/visitor', async (route) => {
        await route.fulfill({
          status: 200,
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            visitor_id: 'visitor-001',
            is_new: true,
          }),
        });
      });

      // Mock lead tracking
      await page.route('**/api/v1/leads/track', async (route) => {
        await route.fulfill({
          status: 200,
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ success: true }),
        });
      });

      // 1. Visit the site (triggers visitor creation)
      await page.goto('/');

      // 2. Browse properties
      await page.goto('/search');
      await page.waitForTimeout(500); // Simulate browsing time

      // 3. View a property
      await page.goto('/property/1');
      await page.waitForTimeout(500); // Simulate reading

      // 4. Register
      await page.goto('/auth/register');

      // Mock registration
      await page.route('**/api/v1/auth/register', async (route) => {
        await route.fulfill({
          status: 201,
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            user: {
              id: 'user-001',
              email,
              full_name: 'New User',
            },
          }),
        });
      });

      // Fill and submit registration. The name has to match exactly: the
      // footer carries a newsletter field labelled "Email address" as well.
      const emailInput = page.getByLabel('Email', { exact: true });
      const passwordInput = page.getByLabel('Password', { exact: true });
      const submitButton = page.getByRole('button', { name: /create account|sign up|register/i });
      // The form refuses to submit without the consent - the backend writes
      // `gdpr_consent_at` from it.
      const consentCheckbox = page.locator('#consent, input[name="consent"]');

      await emailInput.fill(email);
      await passwordInput.fill('TestPassword123!');
      await consentCheckbox.check();
      await submitButton.click();

      // Should redirect after registration
      await expect(page).toHaveURL(/^(?!.*\/auth\/register).*$/, { timeout: 10000 });
    });
  });

  test.describe('Settings Persistence Flow', () => {
    test('should save and persist user settings @integration', async ({ page }) => {
      // Mock authenticated state
      await page.route('**/api/v1/auth/me', async (route) => {
        await route.fulfill({
          status: 200,
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            id: 'test-user-001',
            email: 'test@example.com',
          }),
        });
      });

      // Mock settings
      let savedSettings: Record<string, unknown> = {};
      await page.route('**/api/v1/settings*', async (route) => {
        const request = route.request();

        if (request.method() === 'GET') {
          await route.fulfill({
            status: 200,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(savedSettings),
          });
        } else if (request.method() === 'PUT' || request.method() === 'PATCH') {
          const rawBody = await request.postData();
          const settingsBody = rawBody ? JSON.parse(rawBody) : {};
          savedSettings = { ...savedSettings, ...settingsBody };
          await route.fulfill({
            status: 200,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(savedSettings),
          });
        }
      });

      // 1. Navigate to settings
      await page.goto('/settings');

      // 2. Change a setting (e.g., toggle notifications)
      const notificationToggle = page.getByRole('switch', { name: /notification|email/i });
      if (await notificationToggle.isVisible()) {
        await notificationToggle.click();

        // Wait for save
        await page.waitForTimeout(1000);

        // 3. Reload page
        await page.reload();

        // 4. Verify setting persisted
        await expect(notificationToggle).toBeChecked();
      }
    });
  });

  test.describe('Lead Scoring Flow', () => {
    test('should display leads with scores and allow assignment @integration', async ({ page }) => {
      // Mock authenticated state
      await page.route('**/api/v1/auth/me', async (route) => {
        await route.fulfill({
          status: 200,
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            id: 'test-user-001',
            email: 'test@example.com',
            role: 'admin',
          }),
        });
      });

      // Mock leads list with scores
      await page.route('**/api/v1/leads*', async (route) => {
        await route.fulfill({
          status: 200,
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            items: [
              {
                id: 'lead-001',
                visitor_id: 'visitor-001',
                email: 'high.value@example.com',
                name: 'High Value Lead',
                status: 'new',
                total_score: 92,
                current_score: 92,
                source: 'organic',
                created_at: new Date().toISOString(),
                last_activity_at: new Date().toISOString(),
              },
              {
                id: 'lead-002',
                visitor_id: 'visitor-002',
                email: 'medium.value@example.com',
                name: 'Medium Value Lead',
                status: 'contacted',
                total_score: 65,
                current_score: 65,
                source: 'referral',
                phone: '+1234567890',
                created_at: new Date().toISOString(),
                last_activity_at: new Date().toISOString(),
              },
            ],
            total: 2,
            page: 1,
            page_size: 50,
            total_pages: 1,
          }),
        });
      });

      // Mock scoring statistics
      await page.route('**/api/v1/leads/scores/statistics*', async (route) => {
        await route.fulfill({
          status: 200,
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            total_leads: 100,
            avg_score: 55.5,
            high_value_leads: 15,
            conversion_rate: 0.25,
            converted_leads: 25,
            new_leads_24h: 10,
            score_distribution: {
              high_80_100: 15,
              medium_50_79: 25,
              low_0_49: 60,
            },
            scores_calculated_today: 20,
            model_version: '1.0.0',
            weights: {
              search_activity: 0.3,
              property_views: 0.25,
              engagement: 0.25,
              recency: 0.2,
            },
          }),
        });
      });

      // Mock high value leads
      await page.route('**/api/v1/leads/high-value*', async (route) => {
        await route.fulfill({
          status: 200,
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify([
            {
              id: 'lead-001',
              visitor_id: 'visitor-001',
              email: 'high.value@example.com',
              name: 'High Value Lead',
              status: 'new',
              total_score: 92,
              current_score: 92,
              source: 'organic',
              created_at: new Date().toISOString(),
              last_activity_at: new Date().toISOString(),
            },
          ]),
        });
      });

      // 1. Navigate to leads dashboard
      await page.goto('/leads');

      // 2. Verify dashboard loads with statistics
      await expect(page.getByRole('heading', { name: /lead dashboard/i })).toBeVisible({
        timeout: 10000,
      });

      // 3. Verify leads are displayed with scores
      await expect(page.getByText('High Value Lead', { exact: true })).toBeVisible({
        timeout: 10000,
      });
      await expect(page.locator('text=92').first()).toBeVisible(); // Score badge

      // 4. Verify statistics cards
      await expect(page.getByRole('heading', { name: /total leads/i })).toBeVisible();
      await expect(page.getByText('100', { exact: true }).first()).toBeVisible();
    });

    test('should filter leads by status @integration', async ({ page }) => {
      // Mock authenticated state
      await page.route('**/api/v1/auth/me', async (route) => {
        await route.fulfill({
          status: 200,
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            id: 'test-user-001',
            email: 'test@example.com',
          }),
        });
      });

      // Mock leads with different statuses
      await page.route('**/api/v1/leads*', async (route) => {
        const url = new URL(route.request().url());
        const status = url.searchParams.get('status');

        const allLeads = [
          { id: 'lead-1', name: 'New Lead', status: 'new', email: 'new@test.com', total_score: 50 },
          {
            id: 'lead-2',
            name: 'Contacted Lead',
            status: 'contacted',
            email: 'contacted@test.com',
            total_score: 60,
          },
          {
            id: 'lead-3',
            name: 'Qualified Lead',
            status: 'qualified',
            email: 'qualified@test.com',
            total_score: 80,
          },
        ];

        const filteredLeads = status ? allLeads.filter((l) => l.status === status) : allLeads;

        await route.fulfill({
          status: 200,
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            items: filteredLeads.map((l) => ({
              ...l,
              visitor_id: `visitor-${l.id}`,
              current_score: l.total_score,
              created_at: new Date().toISOString(),
              last_activity_at: new Date().toISOString(),
            })),
            total: filteredLeads.length,
            page: 1,
            page_size: 50,
            total_pages: 1,
          }),
        });
      });

      await page.route('**/api/v1/leads/scores/statistics*', async (route) => {
        await route.fulfill({
          status: 200,
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            total_leads: 3,
            avg_score: 63.3,
            high_value_leads: 1,
            conversion_rate: 0.33,
            converted_leads: 1,
            new_leads_24h: 1,
            score_distribution: { high_80_100: 1, medium_50_79: 1, low_0_49: 1 },
            scores_calculated_today: 3,
            model_version: '1.0.0',
            weights: { search_activity: 0.3, property_views: 0.25, engagement: 0.25, recency: 0.2 },
          }),
        });
      });

      await page.route('**/api/v1/leads/high-value*', async (route) => {
        await route.fulfill({
          status: 200,
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify([]),
        });
      });

      await page.goto('/leads');

      // Verify tab navigation exists
      await expect(page.getByRole('tab', { name: /all leads/i })).toBeVisible({ timeout: 10000 });
      await expect(page.getByRole('tab', { name: /new/i })).toBeVisible();

      // Click on New tab to filter
      await page.getByRole('tab', { name: /new/i }).click();

      // Should show only new leads
      await expect(page.locator('text=New Lead')).toBeVisible({ timeout: 5000 });
    });

    test('should recalculate lead scores @integration', async ({ page }) => {
      // Mock authenticated state
      await page.route('**/api/v1/auth/me', async (route) => {
        await route.fulfill({
          status: 200,
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            id: 'test-user-001',
            email: 'test@example.com',
            role: 'admin',
          }),
        });
      });

      let recalculateCalled = false;

      // Mock leads list
      await page.route('**/api/v1/leads*', async (route) => {
        await route.fulfill({
          status: 200,
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            items: [
              {
                id: 'lead-001',
                visitor_id: 'visitor-001',
                email: 'test@example.com',
                name: 'Test Lead',
                status: 'new',
                total_score: 75,
                current_score: 75,
                created_at: new Date().toISOString(),
                last_activity_at: new Date().toISOString(),
              },
            ],
            total: 1,
            page: 1,
            page_size: 50,
            total_pages: 1,
          }),
        });
      });

      // Mock statistics
      await page.route('**/api/v1/leads/scores/statistics*', async (route) => {
        await route.fulfill({
          status: 200,
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            total_leads: 1,
            avg_score: 75,
            high_value_leads: 0,
            conversion_rate: 0,
            converted_leads: 0,
            new_leads_24h: 1,
            score_distribution: { high_80_100: 0, medium_50_79: 1, low_0_49: 0 },
            scores_calculated_today: 1,
            model_version: '1.0.0',
            weights: { search_activity: 0.3, property_views: 0.25, engagement: 0.25, recency: 0.2 },
          }),
        });
      });

      // Mock high value leads
      await page.route('**/api/v1/leads/high-value*', async (route) => {
        await route.fulfill({
          status: 200,
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify([]),
        });
      });

      // Mock recalculate endpoint
      await page.route('**/api/v1/leads/scores/recalculate*', async (route) => {
        if (route.request().method() === 'POST') {
          recalculateCalled = true;
          await route.fulfill({
            status: 200,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: 'Scores recalculated', updated_count: 1 }),
          });
        }
      });

      await page.goto('/leads');

      // Find and click recalculate button
      const recalcButton = page.getByRole('button', { name: /recalculate scores/i });
      await expect(recalcButton).toBeVisible({ timeout: 10000 });
      await recalcButton.click();

      // Verify recalculate was called
      await page.waitForTimeout(1000);
      expect(recalculateCalled).toBe(true);
    });
  });
});
