/**
 * Tools Page Object for E2E tests.
 * Encapsulates tools page interactions and elements for mortgage calculator,
 * property comparison, and neighborhood quality tools.
 */

import { Page, Locator, expect } from '@playwright/test';

export class ToolsPage {
  readonly page: Page;
  readonly heading: Locator;

  // Mortgage calculator elements
  readonly mortgageSection: Locator;
  readonly mortgagePropertyPriceInput: Locator;
  readonly mortgageDownPaymentInput: Locator;
  readonly mortgageInterestRateInput: Locator;
  readonly mortgageLoanYearsInput: Locator;
  readonly mortgageCalculateButton: Locator;
  readonly mortgageResult: Locator;
  readonly mortgageError: Locator;

  // Compare properties elements
  readonly compareSection: Locator;
  readonly compareIdsInput: Locator;
  readonly compareButton: Locator;
  readonly compareResult: Locator;
  readonly compareError: Locator;

  // Neighborhood quality elements
  readonly neighborhoodSection: Locator;
  readonly neighborhoodPropertyIdInput: Locator;
  readonly neighborhoodLatInput: Locator;
  readonly neighborhoodLonInput: Locator;
  readonly neighborhoodCityInput: Locator;
  readonly neighborhoodAnalyzeButton: Locator;
  readonly neighborhoodResult: Locator;
  readonly neighborhoodError: Locator;

  constructor(page: Page) {
    this.page = page;
    this.heading = page.getByRole('heading', { name: /^tools$/i });

    // Mortgage calculator
    this.mortgageSection = page.locator('section').filter({ hasText: /mortgage calculator/i });
    this.mortgagePropertyPriceInput = this.mortgageSection.getByPlaceholder(/property price/i);
    this.mortgageDownPaymentInput = this.mortgageSection.getByPlaceholder(/down payment/i);
    this.mortgageInterestRateInput = this.mortgageSection.getByPlaceholder(/interest rate/i);
    this.mortgageLoanYearsInput = this.mortgageSection.getByPlaceholder(/loan years/i);
    this.mortgageCalculateButton = this.mortgageSection.getByRole('button', {
      name: /^calculate$/i,
    });
    this.mortgageResult = this.mortgageSection.locator('text=/monthly payment:/i');
    this.mortgageError = this.mortgageSection.locator('p.text-destructive');

    // Compare properties
    this.compareSection = page.locator('section').filter({ hasText: /compare properties/i });
    this.compareIdsInput = this.compareSection.getByPlaceholder(/ids comma-separated/i);
    this.compareButton = this.compareSection.getByRole('button', { name: /^compare$/i });
    this.compareResult = this.compareSection.locator('text=/count:/i');
    this.compareError = this.compareSection.locator('p.text-destructive');

    // Neighborhood quality
    this.neighborhoodSection = page.locator('section').filter({ hasText: /neighborhood quality/i });
    this.neighborhoodPropertyIdInput = this.neighborhoodSection
      .getByPlaceholder(/property id/i)
      .first();
    this.neighborhoodLatInput = this.neighborhoodSection.getByPlaceholder(/latitude/i);
    this.neighborhoodLonInput = this.neighborhoodSection.getByPlaceholder(/longitude/i);
    this.neighborhoodCityInput = this.neighborhoodSection.getByPlaceholder(/^city/i);
    this.neighborhoodAnalyzeButton = this.neighborhoodSection.getByRole('button', {
      name: /^analyze$/i,
    });
    this.neighborhoodResult = this.neighborhoodSection.locator('text=/overall score:/i');
    this.neighborhoodError = this.neighborhoodSection.locator('p.text-destructive');
  }

  /**
   * Navigate to the tools page.
   */
  async navigate(): Promise<void> {
    await this.page.goto('/tools');
    await expect(this.heading).toBeVisible({ timeout: 10000 });
  }

  /**
   * Fill the mortgage calculator form with the given values.
   */
  async fillMortgageForm(input: {
    propertyPrice: string;
    downPaymentPercent?: string;
    interestRate?: string;
    loanYears?: string;
  }): Promise<void> {
    await this.mortgagePropertyPriceInput.fill(input.propertyPrice);
    if (input.downPaymentPercent !== undefined) {
      await this.mortgageDownPaymentInput.clear();
      await this.mortgageDownPaymentInput.fill(input.downPaymentPercent);
    }
    if (input.interestRate !== undefined) {
      await this.mortgageInterestRateInput.clear();
      await this.mortgageInterestRateInput.fill(input.interestRate);
    }
    if (input.loanYears !== undefined) {
      await this.mortgageLoanYearsInput.clear();
      await this.mortgageLoanYearsInput.fill(input.loanYears);
    }
  }

  /**
   * Click the mortgage calculate button.
   */
  async calculateMortgage(): Promise<void> {
    await this.mortgageCalculateButton.click();
  }

  /**
   * Fill mortgage form and calculate.
   */
  async fillAndCalculateMortgage(input: {
    propertyPrice: string;
    downPaymentPercent?: string;
    interestRate?: string;
    loanYears?: string;
  }): Promise<void> {
    await this.fillMortgageForm(input);
    await this.calculateMortgage();
  }

  /**
   * Check if the mortgage result is visible.
   */
  async hasMortgageResult(): Promise<boolean> {
    return await this.mortgageResult.isVisible();
  }

  /**
   * Get the monthly payment text from the mortgage result.
   */
  async getMonthlyPaymentText(): Promise<string | null> {
    if (await this.mortgageResult.isVisible()) {
      return await this.mortgageResult.textContent();
    }
    return null;
  }

  /**
   * Check if the mortgage error is visible.
   */
  async hasMortgageError(): Promise<boolean> {
    return await this.mortgageError.isVisible();
  }

  /**
   * Fill the compare properties form and compare.
   */
  async fillAndCompare(ids: string[]): Promise<void> {
    await this.compareIdsInput.fill(ids.join(', '));
    await this.compareButton.click();
  }

  /**
   * Check if the comparison result is visible.
   */
  async hasComparisonResult(): Promise<boolean> {
    return await this.compareResult.isVisible();
  }

  /**
   * Check if the comparison error is visible.
   */
  async hasComparisonError(): Promise<boolean> {
    return await this.compareError.isVisible();
  }

  /**
   * Fill the neighborhood quality form and analyze.
   */
  async fillAndAnalyzeNeighborhood(input: {
    propertyId: string;
    lat?: string;
    lon?: string;
    city?: string;
  }): Promise<void> {
    await this.neighborhoodPropertyIdInput.fill(input.propertyId);
    if (input.lat) await this.neighborhoodLatInput.fill(input.lat);
    if (input.lon) await this.neighborhoodLonInput.fill(input.lon);
    if (input.city) await this.neighborhoodCityInput.fill(input.city);
    await this.neighborhoodAnalyzeButton.click();
  }

  /**
   * Check if the neighborhood quality result is visible.
   */
  async hasNeighborhoodResult(): Promise<boolean> {
    return await this.neighborhoodResult.isVisible();
  }

  /**
   * Check if the neighborhood quality error is visible.
   */
  async hasNeighborhoodError(): Promise<boolean> {
    return await this.neighborhoodError.isVisible();
  }
}
