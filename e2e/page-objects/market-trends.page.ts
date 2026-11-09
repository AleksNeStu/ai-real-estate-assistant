/**
 * Market Trends Page Object for E2E tests.
 * Encapsulates market-trends page interactions and elements.
 */

import { Page, Locator, expect } from '@playwright/test';

export class MarketTrendsPage {
  readonly page: Page;
  readonly heading: Locator;
  readonly cityInput: Locator;
  readonly intervalSelect: Locator;
  readonly monthsBackInput: Locator;
  readonly applyFiltersButton: Locator;
  readonly indicatorCards: Locator;
  readonly priceTrendsCard: Locator;
  readonly volumeCard: Locator;
  readonly errorMessage: Locator;
  readonly loadingSpinner: Locator;
  readonly hottestAreasCard: Locator;
  readonly mostAffordableCard: Locator;

  constructor(page: Page) {
    this.page = page;
    this.heading = page.getByRole('heading', { name: /market trends/i });
    this.cityInput = page.locator('#city');
    this.intervalSelect = page.locator('#interval');
    this.monthsBackInput = page.locator('#months');
    this.applyFiltersButton = page.getByRole('button', { name: /apply filters/i });
    // The indicators are a ledger of rows, not a grid of cards: one row per
    // indicator, in the panel beside the charts.
    this.indicatorCards = page.locator('[data-testid="indicator-row"]');
    this.priceTrendsCard = page.locator('text=/average and median prices/i').locator('..');
    this.volumeCard = page.locator('text=/listing volume/i').locator('..');
    this.errorMessage = page.locator('[class*="bg-destructive"], [class*="border-destructive"]');
    this.loadingSpinner = page.locator('.animate-spin');
    this.hottestAreasCard = page.locator('text=/hottest areas/i').locator('..');
    this.mostAffordableCard = page.locator('text=/most affordable/i').locator('..');
  }

  /**
   * Navigate to the market trends page.
   */
  async navigate(): Promise<void> {
    await this.page.goto('/market-trends');
    await expect(this.heading).toBeVisible({ timeout: 10000 });
  }

  /**
   * Set the city filter value.
   */
  async setCity(city: string): Promise<void> {
    await this.cityInput.clear();
    await this.cityInput.fill(city);
  }

  /**
   * Select the interval (month/quarter/year).
   */
  async setInterval(interval: 'month' | 'quarter' | 'year'): Promise<void> {
    await this.intervalSelect.click();
    const optionMap: Record<string, string> = {
      month: 'Monthly',
      quarter: 'Quarterly',
      year: 'Yearly',
    };
    await this.page.getByRole('option', { name: optionMap[interval] }).click();
  }

  /**
   * Set the months back value.
   */
  async setMonthsBack(months: number): Promise<void> {
    await this.monthsBackInput.clear();
    await this.monthsBackInput.fill(months.toString());
  }

  /**
   * Click the apply filters button.
   */
  async applyFilters(): Promise<void> {
    await this.applyFiltersButton.click();
  }

  /**
   * Set city and apply filters.
   */
  async filterByCity(city: string): Promise<void> {
    await this.setCity(city);
    await this.applyFilters();
  }

  /**
   * Get the number of indicator rows visible.
   */
  async getIndicatorCardCount(): Promise<number> {
    // The indicator panel carries one row per indicator.
    return await this.indicatorCards.count();
  }

  /**
   * Get the text content of a specific indicator card by label.
   */
  async getIndicatorValue(label: string): Promise<string | null> {
    const card = this.page.locator(`text=/${label}/i`).locator('..');
    if (await card.isVisible()) {
      return await card.textContent();
    }
    return null;
  }

  /**
   * Check if the price trends chart is visible.
   */
  async isPriceTrendsChartVisible(): Promise<boolean> {
    // The recharts container renders inside a div with specific class patterns
    const chartContainer = this.page.locator('.recharts-wrapper').first();
    return await chartContainer.isVisible().catch(() => false);
  }

  /**
   * Check if error state is visible.
   */
  async hasError(): Promise<boolean> {
    return await this.errorMessage.isVisible();
  }

  /**
   * Check if loading spinner is visible.
   */
  async isLoading(): Promise<boolean> {
    return await this.loadingSpinner.isVisible();
  }

  /**
   * Wait for data to load (spinner disappears).
   */
  async waitForLoad(): Promise<void> {
    await expect(this.loadingSpinner).toBeHidden({ timeout: 15000 }).catch(() => {
      // Spinner may have already disappeared
    });
  }
}
