import { test, expect } from '@playwright/test';
import { writeFile, mkdir } from 'fs/promises';

test('collect console and network metrics', async ({ page }) => {
  await mkdir('artifacts/test_run_2025-12-09/logs', { recursive: true });
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

  await page.goto('/');
  await page.waitForURL('**/');
  await expect(page.locator('[data-testid="stAppViewBlockContainer"]')).toBeVisible({ timeout: 10000 });

  const tabs = page.locator('.stTabs [data-baseweb="tab"]');
  for (let i = 0; i < await tabs.count(); i++) {
    await tabs.nth(i).click({ force: true });
  }

  const perf = await page.evaluate(() => {
    const nav = performance.getEntriesByType('navigation');
    const res = performance.getEntriesByType('resource');
    return { navigation: nav, resources: res };
  });

  // keep raw logs and performance, omit derived summary for minimal footprint

  await writeFile(
    'artifacts/test_run_2025-12-09/logs/browser_console.json',
    JSON.stringify({ logs }, null, 2)
  );
  await writeFile(
    'artifacts/test_run_2025-12-09/logs/browser_network.json',
    JSON.stringify({ responses }, null, 2)
  );
  await writeFile(
    'artifacts/test_run_2025-12-09/logs/browser_performance.json',
    JSON.stringify(perf, null, 2)
  );
});
