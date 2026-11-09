/**
 * API response mocks for E2E tests.
 * Provides mock handlers for search, auth, and other API endpoints.
 */

import { Route } from '@playwright/test';
import { TEST_SEARCH_RESULTS } from '../fixtures/properties';
import { TEST_USERS } from '../fixtures/users';

/**
 * Mock search API response with properties.
 *
 * The frontend expects the `SearchResponse` shape of
 * `apps/web/src/lib/types.ts`: `{ results: [{ property, score }], count }`.
 * The older `{ properties, total }` payload was silently ignored, so the
 * results grid never appeared and every search test failed.
 */
export async function mockSearchSuccess(route: Route): Promise<void> {
  await route.fulfill({
    status: 200,
    headers: {
      'Content-Type': 'application/json',
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Expose-Headers': 'X-Request-ID',
      'X-Request-ID': 'req-mock-search-success',
    },
    body: JSON.stringify({
      results: TEST_SEARCH_RESULTS,
      count: TEST_SEARCH_RESULTS.length,
    }),
  });
}

/**
 * Mock empty search results.
 */
export async function mockSearchEmpty(route: Route): Promise<void> {
  await route.fulfill({
    status: 200,
    headers: {
      'Content-Type': 'application/json',
      'Access-Control-Allow-Origin': '*',
      'X-Request-ID': 'req-mock-search-empty',
    },
    body: JSON.stringify({
      results: [],
      count: 0,
    }),
  });
}

/**
 * Mock search API error.
 */
export async function mockSearchError(
  route: Route,
  statusCode?: number,
  message?: string
): Promise<void> {
  // Playwright calls the handler with (route, request) - the second argument is
  // the request object and not the status code.
  const status = typeof statusCode === 'number' ? statusCode : 500;
  const text = typeof message === 'string' ? message : 'Search failed';
  await route.fulfill({
    status,
    headers: {
      'Content-Type': 'application/json',
      'Access-Control-Allow-Origin': '*',
      'X-Request-ID': `req-mock-search-error-${status}`,
    },
    body: JSON.stringify({ detail: text }),
  });
}

/**
 * Mock the property export endpoint. The frontend turns the response into a
 * blob and clicks an anchor with the `download` attribute, so the browser
 * fires a download event only when the response carries a filename.
 */
export async function mockExportSuccess(route: Route): Promise<void> {
  const request = route.request();
  const body = request.postDataJSON() as { format?: string } | null;
  const format = body?.format || 'csv';

  const payload =
    format === 'json'
      ? JSON.stringify(
          TEST_SEARCH_RESULTS.map((item) => item.property),
          null,
          2
        )
      : 'id,title,city,price\nprop-001,Modern 2-Bedroom Apartment in Mitte,Berlin,1200\n';

  await route.fulfill({
    status: 200,
    headers: {
      'Content-Type': format === 'json' ? 'application/json' : 'text/csv',
      'Content-Disposition': `attachment; filename="properties.${format}"`,
      'Access-Control-Allow-Origin': '*',
    },
    body: payload,
  });
}

/**
 * Mock successful registration.
 */
export async function mockRegisterSuccess(route: Route): Promise<void> {
  await route.fulfill({
    status: 201,
    headers: {
      'Content-Type': 'application/json',
      'Access-Control-Allow-Origin': '*',
      'Set-Cookie': 'access_token=mock-access-token; Path=/; HttpOnly',
    },
    body: JSON.stringify({
      user: {
        id: 'new-user-001',
        email: 'newuser@example.com',
        full_name: 'New User',
        role: 'user',
        is_verified: false,
      },
      message: 'Registration successful. Please check your email to verify your account.',
    }),
  });
}

/**
 * Mock successful login.
 * Returns AuthResponse format expected by frontend.
 */
export async function mockLoginSuccess(route: Route): Promise<void> {
  const testUser = TEST_USERS.basic;

  await route.fulfill({
    status: 200,
    headers: {
      'Content-Type': 'application/json',
      'Access-Control-Allow-Origin': '*',
      'Set-Cookie': [
        'access_token=mock-access-token; Path=/; HttpOnly; SameSite=Lax',
        'refresh_token=mock-refresh-token; Path=/; HttpOnly; SameSite=Lax',
      ].join(', '),
    },
    body: JSON.stringify({
      access_token: 'mock-access-token',
      refresh_token: 'mock-refresh-token',
      token_type: 'bearer',
      expires_in: 3600,
      user: {
        id: testUser.id,
        email: testUser.email,
        full_name: testUser.fullName,
        role: testUser.role,
        is_active: true,
        is_verified: testUser.isVerified,
        created_at: new Date().toISOString(),
      },
    }),
  });
}

/**
 * Mock failed login (invalid credentials).
 */
export async function mockLoginError(route: Route): Promise<void> {
  await route.fulfill({
    status: 401,
    headers: {
      'Content-Type': 'application/json',
      'Access-Control-Allow-Origin': '*',
    },
    body: JSON.stringify({
      detail: 'Invalid email or password',
    }),
  });
}

