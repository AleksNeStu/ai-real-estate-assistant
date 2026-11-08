/**
 * Market API mock handlers for E2E tests.
 * Provides mock responses for market trends and indicators endpoints.
 */

import { Route } from '@playwright/test';
import {
  TEST_MARKET_INDICATORS,
  TEST_MARKET_INDICATORS_KRAKOW,
  TEST_MARKET_TRENDS,
  TEST_MARKET_TRENDS_KRAKOW,
  TEST_MARKET_TRENDS_QUARTERLY,
  TEST_PRICE_HISTORY,
  TEST_PRICE_HISTORY_EMPTY,
  TEST_PRICE_ANOMALIES,
} from '../fixtures/market-data';

/**
 * Mock GET /api/v1/market/indicators (default, no city filter).
 */
export async function mockMarketIndicators(route: Route): Promise<void> {
  await route.fulfill({
    status: 200,
    headers: {
      'Content-Type': 'application/json',
      'Access-Control-Allow-Origin': '*',
    },
    body: JSON.stringify(TEST_MARKET_INDICATORS),
  });
}

/**
 * Mock GET /api/v1/market/indicators?city=Krakow (city-specific).
 */
export async function mockMarketIndicatorsKrakow(route: Route): Promise<void> {
  await route.fulfill({
    status: 200,
    headers: {
      'Content-Type': 'application/json',
      'Access-Control-Allow-Origin': '*',
    },
    body: JSON.stringify(TEST_MARKET_INDICATORS_KRAKOW),
  });
}

/**
 * Mock GET /api/v1/market/indicators returning an error.
 */
export async function mockMarketIndicatorsError(
  route: Route,
  statusCode?: number,
  message?: string
): Promise<void> {
  // Playwright calls the handler with (route, request) - the second argument is
  // the request object and not the status code.
  const status = typeof statusCode === 'number' ? statusCode : 500;
  const text = typeof message === 'string' ? message : 'Failed to load market indicators';
  await route.fulfill({
    status,
    headers: {
      'Content-Type': 'application/json',
      'Access-Control-Allow-Origin': '*',
    },
    body: JSON.stringify({ detail: text }),
  });
}

/**
 * Mock GET /api/v1/market/trends (default, monthly interval).
 * Inspects the request URL to return appropriate fixture based on city/interval params.
 */
export async function mockMarketTrends(route: Route): Promise<void> {
  const url = route.request().url();
  const urlObj = new URL(url);
  const city = urlObj.searchParams.get('city');
  const interval = urlObj.searchParams.get('interval') || 'month';

  let data;
  if (city && city.toLowerCase() === 'krakow') {
    data = TEST_MARKET_TRENDS_KRAKOW;
  } else if (interval === 'quarter') {
    data = TEST_MARKET_TRENDS_QUARTERLY;
  } else {
    data = TEST_MARKET_TRENDS;
  }

  await route.fulfill({
    status: 200,
    headers: {
      'Content-Type': 'application/json',
      'Access-Control-Allow-Origin': '*',
    },
    body: JSON.stringify(data),
  });
}

/**
 * Mock GET /api/v1/market/trends returning an error.
 */
export async function mockMarketTrendsError(
  route: Route,
  statusCode?: number,
  message?: string
): Promise<void> {
  // Playwright calls the handler with (route, request) - the second argument is
  // the request object and not the status code.
  const status = typeof statusCode === 'number' ? statusCode : 500;
  const text = typeof message === 'string' ? message : 'Failed to load market trends';
  await route.fulfill({
    status,
    headers: {
      'Content-Type': 'application/json',
      'Access-Control-Allow-Origin': '*',
    },
    body: JSON.stringify({ detail: text }),
  });
}

/**
 * Mock delayed market trends response to test loading states.
 */
export function mockMarketTrendsDelayed(delayMs: number = 2000) {
  return async (route: Route): Promise<void> => {
    await new Promise((resolve) => setTimeout(resolve, delayMs));
    await mockMarketTrends(route);
  };
}

/**
 * Mock delayed market indicators response to test loading states.
 */
export function mockMarketIndicatorsDelayed(delayMs: number = 2000) {
  return async (route: Route): Promise<void> => {
    await new Promise((resolve) => setTimeout(resolve, delayMs));
    await mockMarketIndicators(route);
  };
}

/**
 * Mock GET /api/v1/market/price-history/:propertyId
 */
export async function mockPriceHistory(route: Route): Promise<void> {
  await route.fulfill({
    status: 200,
    headers: {
      'Content-Type': 'application/json',
      'Access-Control-Allow-Origin': '*',
    },
    body: JSON.stringify(TEST_PRICE_HISTORY),
  });
}

/**
 * Mock GET /api/v1/market/price-history/:propertyId returning empty data.
 */
export async function mockPriceHistoryEmpty(route: Route): Promise<void> {
  await route.fulfill({
    status: 200,
    headers: {
      'Content-Type': 'application/json',
      'Access-Control-Allow-Origin': '*',
    },
    body: JSON.stringify(TEST_PRICE_HISTORY_EMPTY),
  });
}

/**
 * Mock GET /api/v1/market/price-history/:propertyId returning an error.
 */
export async function mockPriceHistoryError(
  route: Route,
  statusCode?: number,
  message?: string
): Promise<void> {
  // Playwright calls the handler with (route, request) - the second argument is
  // the request object and not the status code.
  const status = typeof statusCode === 'number' ? statusCode : 500;
  const text = typeof message === 'string' ? message : 'Failed to load price history';
  await route.fulfill({
    status,
    headers: {
      'Content-Type': 'application/json',
      'Access-Control-Allow-Origin': '*',
    },
    body: JSON.stringify({ detail: text }),
  });
}

/**
 * Mock GET /api/v1/market/anomalies
 */
export async function mockAnomalies(route: Route): Promise<void> {
  await route.fulfill({
    status: 200,
    headers: {
      'Content-Type': 'application/json',
      'Access-Control-Allow-Origin': '*',
    },
    body: JSON.stringify({ anomalies: TEST_PRICE_ANOMALIES }),
  });
}

/**
 * Mock GET /api/v1/market/anomalies returning empty.
 */
export async function mockAnomaliesEmpty(route: Route): Promise<void> {
  await route.fulfill({
    status: 200,
    headers: {
      'Content-Type': 'application/json',
      'Access-Control-Allow-Origin': '*',
    },
    body: JSON.stringify({ anomalies: [] }),
  });
}
