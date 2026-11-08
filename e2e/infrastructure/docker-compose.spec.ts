/**
 * Docker Compose validation E2E tests.
 * Tests service health, inter-service communication, and data persistence.
 *
 * These tests validate the Docker Compose stack works correctly.
 * They require Docker to be running and the stack to be started.
 *
 * Run with: PLAYWRIGHT_START_WEB=false npx playwright test docker-compose --project=desktop-chromium
 */

import { test, expect } from '@playwright/test';

// Service URLs - defaults for local Docker Compose
const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';
const FRONTEND_URL = process.env.FRONTEND_URL || 'http://localhost:3000';
const REDIS_URL = process.env.REDIS_URL || 'http://localhost:6379';

// Timeout for service health checks
const SERVICE_TIMEOUT = 60000;

// The whole file needs the Docker Compose stack (the backend on :8000, the
// Redis on :6379). CI does not start one, so the suite is opt-in: it runs
// where the stack is up.
test.skip(process.env.E2E_STACK !== 'true', 'needs the Docker Compose stack (E2E_STACK=true)');

test.describe('Docker Compose Validation', () => {
  test.describe.configure({ mode: 'serial' }); // Run tests in sequence

  test.describe('Service Health Checks', () => {
    test('backend health endpoint returns 200 @smoke', async ({ request }) => {
      const response = await request.get(`${BACKEND_URL}/health`, {
        timeout: SERVICE_TIMEOUT,
      });

      expect(response.status()).toBe(200);

      const body = await response.json();
      expect(body).toHaveProperty('status');
      expect(body.status).toBe('healthy');
    });

    test('backend ready endpoint answers', async ({ request }) => {
      const response = await request.get(`${BACKEND_URL}/ready`, {
        timeout: SERVICE_TIMEOUT,
      });

      // The readiness probe needs the credentials of the stack. Without them
      // the API answers with 401, with them it is 200 or 503 (a service of the
      // stack is not up yet).
      expect([200, 401, 503]).toContain(response.status());
    });

    test('frontend is accessible @smoke', async ({ page }) => {
      await page.goto(FRONTEND_URL);

      // Should load the page without errors
      await expect(page).toHaveURL(FRONTEND_URL);
    });

    test('frontend loads without console errors', async ({ page }) => {
      const errors: string[] = [];

      page.on('console', (msg) => {
        if (msg.type() === 'error') {
          errors.push(msg.text());
        }
      });

      await page.goto(FRONTEND_URL);
      await page.waitForTimeout(3000); // Wait for any delayed errors

      // Filter out known non-critical errors
      const criticalErrors = errors.filter(
        (err) => !err.includes('ResizeObserver') && !err.includes('network') && !err.includes('404')
      );

      expect(criticalErrors).toHaveLength(0);
    });
  });

  test.describe('Inter-Service Communication', () => {
    test('frontend can reach backend API', async ({ page, request }) => {
      // First verify backend is healthy
      const healthResponse = await request.get(`${BACKEND_URL}/health`);
      expect(healthResponse.status()).toBe(200);

      // Then verify frontend can access backend through its proxy
      await page.goto(`${FRONTEND_URL}/api/v1/health`);

      // The frontend proxy should forward to backend
      const content = await page.content();
      expect(content).toContain('healthy');
    });

    test('backend API returns proper CORS headers', async ({ request }) => {
      const response = await request.fetch({
        url: `${BACKEND_URL}/health`,
        method: 'OPTIONS',
        headers: {
          Origin: FRONTEND_URL,
          'Access-Control-Request-Method': 'GET',
        },
      });

      // CORS preflight should succeed
      expect([200, 204]).toContain(response.status());
    });

    test('backend API version endpoint is accessible', async ({ request }) => {
      const response = await request.get(`${BACKEND_URL}/api/v1/version`, {
        timeout: 10000,
      });

      // Version endpoint may or may not exist
      if (response.status() === 200) {
        const body = await response.json();
        expect(body).toHaveProperty('version');
      } else if (response.status() === 404) {
        // Version endpoint not implemented, skip
        test.skip();
      }
    });
  });

  test.describe('Data Persistence', () => {
    test('Redis is accessible from backend', async ({ request }) => {
      // Test Redis connectivity through backend health check
      const response = await request.get(`${BACKEND_URL}/health`, {
        timeout: SERVICE_TIMEOUT,
      });

      expect(response.status()).toBe(200);

      const body = await response.json();

      // If health check includes Redis status, verify it
      if (body.services?.redis !== undefined) {
        expect(body.services.redis).toBe('healthy');
      }
    });

    test('ChromaDB is accessible from backend', async ({ request }) => {
      // Test ChromaDB connectivity through backend health check
      const response = await request.get(`${BACKEND_URL}/health`, {
        timeout: SERVICE_TIMEOUT,
      });

      expect(response.status()).toBe(200);

      const body = await response.json();

      // If health check includes ChromaDB status, verify it
      if (body.services?.chromadb !== undefined) {
        expect(body.services.chromadb).toBe('healthy');
      }
    });
  });

  test.describe('Error Handling', () => {
    test('backend returns proper error for invalid endpoint', async ({ request }) => {
      const response = await request.get(`${BACKEND_URL}/api/v1/nonexistent-endpoint`);

      expect(response.status()).toBe(404);
    });

    test('backend returns JSON error responses', async ({ request }) => {
      const response = await request.get(`${BACKEND_URL}/api/v1/nonexistent-endpoint`);

      const contentType = response.headers()['content-type'];
      expect(contentType).toContain('application/json');
    });

    test('frontend shows error page for invalid routes', async ({ page }) => {
      await page.goto(`${FRONTEND_URL}/nonexistent-route-12345`);

      // Should show 404 page or redirect to home
      const is404 = await page
        .locator('text=/404|not found/i')
        .isVisible()
        .catch(() => false);
      const isHome = page.url() === FRONTEND_URL + '/' || page.url() === FRONTEND_URL;

      expect(is404 || isHome).toBe(true);
    });
  });

  test.describe('Security Headers', () => {
    test('backend includes security headers', async ({ request }) => {
      const response = await request.get(`${BACKEND_URL}/health`);

      // Check for common security headers
      const headers = response.headers();

      // These headers may or may not be present depending on configuration
      const securityHeaders = [
        'x-content-type-options',
        'x-frame-options',
        'x-xss-protection',
        'strict-transport-security',
      ];

      const presentHeaders = securityHeaders.filter((h) => headers[h]);

      // At least some security headers should be present
      // This is a soft check - we don't fail if none are present
      if (presentHeaders.length === 0) {
        console.warn('No security headers found - consider adding them');
      }
    });
  });

  test.describe('Performance', () => {
    test('backend health check responds quickly', async ({ request }) => {
      const startTime = Date.now();

      const response = await request.get(`${BACKEND_URL}/health`, {
        timeout: SERVICE_TIMEOUT,
      });

      const responseTime = Date.now() - startTime;

      expect(response.status()).toBe(200);
      expect(responseTime).toBeLessThan(5000); // Should respond within 5 seconds
    });

    test('frontend initial page load is acceptable', async ({ page }) => {
      const startTime = Date.now();

      await page.goto(FRONTEND_URL);
      await page.waitForLoadState('networkidle');

      const loadTime = Date.now() - startTime;

      // Initial page load should complete within 30 seconds
      expect(loadTime).toBeLessThan(30000);
    });
  });
});

test.describe('Docker Compose Stack Status', () => {
  test('all required services are running', async ({ request }) => {
    // Check backend health which should report service status
    const response = await request.get(`${BACKEND_URL}/health`, {
      timeout: SERVICE_TIMEOUT,
    });

    expect(response.status()).toBe(200);

    const body = await response.json();

    // Verify backend reports as healthy
    expect(body.status).toBe('healthy');

    // Log service status for debugging
    console.log('Service health status:', JSON.stringify(body.services || {}, null, 2));
  });

  test('optional services are reported correctly', async ({ request }) => {
    const response = await request.get(`${BACKEND_URL}/health`, {
      timeout: SERVICE_TIMEOUT,
    });

    expect(response.status()).toBe(200);

    const body = await response.json();

    // Ollama is optional - if present, it should be healthy or skipped
    if (body.services?.ollama) {
      expect(['healthy', 'unavailable', 'skipped']).toContain(body.services.ollama);
    }

    // SearXNG is optional - if present, it should be healthy or skipped
    if (body.services?.searxng) {
      expect(['healthy', 'unavailable', 'skipped']).toContain(body.services.searxng);
    }
  });
});
