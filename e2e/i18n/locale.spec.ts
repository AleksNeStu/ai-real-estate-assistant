/**
 * i18n locale E2E tests.
 * Tests locale routing, language switcher, and content translation.
 * Uses direct Playwright imports (no auth required for navigation/locale tests).
 */

import { test, expect } from '@playwright/test';

/**
 * The nine languages the product claims.
 *
 * The catalogues of all nine are checked for parity by a unit test, but a
 * catalogue can be complete and still break at runtime: a missing ICU
 * plural, a key the component reads in one place and not in another. Only
 * English, Polish and Russian were ever rendered in a browser; the other
 * six were never seen by anything but a JSON parser.
 */
const THE_NINE = ['pl', 'en', 'ru', 'de', 'es', 'it', 'pt', 'tr', 'uk'];

test.describe('every language is a page', () => {
  for (const locale of THE_NINE) {
    test(`the landing renders in ${locale}`, async ({ page }) => {
      const errors: string[] = [];
      page.on('pageerror', (error) => errors.push(String(error)));

      await page.goto(`/${locale}/`);

      await expect(page.locator('h1').first()).toBeVisible({ timeout: 15000 });
      await expect(page.locator('html')).toHaveAttribute('lang', locale);

      const heading = (await page.locator('h1').first().textContent()) ?? '';
      expect(heading.trim().length).toBeGreaterThan(0);
      // A key that the catalogue does not carry is printed as the key
      // itself - "landing.hero.title" on the page.
      expect(heading).not.toMatch(/^[a-z]+\.[a-zA-Z.]+$/);
      expect(errors).toEqual([]);
    });
  }
});

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
    const switcherButton = page.getByTestId('language-switcher');
    await expect(switcherButton).toBeVisible({ timeout: 10000 });
  });

  test('should show locale options when language switcher is opened', async ({ page }) => {
    await page.goto('/pl/');

    const switcherButton = page.getByTestId('language-switcher');
    await switcherButton.click();

    // Dropdown should show locale names from localeNames config
    const englishOption = page.getByRole('menuitem', { name: /English/i });
    const russianOption = page.getByRole('menuitem', { name: /Русский/i });

    await expect(englishOption).toBeVisible({ timeout: 5000 });
    await expect(russianOption).toBeVisible({ timeout: 5000 });
  });

  test('should switch to English and update URL', async ({ page }) => {
    await page.goto('/pl/');

    const switcherButton = page.getByTestId('language-switcher');
    await switcherButton.click();

    const englishOption = page.getByRole('menuitem', { name: /English/i });
    await englishOption.click();

    // URL should now contain /en/
    await expect(page).toHaveURL(/\/en(\/|$)/, { timeout: 10000 });
  });

  test('should switch to Russian and update URL', async ({ page }) => {
    await page.goto('/en/');

    const switcherButton = page.getByTestId('language-switcher');
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
    const switcherButton = page.getByTestId('language-switcher');
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
