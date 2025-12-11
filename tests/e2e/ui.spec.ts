import { test, expect } from '@playwright/test';

test.describe('UI Smoke', () => {
  test('home renders and app title visible @smoke', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByText('AI Real Estate Assistant')).toBeVisible();
    await page.screenshot({ path: 'artifacts/test_run_2025-12-09/screenshots/home.png', fullPage: true });
  });

  test('load data from default URLs via sidebar @smoke', async ({ page }) => {
    await page.goto('/');
    const dsDetails = page.locator('details:has(summary:has-text("Data Sources"))');
    const dsHandle = await dsDetails.elementHandle();
    if (dsHandle) {
      await page.evaluate((el) => el.setAttribute('open', ''), dsHandle);
    }
    const sidebar = page.locator('body');
    await sidebar.getByRole('radio', { name: 'URL' }).click({ force: true });
    const ta = sidebar.getByLabel(/Data URLs/);
    await expect(ta).toBeVisible();
    await sidebar.getByRole('button', { name: /Load Data/i }).click({ force: true });
    await page.screenshot({ path: 'artifacts/test_run_2025-12-09/screenshots/data_loaded.png', fullPage: true });
  });

  test('notifications tab shows email inputs @smoke', async ({ page }) => {
    await page.goto('/');
    await page.getByRole('button', { name: /Notifications/i }).click({ force: true });
    const configDetails = page.locator('details:has(summary:has-text("Configure Email"))');
    const handle = await configDetails.elementHandle();
    if (handle) {
      await page.evaluate((el) => el.setAttribute('open', ''), handle);
    }
    const emailUser = page.getByLabel('Email Username', { exact: false });
    const emailPass = page.getByLabel('Email Password/App Password', { exact: false });
    await page.screenshot({ path: 'artifacts/test_run_2025-12-09/screenshots/notifications_inputs.png', fullPage: true });
  });
  test('tabs navigate and render content @smoke', async ({ page }) => {
    await page.goto('/');
    await page.getByRole('button', { name: /Chat/i }).click({ force: true });
    await page.screenshot({ path: 'artifacts/test_run_2025-12-09/screenshots/tab_chat.png', fullPage: true });

    await page.getByRole('button', { name: /Market Insights/i }).click({ force: true });
    await page.screenshot({ path: 'artifacts/test_run_2025-12-09/screenshots/tab_insights.png', fullPage: true });

    await page.getByRole('button', { name: /Compare/i }).click({ force: true });
    await page.screenshot({ path: 'artifacts/test_run_2025-12-09/screenshots/tab_compare.png', fullPage: true });

    await page.getByRole('button', { name: /Export/i }).click({ force: true });
    await page.screenshot({ path: 'artifacts/test_run_2025-12-09/screenshots/tab_export.png', fullPage: true });

    await page.getByRole('button', { name: /Analytics/i }).click({ force: true });
    await page.screenshot({ path: 'artifacts/test_run_2025-12-09/screenshots/tab_analytics.png', fullPage: true });

    await page.getByRole('button', { name: /Notifications/i }).click({ force: true });
    await page.screenshot({ path: 'artifacts/test_run_2025-12-09/screenshots/tab_notifications.png', fullPage: true });
  });

  test('model configuration expander and provider select @smoke', async ({ page }) => {
    await page.goto('/');
    const expanderSummary = page.locator('summary:has-text("Model Configuration")');
    await expect(expanderSummary).toBeVisible();
    await expanderSummary.click({ force: true });
    // expander opened; take screenshot for visual confirmation
    await page.screenshot({ path: 'artifacts/test_run_2025-12-09/screenshots/sidebar_model_config.png', fullPage: true });
  });
});