/**
 * Mock successful logout.
 */
export async function mockLogoutSuccess(route: Route): Promise<void> {
  await route.fulfill({
    status: 200,
    headers: {
      'Content-Type': 'application/json',
      'Access-Control-Allow-Origin': '*',
      'Set-Cookie': ['access_token=; Path=/; Max-Age=0', 'refresh_token=; Path=/; Max-Age=0'].join(
        ', '
      ),
    },
    body: JSON.stringify({ message: 'Logged out successfully' }),
  });
}

/**
 * Mock get current user (authenticated).
 */
export async function mockGetCurrentUser(route: Route): Promise<void> {
  const testUser = TEST_USERS.basic;

  await route.fulfill({
    status: 200,
    headers: {
      'Content-Type': 'application/json',
      'Access-Control-Allow-Origin': '*',
    },
    body: JSON.stringify({
      id: testUser.id,
      email: testUser.email,
      full_name: testUser.fullName,
      role: testUser.role,
      is_verified: testUser.isVerified,
    }),
  });
}

/**
 * Mock unauthorized (not logged in).
 */
export async function mockUnauthorized(route: Route): Promise<void> {
  await route.fulfill({
    status: 401,
    headers: {
      'Content-Type': 'application/json',
      'Access-Control-Allow-Origin': '*',
    },
    body: JSON.stringify({ detail: 'Not authenticated' }),
  });
}

/**
 * Setup all auth-related mocks for a page.
 */
export function setupAuthMocks(page: import('@playwright/test').Page): void {
  // Mock login
  page.route('**/api/v1/auth/login', async (route) => {
    const request = route.request();
    if (request.method() === 'OPTIONS') {
      await route.fulfill({ status: 204, headers: { 'Access-Control-Allow-Origin': '*' } });
      return;
    }
    await mockLoginSuccess(route);
  });

  // Mock logout
  page.route('**/api/v1/auth/logout', async (route) => {
    const request = route.request();
    if (request.method() === 'OPTIONS') {
      await route.fulfill({ status: 204, headers: { 'Access-Control-Allow-Origin': '*' } });
      return;
    }
    await mockLogoutSuccess(route);
  });

  // Mock get current user
  page.route('**/api/v1/auth/me', async (route) => {
    const request = route.request();
    if (request.method() === 'OPTIONS') {
      await route.fulfill({ status: 204, headers: { 'Access-Control-Allow-Origin': '*' } });
      return;
    }
    await mockGetCurrentUser(route);
  });
}

/**
 * Mock the calls the landing makes when it loads.
 *
 * The landing asks the API for the catalogue counts, for what the deployment
 * can do, for a live slice of the catalogue and for the waitlist state.
 * Without a backend those requests hang - the proxy waits for an address
 * that never answers - and the page never reaches `networkidle`, so every
 * test that waits for it times out on a page that is in fact fine.
 *
 * The shapes are the ones the application serves: `CatalogueStatsResponse`
 * for the counts, the capabilities dict for the state, the `SearchResponse`
 * for the slice.
 */
export async function mockLandingApis(page: import('@playwright/test').Page): Promise<void> {
  await page.route('**/api/v1/search', async (route) => {
    if (route.request().method() === 'OPTIONS') {
      await route.fulfill({ status: 204, headers: { 'Access-Control-Allow-Origin': '*' } });
      return;
    }
    await mockSearchSuccess(route);
  });

  await page.route('**/api/v1/catalogue/stats', async (route) => {
    await route.fulfill({
      status: 200,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        total: 250,
        agents: 15,
        cities: [
          { name: 'Kraków', count: 62 },
          { name: 'Warsaw', count: 58 },
          { name: 'Gdańsk', count: 47 },
          { name: 'Wrocław', count: 44 },
          { name: 'Poznań', count: 39 },
        ],
        currencies: ['PLN'],
      }),
    });
  });

  await page.route('**/api/v1/capabilities', async (route) => {
    await route.fulfill({
      status: 200,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        auth: { jwt_enabled: true, demo_user_bypass: false, oauth: { google: false, apple: false } },
        email: { enabled: false, provider: 'dummy' },
        llm: { demo_mode: true, mode: 'local-model', provider: 'minimax', model: 'MiniMax-M3.1-Flash' },
        lead_capture: { waitlist_enabled: false },
        observability: { error_tracking: false },
      }),
    });
  });

  await page.route('**/api/v1/leads/visitor', async (route) => {
    if (route.request().method() === 'OPTIONS') {
      await route.fulfill({ status: 204, headers: { 'Access-Control-Allow-Origin': '*' } });
      return;
    }
    await route.fulfill({
      status: 200,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        id: 'lead-mock-visitor',
        visitor_id: 'visitor-mock',
        email: null,
        phone: null,
        name: null,
        status: 'new',
        source: 'propvector_waitlist',
        created_at: new Date().toISOString(),
      }),
    });
  });

  await page.route('**/api/v1/leads/track', async (route) => {
    await route.fulfill({
      status: 200,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ tracked: true }),
    });
  });
}
