/**
 * The narrow widths.
 *
 * The suite ran at one viewport for a long time, so a layout that breaks at
 * the phone width landed green. The four-column row of the landing
 * instrument needed 344px and the row has 340px there, and the routes of the
 * "More" menu were nowhere in the phone menu - a phone visitor could not
 * reach them at all.
 *
 * These are the assertions that hold at every width the project declares:
 * the three surfaces of the product fit the width they are shown in, and the
 * thing that broke is broken no more. The baselines next to them are the
 * record of what each surface looked like at each size.
 */

import { Page, TestInfo, Locator } from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';

import { test, expect } from '../conftest';
import { mockLandingApis, mockChatSuccess, mockSearchSuccess } from '../mocks';

/**
 * The width of the document against the width of the window it is shown in.
 *
 * A document wider than its window is a horizontal scrollbar, and a
 * horizontal scrollbar is the thing a phone width is not allowed to have.
 */
async function horizontalOverflow(page: Page): Promise<number> {
  return page.evaluate(() => {
    const doc = document.documentElement;
    return doc.scrollWidth - doc.clientWidth;
  });
}

/**
 * The width of an element's content against the width it has.
 *
 * The instrument clips its overflow, so a row that does not fit is not a
 * scrollbar on the document - it is a price that is cut in half, and the
 * document never learns about it.
 */
async function clippedWidth(element: Locator): Promise<number> {
  return element.evaluate((node) => node.scrollWidth - node.clientWidth);
}

/**
 * The baseline of a surface at the size the project runs.
 *
 * The file is written when it is missing - a deliberate change of the
 * surface replaces the baseline by deleting it and running the suite again.
 * It is the record of what the surface looked like, not a pixel comparison:
 * the fonts of the workstation and of the runner are not the same, so a pixel
 * gate would only measure that.
 */
async function keepBaseline(testInfo: TestInfo, name: string, page: Page): Promise<void> {
  // The baselines live next to the suite that keeps them, one folder per
  // project - the size is the project's own name.
  const dir = path.join(testInfo.config.rootDir, 'baselines', testInfo.project.name);
  const file = path.join(dir, `${name}.png`);
  if (fs.existsSync(file)) return;
  fs.mkdirSync(dir, { recursive: true });
  await page.screenshot({ path: file, fullPage: false });
}

test.describe('The landing', () => {
  test('the map, the priced rows and the exit controls fit the width', async ({ page }, testInfo) => {
    await mockLandingApis(page);
    await page.goto('/en/');

    // The map panel of the hero.
    await expect(page.locator('.leaflet-container').first()).toBeVisible({ timeout: 20000 });

    // The three priced rows - the instrument of the hero.
    const rows = page.getByTestId('instrument-row');
    await expect(rows).toHaveCount(3, { timeout: 20000 });

    // A row carries its four numbers in one row at the desktop width and in
    // two at the phone one. Either way the row holds all of them: the
    // instrument clips what does not fit, so a clipped row is a price cut
    // in half.
    expect(await clippedWidth(rows.first())).toBeLessThanOrEqual(1);

    // The exit controls. The landing was rebuilt: the waitlist sits in the
    // hosted tier now and the open-source material in its own section.
    const open = page.locator('#open');
    const hosted = page.locator('#hosted');
    for (const control of [
      open.getByRole('link', { name: 'Fork it on GitHub' }),
      hosted.getByRole('button', { name: 'Notify me' }),
      open.getByRole('link', { name: 'Talk to the studio' }),
    ]) {
      await expect(control).toBeVisible({ timeout: 15000 });
    }

    expect(await horizontalOverflow(page)).toBeLessThanOrEqual(1);

    await keepBaseline(testInfo, 'landing', page);
  });
});

test.describe('The search page', () => {
  test('the map stands after the results at every width', async ({ page }) => {
    await page.route('**/api/v1/search*', mockSearchSuccess);
    await page.route('**/api/v1/properties*', mockSearchSuccess);

    await page.goto('/en/search');

    const map = page.getByTestId('search-map');
    const results = page.getByTestId('search-results');
    await expect(map).toBeVisible({ timeout: 20000 });
    await expect(results).toBeVisible({ timeout: 20000 });

    // The two panes stand in the same order at every width: the results
    // first, the map after them. On a desktop that is two columns; on a
    // phone it is one column with the same order. The map used to stand
    // BEFORE the results on a phone, so the visitor met a map where the
    // results should have been - and the toggle meant two different things
    // depending on the width.
    const boxes = await page.evaluate(() => {
      const mapBox = document.querySelector('[data-testid="search-map"]')?.getBoundingClientRect();
      const resultsBox = document
        .querySelector('[data-testid="search-results"]')
        ?.getBoundingClientRect();
      if (!mapBox || !resultsBox) return null;
      return {
        mapX: mapBox.x,
        mapY: mapBox.y,
        resultsX: resultsBox.x,
        resultsY: resultsBox.y,
        width: window.innerWidth,
      };
    });

    expect(boxes).not.toBeNull();
    const { mapX, mapY, resultsX, resultsY, width } = boxes!;

    if (width >= 1024) {
      // The desktop: the map is the third column, on the right of the results.
      expect(mapX).toBeGreaterThan(resultsX);
    } else {
      // The phone: the map is under the results, not over them.
      expect(mapY).toBeGreaterThan(resultsY);
    }
  });

  test('the map and the filters fit the width', async ({ page }, testInfo) => {
    await page.route('**/api/v1/search*', mockSearchSuccess);
    await page.route('**/api/v1/properties*', mockSearchSuccess);

    await page.goto('/en/search');

    // The map pane.
    await expect(page.getByTestId('search-map')).toBeVisible({ timeout: 20000 });

    // The filters are behind the toggle below the `lg` breakpoint - the
    // pane is the same one, collapsed. Opening it is what the visitor does.
    const toggle = page.getByTestId('search-filters-toggle');
    if (await toggle.isVisible().catch(() => false)) {
      await toggle.click();
    }
    await expect(page.locator('#min-price')).toBeVisible({ timeout: 10000 });

    expect(await horizontalOverflow(page)).toBeLessThanOrEqual(1);

    await keepBaseline(testInfo, 'search', page);
  });
});

test.describe('The chat', () => {
  test('the chat sends and streams at the width', async ({ page, authenticatedChatPage }, testInfo) => {
    await page.route('**/api/v1/chat*', mockChatSuccess);

    await authenticatedChatPage.navigate();
    await authenticatedChatPage.sendMessageAndWaitForResponse('Find me an apartment in Berlin');

    const answer = await authenticatedChatPage.getLastAssistantMessageText();
    expect(answer.length).toBeGreaterThan(0);

    expect(await horizontalOverflow(page)).toBeLessThanOrEqual(1);

    await keepBaseline(testInfo, 'chat', page);
  });
});
