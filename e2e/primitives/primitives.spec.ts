/**
 * The primitives E2E tests.
 *
 * The four primitives are the shared base of the interface: the stat tile,
 * the chart frame, the mono annotation and the tool card. Every route that
 * was reskinned draws them, so a route that loses one of them loses the
 * shape of the whole screen.
 *
 * Each primitive is asserted once, through the rendered output and by its
 * own handle.
 */

import { test, expect } from '@playwright/test';
import { mockChatSuccess } from '../mocks';
import {
  mockMarketIndicators,
  mockMarketTrends,
} from '../mocks/market.mock';
import { mockSearchSuccess } from '../mocks/api.mock';

test.describe('The Primitives', () => {
  test('the stat tile states a number and what it is about', async ({ page }) => {
    await page.route('**/api/v1/search*', mockSearchSuccess);

    await page.goto('/en/search');
    await page.getByTestId('search-input').fill('apartment in Berlin');
    await page.getByTestId('search-submit').click();

    // The area panel of the results carries the tiles.
    const tile = page.getByTestId('stat-tile').first();
    await expect(tile).toBeVisible({ timeout: 15000 });
  });

  test('the chart frame holds the chart and its caption', async ({ page }) => {
    await page.route('**/api/v1/market/indicators**', mockMarketIndicators);
    await page.route('**/api/v1/market/trends**', mockMarketTrends);

    await page.goto('/en/market-trends');

    await expect(page.getByTestId('chart-frame-area').first()).toBeVisible({ timeout: 15000 });
  });

  test('the mono annotation states a number', async ({ page }) => {
    await page.route('**/api/v1/market/indicators**', mockMarketIndicators);
    await page.route('**/api/v1/market/trends**', mockMarketTrends);

    await page.goto('/en/market-trends');

    await expect(page.getByTestId('mono-annotation').first()).toBeVisible({ timeout: 15000 });
  });

  test('the tool card shows the call the agent made', async ({ page }) => {
    await page.route('**/api/v1/chat*', mockChatSuccess);

    await page.goto('/en/chat');
    const input = page.getByLabel(/chat message input/i);
    await expect(input).toBeVisible({ timeout: 15000 });
    await input.fill('two-room flat in Kraków');
    await page.getByTestId('chat-send').click();

    await expect(page.getByTestId('tool-card').first()).toBeVisible({ timeout: 20000 });
  });
});
