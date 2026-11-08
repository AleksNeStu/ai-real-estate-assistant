/**
 * i18n locale E2E tests.
 * Tests locale routing, language switcher, and content translation.
 * Uses direct Playwright imports (no auth required for navigation/locale tests).
 */

import { test, expect } from '@playwright/test';

test.describe('i18n Locale Routing', () => {
  test('should redirect root to the detected locale @smoke', async ({ page }) => {
    await page.goto('/');

    // The app detects the locale of the browser (next-intl). The context of
    // Playwright asks for English, so the root leads to a locale prefix -
    // which one depends on the language of the browser.
    await expect(page).toHaveURL(/\/(pl|en|ru|de|es|it|pt|tr|uk)(\/|$)/, { timeout: 10000 });
  });

  test.describe('with a Polish browser', () => {
    test.use({ locale: 'pl-PL' });

    test('should redirect root to the default locale /pl/', async ({ page }) => {
      await page.goto('/');

      await expect(page).toHaveURL(/\/pl(\/|$)/, { timeout: 10000 });
    });
  });

  test('should serve content at /en/ when English locale is requested', async ({ page }) => {
    await page.goto('/en/');

    await expect(page).toHaveURL(/\/en(\/|$)/, { timeout: 10000 });
  });

  test('should serve content at /ru/ when Russian locale is requested', async ({ page }) => {
    await page.goto('/ru/');

    await expect(page).toHaveURL(/\/ru(\/|$)/, { timeout: 10000 });
  });
});

test.describe('Language Switcher', () => {
  test('should display language switcher in the page @smoke', async ({ page }) => {
    await page.goto('/pl/');

    // The LanguageSwitcher renders a ghost button with the current locale flag
    const switcherButton = page.getByRole('button', { name: /change language/i });
    await expect(switcherButton).toBeVisible({ timeout: 10000 });
  });

  test('should show locale options when language switcher is opened', async ({ page }) => {
    await page.goto('/pl/');

    const switcherButton = page.getByRole('button', { name: /change language/i });
    await switcherButton.click();

    // Dropdown should show locale names from localeNames config
    const englishOption = page.getByRole('menuitem', { name: /English/i });
    const russianOption = page.getByRole('menuitem', { name: /Русский/i });

    await expect(englishOption).toBeVisible({ timeout: 5000 });
    await expect(russianOption).toBeVisible({ timeout: 5000 });
  });

  test('should switch to English and update URL', async ({ page }) => {
    await page.goto('/pl/');

    const switcherButton = page.getByRole('button', { name: /change language/i });
    await switcherButton.click();

    const englishOption = page.getByRole('menuitem', { name: /English/i });
    await englishOption.click();

    // URL should now contain /en/
    await expect(page).toHaveURL(/\/en(\/|$)/, { timeout: 10000 });
  });

  test('should switch to Russian and update URL', async ({ page }) => {
    await page.goto('/en/');

    const switcherButton = page.getByRole('button', { name: /change language/i });
    await switcherButton.click();

    const russianOption = page.getByRole('menuitem', { name: /Русский/i });
    await russianOption.click();

    // URL should now contain /ru/
    await expect(page).toHaveURL(/\/ru(\/|$)/, { timeout: 10000 });
  });

  test('should display different content after locale switch', async ({ page }) => {
    // Load the Polish page first
    await page.goto('/pl/');

    // Wait for page to be ready and capture a heading
    const pageHeading = page.locator('h1').first();
    await pageHeading.waitFor({ state: 'visible', timeout: 10000 });
    const polishText = await pageHeading.textContent();

    // Switch to English
    const switcherButton = page.getByRole('button', { name: /change language/i });
    await switcherButton.click();

    const englishOption = page.getByRole('menuitem', { name: /English/i });
    await englishOption.click();

    // Wait for navigation to complete and content to update
    await expect(page).toHaveURL(/\/en(\/|$)/, { timeout: 10000 });

    // The h1 heading text should have changed (translations differ)
    const englishHeading = page.locator('h1').first();
    await englishHeading.waitFor({ state: 'visible', timeout: 10000 });
    const englishText = await englishHeading.textContent();

    // Content should be different after switching locales
    expect(englishText).not.toBe(polishText);
  });
});
