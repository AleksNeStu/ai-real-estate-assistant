/**
 * Search Page Object for E2E tests.
 * Encapsulates search page interactions and elements.
 */

import { Page, Locator, expect } from '@playwright/test';

/**
 * The property cards of the results grid. `PropertyCard` marks every card
 * with `data-testid="property-card"`.
 */
function propertyCards(page: Page): Locator {
  return page.locator('[data-testid="property-card"]');
}

export class SearchPage {
  readonly page: Page;
  readonly searchInput: Locator;
  readonly searchButton: Locator;
  readonly resultsContainer: Locator;
  readonly mapContainer: Locator;
  readonly listContainer: Locator;
  readonly resultCount: Locator;
  readonly noResultsMessage: Locator;
  readonly loadingSpinner: Locator;
  readonly errorMessage: Locator;
  readonly filtersPanel: Locator;
  readonly mapViewButton: Locator;
  readonly listViewButton: Locator;
  readonly exportButton: Locator;

  constructor(page: Page) {
    this.page = page;
    // Actual UI: input with aria-label="Search query" inside form with role="search"
    this.searchInput = page
      .getByLabel('Search query')
      .or(page.getByPlaceholder(/describe what you.re looking for/i));
    // The submit button of the search form carries a test id. A plain
    // "button[type=submit]" would also collect the button of the newsletter
    // form in the footer.
    this.searchButton = page.getByTestId('search-submit');
    // A rendered result card is the proof that the search returned something.
    // The grid itself cannot be used: a locator that matches the grid and its
    // cards at the same time resolves to several elements and the strict mode
    // refuses to act on it.
    this.resultsContainer = page.locator('[data-testid="property-card"]').first();
    this.mapContainer = page.locator('.h-\\[420px\\]').or(page.locator('[class*="map"]'));
    this.listContainer = page.locator('.grid.grid-cols-1').first();
    this.resultCount = page.locator('text=/\\d+.*shown/i');
    this.noResultsMessage = page.locator('text=/no results found/i');
    this.loadingSpinner = page.locator('.animate-pulse').first();
    // A failed search shows the error state of the page (role="alert"). The
    // announcer of the router has the same role - it is not part of the page.
    this.errorMessage = page.locator('[role="alert"]:not(#__next-route-announcer__)').first();
    // The filter card is the one that owns the filter inputs.
    this.filtersPanel = page
      .locator('div.rounded-lg.border.bg-card')
      .filter({ has: page.locator('#min-price') })
      .first();
    // The switch between the list and the map view is a group of its own.
    const viewGroup = page.getByRole('group');
    this.mapViewButton = viewGroup.getByRole('button', { name: /^map$/i });
    this.listViewButton = viewGroup.getByRole('button', { name: /^list$/i });
    this.exportButton = page.getByRole('button', { name: /^export$/i });
  }

  /**
   * Navigate to the search page.
   */
  async navigate(): Promise<void> {
    await this.page.goto('/search');
    // Wait for the search input to be visible
    await expect(this.searchInput).toBeVisible({ timeout: 10000 });
  }

  /**
   * Perform a search query.
   */
  async search(query: string): Promise<void> {
    await this.searchInput.fill(query);
    await this.searchButton.click();
    // Wait for loading to complete
    await this.waitForResults();
  }

  /**
   * Wait for search results to load.
   */
  async waitForResults(): Promise<void> {
    // Wait for either results, the empty state or the error state - a failed
    // request shows an error and neither of the other two.
    await Promise.race([
      expect(this.resultsContainer).toBeVisible({ timeout: 15000 }),
      expect(this.noResultsMessage).toBeVisible({ timeout: 15000 }),
      expect(this.errorMessage).toBeVisible({ timeout: 15000 }),
    ]);
  }

  /**
   * Get the number of results displayed.
   *
   * The counter of the page ("{shown} of {total} shown on the map") starts
   * with the number of mappable listings, so it is not a reliable source.
   * The rendered cards are.
   */
  async getResultCount(): Promise<number> {
    await this.waitForResults();
    return await propertyCards(this.page).count();
  }

  /**
   * Get all property card elements.
   */
  async getPropertyCards(): Promise<Locator[]> {
    await this.waitForResults();
    return await propertyCards(this.page).all();
  }

  /**
   * Click on a property card by index.
   */
  async clickPropertyCard(index: number = 0): Promise<void> {
    const cards = await this.getPropertyCards();
    if (cards[index]) {
      await cards[index].click();
    } else {
      throw new Error(`Property card at index ${index} not found`);
    }
  }

  /**
   * Toggle to map view.
   */
  async switchToMapView(): Promise<void> {
    await this.mapViewButton.click();
    await expect(this.mapContainer).toBeVisible({ timeout: 5000 });
  }

  /**
   * Toggle to list view.
   */
  async switchToListView(): Promise<void> {
    await this.listViewButton.click();
    await expect(this.listContainer).toBeVisible({ timeout: 5000 });
  }

  /**
   * Set price range filter.
   */
  async setPriceRange(min: number, max: number): Promise<void> {
    const minInput = this.page.locator('#min-price');
    const maxInput = this.page.locator('#max-price');

    if (await minInput.isVisible()) {
      await minInput.fill(min.toString());
    }
    if (await maxInput.isVisible()) {
      await maxInput.fill(max.toString());
    }
  }

  /**
   * Set minimum rooms filter.
   */
  async setMinRooms(rooms: number): Promise<void> {
    const roomsInput = this.page.locator('#rooms');
    if (await roomsInput.isVisible()) {
      await roomsInput.fill(rooms.toString());
    }
  }

  /**
   * Apply filters (click apply button if exists).
   */
  async applyFilters(): Promise<void> {
    const applyButton = this.filtersPanel.getByRole('button', { name: /apply filters/i });
    if (await applyButton.isVisible().catch(() => false)) {
      await applyButton.click();
    } else {
      // There is no separate apply button - the filters travel with the next
      // search. The submit button of the search form stays disabled while the
      // query is empty, so a default query is entered first.
      if (!(await this.searchInput.inputValue())) {
        await this.searchInput.fill('Berlin');
      }
      await this.page.locator('form[role="search"] button[type="submit"]').click();
    }
    await this.waitForResults();
  }

  /**
   * Check if no results message is displayed.
   */
  async hasNoResults(): Promise<boolean> {
    return await this.noResultsMessage.isVisible();
  }

  /**
   * Check if results are displayed.
   */
  async hasResults(): Promise<boolean> {
    return await this.resultsContainer.isVisible();
  }

  /**
   * Export results in the specified format.
   */
  async exportResults(format: 'csv' | 'excel' | 'json' = 'csv'): Promise<void> {
    await this.exportButton.click();

    // Select format if dropdown appears
    const formatOption = this.page.getByRole('option', { name: format });
    if (await formatOption.isVisible({ timeout: 2000 }).catch(() => false)) {
      await formatOption.click();
    }

    // Confirm export
    const confirmButton = this.page.getByRole('button', { name: /export|download|confirm/i });
    if (await confirmButton.isVisible({ timeout: 2000 }).catch(() => false)) {
      await confirmButton.click();
    }
  }
}
