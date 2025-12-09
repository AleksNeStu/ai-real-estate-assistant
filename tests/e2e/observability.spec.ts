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

  const errorsCount = logs.filter(l => l.level === 'error' || l.level === 'pageerror').length;
  const warningsCount = logs.filter(l => l.level === 'warning').length;
  const statusSummary = { '2xx': 0, '3xx': 0, '4xx': 0, '5xx': 0 } as Record<string, number>;
  for (const r of responses) {
    if (r.status >= 500) statusSummary['5xx']++;
    else if (r.status >= 400) statusSummary['4xx']++;
    else if (r.status >= 300) statusSummary['3xx']++;
    else if (r.status >= 200) statusSummary['2xx']++;
  }
  const slowResources = (perf.resources as any[]).filter((e: any) => (e.duration ?? 0) > 500);
  const navigation = (perf.navigation as any[])[0] ?? {};
  const summary = {
    errors: errorsCount,
    warnings: warningsCount,
    statuses: statusSummary,
    slowResourcesCount: slowResources.length,
    navigation: {
      duration: navigation.duration ?? null,
      domContentLoaded: navigation.domContentLoadedEventEnd ?? null,
      loadEventEnd: navigation.loadEventEnd ?? null,
    }
  };

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
  await writeFile(
    'artifacts/test_run_2025-12-09/logs/browser_summary.json',
    JSON.stringify(summary, null, 2)
  );
});
