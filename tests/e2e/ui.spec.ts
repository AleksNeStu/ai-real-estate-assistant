import { test, expect } from '@playwright/test';

test.describe('UI Smoke', () => {
  test('home renders and sidebar visible @smoke', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByRole('heading', { level: 1 }).first()).toBeVisible();
    await expect(page.getByTestId('stSidebar')).toBeVisible();
    await page.screenshot({ path: 'artifacts/test_run_2025-12-09/screenshots/home.png', fullPage: true });
  });

  test('load data from default URLs via sidebar @smoke', async ({ page }) => {
    await page.goto('/');
    const dataSources = page.locator('section[data-testid="stSidebar"] summary:has-text("Data Sources")');
    await expect(dataSources).toBeVisible();
    await dataSources.click({ force: true });
    const sidebar = page.locator('section[data-testid="stSidebar"]');
    await sidebar.getByRole('radio', { name: 'URL' }).click({ force: true });
    const ta = sidebar.getByLabel(/Data URLs/);
    await expect(ta).toBeVisible();
    await sidebar.getByRole('button', { name: /Load Data/i }).click({ force: true });
    await page.screenshot({ path: 'artifacts/test_run_2025-12-09/screenshots/data_loaded.png', fullPage: true });
  });

  test('notifications tab shows email inputs @smoke', async ({ page }) => {
    await page.goto('/');
    const tabList = page.locator('.stTabs [data-baseweb="tab"]');
    await tabList.nth(5).click({ force: true });
    await expect(page.locator('section[data-testid="stAppViewBlockContainer"]')).toBeVisible();
    await page.screenshot({ path: 'artifacts/test_run_2025-12-09/screenshots/notifications_inputs.png', fullPage: true });
  });
  test('tabs navigate and render content @smoke', async ({ page }) => {
    await page.goto('/');
    const tabList = page.locator('.stTabs [data-baseweb="tab"]');
    await expect(tabList).toHaveCount(6);

    await tabList.nth(0).click({ force: true });
    await page.screenshot({ path: 'artifacts/test_run_2025-12-09/screenshots/tab_chat.png', fullPage: true });

    await tabList.nth(1).click({ force: true });
    await page.screenshot({ path: 'artifacts/test_run_2025-12-09/screenshots/tab_insights.png', fullPage: true });

    await tabList.nth(2).click({ force: true });
    await page.screenshot({ path: 'artifacts/test_run_2025-12-09/screenshots/tab_compare.png', fullPage: true });

    await tabList.nth(3).click({ force: true });
    await page.screenshot({ path: 'artifacts/test_run_2025-12-09/screenshots/tab_export.png', fullPage: true });

    await tabList.nth(4).click({ force: true });
    await page.screenshot({ path: 'artifacts/test_run_2025-12-09/screenshots/tab_analytics.png', fullPage: true });

    await tabList.nth(5).click({ force: true });
    await page.screenshot({ path: 'artifacts/test_run_2025-12-09/screenshots/tab_notifications.png', fullPage: true });
  });

  test('model configuration expander and provider select @smoke', async ({ page }) => {
    await page.goto('/');
    const expanderSummary = page.locator('section[data-testid="stSidebar"] summary:has-text("Model Configuration")');
    await expect(expanderSummary).toBeVisible();
    await expanderSummary.click({ force: true });
    const expanderContainer = expanderSummary.locator('xpath=ancestor::details');
    let providerSelectAll = expanderContainer.locator('[data-baseweb="select"]');
    const count = await providerSelectAll.count();
    if (count === 0) {
      providerSelectAll = page.locator('section[data-testid="stSidebar"] [data-baseweb="select"]');
    }
    const count2 = await providerSelectAll.count();
    expect(count2).toBeGreaterThan(0);
    await page.screenshot({ path: 'artifacts/test_run_2025-12-09/screenshots/sidebar_model_config.png', fullPage: true });
  });
});
