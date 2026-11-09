import { defineConfig, devices } from '@playwright/test';

const baseURL = process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:3000';
const isCI = !!process.env.CI;
const startWeb =
  (process.env.PLAYWRIGHT_START_WEB || '').toLowerCase() === '1' ||
  (process.env.PLAYWRIGHT_START_WEB || '').toLowerCase() === 'true';

export default defineConfig({
  testDir: './e2e',
  timeout: 60_000,
  // Retry failed tests in CI
  retries: isCI ? 2 : 0,
  // Limit workers in CI to avoid resource issues
  workers: isCI ? 2 : undefined,
  // Reporters: list for console, HTML for artifacts (use a separate folder to avoid conflicts)
  reporter: [
    ['list'],
    ['html', { outputFolder: 'artifacts/e2e-report', open: 'never' }],
    ['json', { outputFile: 'artifacts/e2e-report/results.json' }],
  ],
  use: {
    baseURL,
    // The service worker claims the page on activate (public/sw.js), and a
    // request that goes through a service worker never reaches `page.route()`
    // - every mocked API call would escape to the real network. Blocking the
    // worker keeps the mocks in charge of the API.
    serviceWorkers: 'block',
    // Capture screenshot on failure
    screenshot: 'only-on-failure',
    // Capture video on failure
    video: 'retain-on-failure',
    // Capture trace on failure for debugging
    trace: 'retain-on-failure',
    // Default action timeout
    actionTimeout: 10_000,
    // Navigation timeout
    navigationTimeout: 30_000,
  },
  outputDir: 'artifacts/e2e-output',
  // Configure web server for local development
  webServer: startWeb
    ? {
        command: 'npm --prefix apps/web run dev -- --port 3000',
        url: baseURL,
        reuseExistingServer: !isCI,
        timeout: 120_000,
      }
    : undefined,
  // Test projects for different viewports
  projects: [
    // Desktop Chromium (primary)
    {
      name: 'desktop-chromium',
      use: {
        browserName: 'chromium',
        viewport: { width: 1440, height: 900 },
      },
    },
    // Tablet and mobile projects run in private repo full suite
  ],
  // Fail build on CI if tests use .only
  forbidOnly: isCI,
});
