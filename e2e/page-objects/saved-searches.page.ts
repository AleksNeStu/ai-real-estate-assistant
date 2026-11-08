/**
 * Saved Searches Page Object for E2E tests.
 * Encapsulates saved-searches page interactions and elements.
 */

import { Page, Locator, expect } from '@playwright/test';

export class SavedSearchesPage {
  readonly page: Page;
  readonly heading: Locator;
  readonly refreshButton: Locator;
  readonly searchCards: Locator;
  readonly emptyState: Locator;
  readonly errorMessage: Locator;
  readonly loadingSpinner: Locator;

  constructor(page: Page) {
    this.page = page;
    this.heading = page.getByRole('heading', { name: /saved searches/i });
    this.refreshButton = page.getByRole('button', { name: /refresh/i });
    this.searchCards = page.locator('.grid.gap-4 > .rounded-lg');
    this.emptyState = page.locator('text=/no saved searches yet/i');
    // The error of the page is a single alert. The selector collects the
    // destructive background as well - both match the same element, so the
    // first one is enough.
    this.errorMessage = page.locator('[role="alert"]').first();
    this.loadingSpinner = page.locator('.animate-spin');
  }

  /**
   * Navigate to the saved searches page.
   */
  async navigate(): Promise<void> {
    await this.page.goto('/saved-searches');
    await expect(this.heading).toBeVisible({ timeout: 10000 });
  }

  /**
   * Navigate and wait for loading to complete.
   */
  async navigateAndWait(): Promise<void> {
    await this.page.goto('/saved-searches');
    // Wait for either the list or empty state to appear
    await Promise.race([
      expect(this.heading).toBeVisible({ timeout: 10000 }),
      expect(this.page).toHaveURL(/auth\/login/, { timeout: 10000 }),
    ]);
  }

  /**
   * Get a specific saved search card by name.
   */
  getSearchCardByName(name: string): Locator {
    return this.page.locator('.grid.gap-4 > .rounded-lg').filter({ hasText: name });
  }

  /**
   * Get the alert toggle button for a saved search by its name.
   */
  getAlertToggleButton(cardName: string): Locator {
    const card = this.getSearchCardByName(cardName);
    return card.getByRole('button').first();
  }

  /**
   * Get the delete button for a saved search by its name.
   */
  getDeleteButton(cardName: string): Locator {
    const card = this.getSearchCardByName(cardName);
    return card
      .getByRole('button', { name: /delete/i })
      .or(card.locator('button[title="Delete search"]'));
  }

  /**
   * Toggle the alert on a saved search by name.
   */
  async toggleAlert(cardName: string): Promise<void> {
    const toggleButton = this.getAlertToggleButton(cardName);
    await toggleButton.click();
  }

  /**
   * Delete a saved search by name.
   * Handles the browser confirm dialog.
   */
  async deleteSearch(cardName: string): Promise<void> {
    // Listen for the confirm dialog and accept it
    this.page.once('dialog', async (dialog) => {
      expect(dialog.type()).toBe('confirm');
      await dialog.accept();
    });

    const deleteButton = this.getDeleteButton(cardName);
    await deleteButton.click();
  }

  /**
   * Get the number of saved search cards displayed.
   */
  async getSearchCount(): Promise<number> {
    return await this.searchCards.count();
  }

  /**
   * Check if the empty state is displayed.
   */
  async isEmptyState(): Promise<boolean> {
    return await this.emptyState.isVisible();
  }

  /**
   * Check if an error is displayed.
   */
  async hasError(): Promise<boolean> {
    return await this.errorMessage.isVisible();
  }

  /**
   * Click the refresh button.
   */
  async refresh(): Promise<void> {
    await this.refreshButton.click();
  }

  /**
   * Wait for loading to complete.
   */
  async waitForLoad(): Promise<void> {
    await expect(this.loadingSpinner)
      .toBeHidden({ timeout: 10000 })
      .catch(() => {
        // Spinner may have already disappeared
      });
  }
}
