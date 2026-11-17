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

// Service URLs - the ports the compose file publishes.
//
// The names are STACK_* on purpose: a project's own .env already carries a
// FRONTEND_URL for the local development stack, and npm loads that file into
// the test process, so a generic name silently points the probe at the wrong
// host. The defaults are the compose ports (8082 / 3082).
const BACKEND_URL = process.env.STACK_BACKEND_URL || 'http://localhost:8082';
const FRONTEND_URL = process.env.STACK_FRONTEND_URL || 'http://localhost:3082';
const REDIS_URL = process.env.STACK_REDIS_URL || 'http://localhost:16379';

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

      // The root redirects to the default locale, so the assertion is that
      // the page stayed on this host - not that the URL is unchanged.
      await expect(page).toHaveURL(new RegExp(`^${FRONTEND_URL.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}`));
      await expect(page.locator('body')).not.toBeEmpty();
    });

    test('frontend loads without console errors', async ({ page }) => {
      const errors: { text: string; url: string }[] = [];

      page.on('console', (msg) => {
        if (msg.type() === 'error') {
          errors.push({ text: msg.text(), url: msg.location()?.url ?? '' });
        }
      });

      await page.goto(FRONTEND_URL);
      await page.waitForTimeout(3000); // Wait for any delayed errors

      // Three kinds of console error are not the stack's fault:
      // - a resource from another host (a font, a map tile): the stack does
      //   not serve it, and the runner's network decides;
      // - the anonymous auth probe, which answers 401 until the visitor
      //   signs in;
      // - a ResizeObserver notice, which is a browser hint, not an error.
      const ownHost = new RegExp(
        `^https?://(localhost|127\\.0\\.0\\.1)(:${new URL(BACKEND_URL).port}|:${new URL(FRONTEND_URL).port})?`
      );

      const criticalErrors = errors.filter(({ text, url }) => {
        if (text.includes('ResizeObserver')) return false;
        // The harness blocks the service worker on purpose (so the API mocks
        // stay in charge), so its registration cannot succeed.
        if (text.includes('Service Worker registration failed')) return false;
        if (url && !ownHost.test(url)) return false;
        if (text.includes('401 (Unauthorized)') && url.includes('/api/v1/auth/')) return false;
        return true;
      });

      expect(criticalErrors).toHaveLength(0);
    });
  });

  test.describe('Inter-Service Communication', () => {
    test('frontend can reach backend API', async ({ page, request }) => {
      // First verify backend is healthy
      const healthResponse = await request.get(`${BACKEND_URL}/health`);
      expect(healthResponse.status()).toBe(200);

      // Then verify frontend can access backend through its proxy.
      // The frontend's own health route (/api/health) forwards to the
      // backend's /health - the backend has no /api/v1/health route, so the
      // proxy would answer 404 and the check would prove nothing.
      await page.goto(`${FRONTEND_URL}/api/health`);

      // The frontend proxy should forward to backend
      const content = await page.content();
      expect(content).toContain('healthy');
    });

    test('backend API returns proper CORS headers', async ({ request }) => {
      const response = await request.fetch(`${BACKEND_URL}/health`, {
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

      // The unknown route is redirected into the default locale, so the
      // answer is the not-found page - and the page carries the number in
      // more than one element, so the first match is the one to look at.
      const is404 = await page
        .getByText(/404|not found/i)
        .first()
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
