/**
 * The Top Bar E2E tests.
 *
 * The bar has two variants: the landing one carries the anchors of the
 * landing page, the application one carries the seven links of the app and
 * the More menu. The locale switcher and the theme toggle are in both.
 *
 * The bar is the chrome every page carries, so the assertions name the
 * routes it links to and the labels the catalogue gives it - never the
 * classes of the bar.
 */

import { test, expect } from '@playwright/test';
import { mockLandingApis } from '../mocks';

test.describe('The Top Bar', () => {
  test('the landing bar carries the anchors of the landing page', async ({ page }) => {
    await mockLandingApis(page);
    await page.goto('/en/');

    const nav = page.getByRole('navigation', { name: /main navigation/i });
    await expect(nav.locator('a[href="#features"]')).toBeVisible({ timeout: 15000 });
    await expect(nav.locator('a[href="#data"]')).toBeVisible();
    await expect(nav.locator('a[href="#faq"]')).toBeVisible();

    // The application links are not on the landing.
    await expect(nav.locator('a[href$="/search"]')).toHaveCount(0);
  });

  test('the application bar carries the seven links and the More menu', async ({ page }) => {
    await page.goto('/en/search');

    const nav = page.getByRole('navigation', { name: /main navigation/i });
    for (const route of [
      '/search',
      '/chat',
      '/city-overview',
      '/analytics',
      '/tools',
      '/agents',
      '/knowledge',
    ]) {
      await expect(nav.locator(`a[href$="${route}"]`)).toHaveCount(1);
    }

    // The More menu opens and every row carries the route it opens.
    const more = nav.getByRole('button', { name: /more/i });
    await expect(more).toBeVisible({ timeout: 15000 });
    await more.click();

    for (const route of ['/market-trends', '/cma', '/valuation', '/showcase']) {
      await expect(page.locator(`a[href$="${route}"]`).first()).toBeVisible();
    }
  });

  test('the locale switcher offers the locales', async ({ page }) => {
    await page.goto('/en/search');

    const switcher = page.getByTestId('language-switcher');
    await expect(switcher).toBeVisible({ timeout: 15000 });
    await switcher.click();

    await expect(page.getByRole('menuitem', { name: /English/ })).toBeVisible();
    await expect(page.getByRole('menuitem', { name: /Polski/ })).toBeVisible();
  });

  test('the theme toggle switches the theme', async ({ page }) => {
    await page.goto('/en/search');

    const toggle = page.getByRole('button', { name: /toggle theme/i });
    await expect(toggle).toBeVisible({ timeout: 15000 });

    const isDark = () =>
      page.evaluate(() => document.documentElement.classList.contains('dark'));

    const before = await isDark();
    await toggle.click();
    await expect.poll(isDark).toBe(!before);
  });
});
