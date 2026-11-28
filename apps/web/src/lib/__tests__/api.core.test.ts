/**
 * Comprehensive tests for api.ts core utility functions and commonly used API endpoints.
 *
 * Tests cover:
 * - getApiUrl() - API URL configuration
 * - buildHeaders() - Request headers construction
 * - handleResponse<T>() - Response handling
 * - safeFetch() - Fetch with error handling
 * - searchProperties() - Property search
 * - getMarketTrends() - Market analytics
 * - calculateMortgage() - Mortgage calculator
 * - comparePropertiesApi() - Property comparison
 * - getFavorites() - User favorites
 * - addFavorite() / removeFavorite() - Favorite management
 * - getCollections() - User collections
 */

import { jest } from '@jest/globals';
import {
  ApiError,
  getApiUrl,
  searchProperties,
  getMarketTrends,
  calculateMortgage,
  comparePropertiesApi,
  getFavorites,
  addFavorite,
  removeFavorite,
  checkFavorite,
  getCollections,
  createCollection,
  getPriceHistory,
} from '../api';
import type {
  SearchResponse,
  MarketTrends,
  MortgageResult,
  FavoriteListResponse,
  FavoriteCheckResponse,
  CollectionListResponse,
  PriceHistory,
} from '../types';

// Mock fetch globally - match pattern from existing tests
global.fetch = jest.fn();

describe('api.ts Core Utility Functions', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    window.localStorage.clear();
    (global.fetch as jest.Mock) = jest.fn();
    // Reset to default API URL
    delete process.env.NEXT_PUBLIC_API_URL;
  });

  afterEach(() => {
    jest.resetAllMocks();
  });

  describe('getApiUrl', () => {
    it('returns default API URL when env var is not set', () => {
      expect(getApiUrl()).toBe('/api/v1');
    });

    it('returns custom API URL from environment', () => {
      process.env.NEXT_PUBLIC_API_URL = 'https://api.example.com';
      expect(getApiUrl()).toBe('https://api.example.com');
    });

    it('returns custom API URL with trailing slash', () => {
      process.env.NEXT_PUBLIC_API_URL = 'https://api.example.com/v2/';
      expect(getApiUrl()).toBe('https://api.example.com/v2/');
    });
  });

  describe('buildHeaders (via API calls)', () => {
    it('includes Content-Type header by default', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ results: [], count: 0 }),
      });

      await searchProperties({ query: 'test' });

      const fetchCall = (global.fetch as jest.Mock).mock.calls[0];
      const headers = fetchCall[1]?.headers;

      expect(headers).toHaveProperty('Content-Type', 'application/json');
    });

    it('never sends an asserted identity - the session names the account', async () => {
      window.localStorage.setItem('userEmail', 'test@example.com');

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ results: [], count: 0 }),
      });

      await searchProperties({ query: 'test' });

      const fetchCall = (global.fetch as jest.Mock).mock.calls[0];
      const headers = fetchCall[1]?.headers;

      // The browser does not name the account: the backend resolves it from
      // the session token, and a header would only ever be an assertion.
      expect(headers).not.toHaveProperty('X-User-Email');
    });

    it('sends no identity header at all when the browser holds no address', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ results: [], count: 0 }),
      });

      await searchProperties({ query: 'test' });

      const fetchCall = (global.fetch as jest.Mock).mock.calls[0];
      const headers = fetchCall[1]?.headers;

      expect(headers).not.toHaveProperty('X-User-Email');
    });
  });

  describe('fetch error propagation', () => {
    it('propagates fetch rejections', async () => {
      (global.fetch as jest.Mock).mockRejectedValueOnce(new TypeError('Failed to fetch'));

      // searchProperties uses safeFetch which should wrap network errors
      // In test environment, the mock rejection is propagated
      await expect(searchProperties({ query: 'test' })).rejects.toThrow();
    });
  });

  describe('handleResponse error handling', () => {
    it('throws ApiError with correct properties on HTTP error', async () => {
      const mockErrorResponse = {
        ok: false,
        status: 404,
        statusText: 'Not Found',
        text: async () => JSON.stringify({ detail: 'Property not found' }),
        json: async () => ({ detail: 'Property not found' }),
        headers: {
          get: (name: string) => (name === 'X-Request-ID' ? 'req-123-abc' : null),
        },
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce(mockErrorResponse);

      try {
        await searchProperties({ query: 'nonexistent' });
      } catch (error) {
        expect(error).toBeInstanceOf(ApiError);
        if (error instanceof ApiError) {
          expect(error.message).toBe('Property not found');
          expect(error.status).toBe(404);
          expect(error.category).toBe('not_found');
          expect(error.request_id).toBe('req-123-abc');
          expect(error.isRetryable).toBe(false);
        }
      }
    });

    it('parses error detail from JSON response', async () => {
      const mockErrorResponse = {
        ok: false,
        status: 400,
        statusText: 'Bad Request',
        text: async () => JSON.stringify({ detail: 'Invalid search parameters' }),
        json: async () => ({ detail: 'Invalid search parameters' }),
        headers: { get: () => null },
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce(mockErrorResponse);

      try {
        await searchProperties({ query: '' });
      } catch (error) {
        expect(error).toBeInstanceOf(ApiError);
        if (error instanceof ApiError) {
          expect(error.message).toBe('Invalid search parameters');
          expect(error.status).toBe(400);
          expect(error.category).toBe('validation');
        }
      }
    });

    it('handles non-JSON error response', async () => {
      const mockErrorResponse = {
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
        text: async () => 'Internal Server Error',
        json: async () => {
          throw new Error('Invalid JSON');
        },
        headers: { get: () => null },
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce(mockErrorResponse);

      try {
        await searchProperties({ query: 'test' });
      } catch (error) {
        expect(error).toBeInstanceOf(ApiError);
        if (error instanceof ApiError) {
          expect(error.message).toBe('Internal Server Error');
          expect(error.status).toBe(500);
          expect(error.category).toBe('server');
        }
      }
    });

    it('uses default message when error text is empty', async () => {
      const mockErrorResponse = {
        ok: false,
        status: 503,
        statusText: 'Service Unavailable',
        text: async () => '',
        json: async () => ({}),
        headers: { get: () => null },
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce(mockErrorResponse);

      try {
        await searchProperties({ query: 'test' });
      } catch (error) {
        expect(error).toBeInstanceOf(ApiError);
        if (error instanceof ApiError) {
          expect(error.message).toBe('API request failed');
        }
      }
    });

    it('returns parsed JSON on successful response', async () => {
      const mockData: SearchResponse = {
        results: [],
        count: 0,
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockData,
      });

      const result = await searchProperties({ query: 'test' });
      expect(result).toEqual(mockData);
    });
  });
});

describe('ApiError class', () => {
  it('creates error with all properties', () => {
    const error = new ApiError('Test error', 400, 'req-123', 'validation');

    expect(error.message).toBe('Test error');
    expect(error.status).toBe(400);
    expect(error.request_id).toBe('req-123');
    expect(error.category).toBe('validation');
    expect(error.name).toBe('ApiError');
  });

  describe('categorizeStatus', () => {
    it('categorizes status codes correctly', () => {
      expect(ApiError.categorizeStatus(0)).toBe('network');
      expect(ApiError.categorizeStatus(401)).toBe('auth');
      expect(ApiError.categorizeStatus(403)).toBe('auth');
      expect(ApiError.categorizeStatus(404)).toBe('not_found');
      expect(ApiError.categorizeStatus(408)).toBe('timeout');
      expect(ApiError.categorizeStatus(429)).toBe('rate_limit');
      expect(ApiError.categorizeStatus(400)).toBe('validation');
      expect(ApiError.categorizeStatus(422)).toBe('validation');
      expect(ApiError.categorizeStatus(500)).toBe('server');
      expect(ApiError.categorizeStatus(502)).toBe('server');
      expect(ApiError.categorizeStatus(503)).toBe('server');
      expect(ApiError.categorizeStatus(504)).toBe('timeout');
      expect(ApiError.categorizeStatus(418)).toBe('unknown'); // I'm a teapot
    });
  });

  describe('isRetryableCategory', () => {
    it('determines retryability correctly', () => {
      expect(ApiError.isRetryableCategory('network', 0)).toBe(true);
      expect(ApiError.isRetryableCategory('timeout', 408)).toBe(true);
      expect(ApiError.isRetryableCategory('rate_limit', 429)).toBe(true);
      expect(ApiError.isRetryableCategory('server', 502)).toBe(true);
      expect(ApiError.isRetryableCategory('server', 503)).toBe(true);
      expect(ApiError.isRetryableCategory('server', 500)).toBe(false);
      expect(ApiError.isRetryableCategory('auth', 401)).toBe(false);
      expect(ApiError.isRetryableCategory('validation', 400)).toBe(false);
      expect(ApiError.isRetryableCategory('not_found', 404)).toBe(false);
    });
  });

  describe('static factory methods', () => {
    it('creates network error', () => {
      const originalError = new Error('Connection lost');
      const error = ApiError.networkError(originalError);

      expect(error.message).toBe('Connection lost');
      expect(error.status).toBe(0);
      expect(error.category).toBe('network');
      expect(error.isRetryable).toBe(true);
      expect(error.cause).toBe(originalError);
    });

    it('creates timeout error', () => {
      const error = ApiError.timeoutError('req-timeout-123');

      expect(error.message).toBe('Request timed out. Please try again.');
      expect(error.status).toBe(408);
      expect(error.request_id).toBe('req-timeout-123');
      expect(error.category).toBe('timeout');
      expect(error.isRetryable).toBe(true);
    });

    it('creates network error without original error', () => {
      const error = ApiError.networkError();

      expect(error.message).toBe('Network request failed. Check your connection.');
      expect(error.status).toBe(0);
      expect(error.category).toBe('network');
      expect(error.cause).toBeUndefined();
    });
  });
});

describe('Property Search API', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (global.fetch as jest.Mock) = jest.fn();
    window.localStorage.clear();
  });

  describe('searchProperties', () => {
    it('sends POST request to /search endpoint', async () => {
      const mockResponse: SearchResponse = {
        results: [],
        count: 0,
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      await searchProperties({ query: 'Berlin apartments' });

      expect(global.fetch).toHaveBeenCalledTimes(1);
      const [url, options] = (global.fetch as jest.Mock).mock.calls[0];
      expect(url).toContain('/search');
      expect(options?.method).toBe('POST');
    });

    it('includes query in request body', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ results: [], count: 0 }),
      });

      await searchProperties({ query: '2 bedroom apartment' });

      const [, options] = (global.fetch as jest.Mock).mock.calls[0];
      const body = JSON.parse(options?.body as string);
      expect(body.query).toBe('2 bedroom apartment');
    });

    it('includes optional parameters in request body', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ results: [], count: 0 }),
      });

      const searchRequest = {
        query: 'test',
        limit: 10,
        filters: { city: 'Berlin' },
        sort_by: 'price' as const,
        sort_order: 'asc' as const,
      };

      await searchProperties(searchRequest);

      const [, options] = (global.fetch as jest.Mock).mock.calls[0];
      const body = JSON.parse(options?.body as string);
      expect(body).toEqual(searchRequest);
    });

    it('returns search results with count', async () => {
      const mockResults: SearchResponse = {
        results: [
          {
            property: {
              id: '1',
              city: 'Berlin',
              property_type: 'apartment',
              listing_type: 'rent',
              has_parking: false,
              has_garden: false,
              has_pool: false,
              has_garage: false,
              has_bike_room: false,
              price: 1500,
            },
            score: 0.95,
          },
        ],
        count: 1,
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResults,
      });

      const result = await searchProperties({ query: 'Berlin' });

      expect(result.results).toHaveLength(1);
      expect(result.count).toBe(1);
      expect(result.results[0].property.city).toBe('Berlin');
    });

    it('handles empty results', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ results: [], count: 0 }),
      });

      const result = await searchProperties({ query: 'nonexistent' });

      expect(result.results).toEqual([]);
      expect(result.count).toBe(0);
    });
  });
});

describe('Market Analytics API', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (global.fetch as jest.Mock) = jest.fn();
  });

  describe('getMarketTrends', () => {
    it('fetches market trends without parameters', async () => {
      const mockTrends: MarketTrends = {
        period_start: '2024-01-01',
        period_end: '2024-12-31',
        data_points: [],
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockTrends,
      });

      await getMarketTrends({});

      expect(global.fetch).toHaveBeenCalledTimes(1);
      const [url] = (global.fetch as jest.Mock).mock.calls[0];
      expect(url).toContain('/market/trends');
    });

    it('includes city in query parameters', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ period_start: '', period_end: '', data_points: [] }),
      });

      await getMarketTrends({ city: 'Berlin' });

      const [url] = (global.fetch as jest.Mock).mock.calls[0];
      expect(url).toContain('city=Berlin');
    });

    it('includes multiple query parameters', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ period_start: '', period_end: '', data_points: [] }),
      });

      await getMarketTrends({
        city: 'Berlin',
        district: 'Mitte',
        interval: 'month',
        months_back: 12,
      });

      const [url] = (global.fetch as jest.Mock).mock.calls[0];
      expect(url).toContain('city=Berlin');
      expect(url).toContain('district=Mitte');
      expect(url).toContain('interval=month');
      expect(url).toContain('months_back=12');
    });

    it('returns market trends data', async () => {
      const mockTrends: MarketTrends = {
        period_start: '2024-01-01',
        period_end: '2024-12-31',
        data_points: [
          { date: '2024-01', avg_price: 500000, count: 100 },
          { date: '2024-02', avg_price: 510000, count: 95 },
        ],
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockTrends,
      });

      const result = await getMarketTrends({ city: 'Berlin' });

      expect(result.data_points).toHaveLength(2);
      expect(result.data_points[0].avg_price).toBe(500000);
    });
  });

  describe('getPriceHistory', () => {
    it('fetches price history for a property', async () => {
      const mockHistory: PriceHistory = {
        property_id: 'prop-123',
        history: [],
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockHistory,
      });

      await getPriceHistory('prop-123');

      expect(global.fetch).toHaveBeenCalledTimes(1);
      const [url] = (global.fetch as jest.Mock).mock.calls[0];
      expect(url).toContain('/market/price-history/prop-123');
    });

    it('includes limit parameter', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ property_id: 'prop-123', history: [] }),
      });

      await getPriceHistory('prop-123', 50);

      const [url] = (global.fetch as jest.Mock).mock.calls[0];
      expect(url).toContain('limit=50');
    });

    it('returns price history data', async () => {
      const mockHistory: PriceHistory = {
        property_id: 'prop-123',
        history: [
          { date: '2024-01-01', price: 450000 },
          { date: '2024-06-01', price: 475000 },
          { date: '2024-12-01', price: 500000 },
        ],
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockHistory,
      });

      const result = await getPriceHistory('prop-123');

      expect(result.history).toHaveLength(3);
      expect(result.history[2].price).toBe(500000);
    });
  });
});

describe('Tools API', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (global.fetch as jest.Mock) = jest.fn();
  });

  describe('calculateMortgage', () => {
    it('calculates mortgage with required parameters', async () => {
      const mockResult: MortgageResult = {
        monthly_payment: 2500,
        total_interest: 400000,
        total_cost: 900000,
        down_payment: 100000,
        loan_amount: 400000,
        breakdown: { principal: 1000, interest: 1500 },
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResult,
      });

      const result = await calculateMortgage({
        property_price: 500000,
      });

      expect(result.monthly_payment).toBe(2500);
    });

    it('includes all optional parameters', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          monthly_payment: 0,
          total_interest: 0,
          total_cost: 0,
          down_payment: 0,
          loan_amount: 0,
          breakdown: {},
        }),
      });

      await calculateMortgage({
        property_price: 500000,
        down_payment_percent: 20,
        interest_rate: 4.5,
        loan_years: 30,
      });

      const [, options] = (global.fetch as jest.Mock).mock.calls[0];
      const body = JSON.parse(options?.body as string);
      expect(body).toEqual({
        property_price: 500000,
        down_payment_percent: 20,
        interest_rate: 4.5,
        loan_years: 30,
      });
    });

    it('sends request to correct endpoint', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          monthly_payment: 0,
          total_interest: 0,
          total_cost: 0,
          down_payment: 0,
          loan_amount: 0,
          breakdown: {},
        }),
      });

      await calculateMortgage({ property_price: 100000 });

      const [url] = (global.fetch as jest.Mock).mock.calls[0];
      expect(url).toContain('/tools/mortgage-calculator');
    });
  });

  describe('comparePropertiesApi', () => {
    it('sends property IDs in request body', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          properties: [],
          summary: { count: 0 },
        }),
      });

      await comparePropertiesApi(['prop-1', 'prop-2', 'prop-3']);

      const [, options] = (global.fetch as jest.Mock).mock.calls[0];
      const body = JSON.parse(options?.body as string);
      expect(body.property_ids).toEqual(['prop-1', 'prop-2', 'prop-3']);
    });

    it('returns comparison results', async () => {
      const mockComparison = {
        properties: [
          {
            id: 'prop-1',
            price: 500000,
            price_per_sqm: 5000,
            city: 'Berlin',
            rooms: 3,
            area_sqm: 100,
          },
          {
            id: 'prop-2',
            price: 450000,
            price_per_sqm: 4500,
            city: 'Berlin',
            rooms: 2,
            area_sqm: 100,
          },
        ],
        summary: {
          count: 2,
          min_price: 450000,
          max_price: 500000,
          price_difference: 50000,
        },
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockComparison,
      });

      const result = await comparePropertiesApi(['prop-1', 'prop-2']);

      expect(result.properties).toHaveLength(2);
      expect(result.summary.price_difference).toBe(50000);
    });

    it('sends request to correct endpoint', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ properties: [], summary: { count: 0 } }),
      });

      await comparePropertiesApi(['prop-1']);

      const [url] = (global.fetch as jest.Mock).mock.calls[0];
      expect(url).toContain('/tools/compare-properties');
    });
  });
});

describe('Favorites API', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (global.fetch as jest.Mock) = jest.fn();
  });

  describe('getFavorites', () => {
    it('fetches favorites without parameters', async () => {
      const mockResponse: FavoriteListResponse = {
        favorites: [],
        total: 0,
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      await getFavorites();

      expect(global.fetch).toHaveBeenCalledTimes(1);
      const [url] = (global.fetch as jest.Mock).mock.calls[0];
      expect(url).toContain('/favorites');
    });

    it('includes collection ID in query parameters', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ favorites: [], total: 0 }),
      });

      await getFavorites('collection-123');

      const [url] = (global.fetch as jest.Mock).mock.calls[0];
      expect(url).toContain('collection_id=collection-123');
    });

    it('includes limit and offset parameters', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ favorites: [], total: 0 }),
      });

      await getFavorites(undefined, 25, 50);

      const [url] = (global.fetch as jest.Mock).mock.calls[0];
      expect(url).toContain('limit=25');
      expect(url).toContain('offset=50');
    });

    it('returns favorites with total count', async () => {
      const mockFavorites: FavoriteListResponse = {
        favorites: [
          {
            id: 'fav-1',
            property_id: 'prop-1',
            created_at: '2024-01-01T00:00:00Z',
          },
        ],
        total: 1,
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockFavorites,
      });

      const result = await getFavorites();

      expect(result.favorites).toHaveLength(1);
      expect(result.total).toBe(1);
    });
  });

  describe('addFavorite', () => {
    it('adds property to favorites', async () => {
      const mockFavorite = {
        id: 'fav-new',
        property_id: 'prop-123',
        created_at: '2024-01-01T00:00:00Z',
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockFavorite,
      });

      const result = await addFavorite({ property_id: 'prop-123' });

      expect(result.property_id).toBe('prop-123');
      expect(global.fetch).toHaveBeenCalledTimes(1);
      const [url, options] = (global.fetch as jest.Mock).mock.calls[0];
      expect(url).toContain('/favorites');
      expect(options?.method).toBe('POST');
    });

    it('includes collection_id in request body', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          id: 'fav-new',
          property_id: 'prop-123',
          created_at: '2024-01-01T00:00:00Z',
        }),
      });

      await addFavorite({ property_id: 'prop-123', collection_id: 'collection-1' });

      const [, options] = (global.fetch as jest.Mock).mock.calls[0];
      const body = JSON.parse(options?.body as string);
      expect(body.collection_id).toBe('collection-1');
    });

    it('includes notes in request body', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          id: 'fav-new',
          property_id: 'prop-123',
          created_at: '2024-01-01T00:00:00Z',
        }),
      });

      await addFavorite({ property_id: 'prop-123', notes: 'Interesting property' });

      const [, options] = (global.fetch as jest.Mock).mock.calls[0];
      const body = JSON.parse(options?.body as string);
      expect(body.notes).toBe('Interesting property');
    });
  });

  describe('removeFavorite', () => {
    it('removes favorite by ID', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        text: async () => '',
      });

      await removeFavorite('fav-123');

      expect(global.fetch).toHaveBeenCalledTimes(1);
      const [url, options] = (global.fetch as jest.Mock).mock.calls[0];
      expect(url).toContain('/favorites/fav-123');
      expect(options?.method).toBe('DELETE');
    });

    it('throws ApiError on failure', async () => {
      const errorResponse = {
        ok: false,
        status: 404,
        text: async () => JSON.stringify({ detail: 'Favorite not found' }),
        headers: { get: () => null },
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce(errorResponse);

      await expect(removeFavorite('fav-999')).rejects.toThrow(ApiError);
    });
  });

  describe('checkFavorite', () => {
    it('checks if property is favorited', async () => {
      const mockCheck: FavoriteCheckResponse = {
        is_favorite: true,
        favorite_id: 'fav-123',
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockCheck,
      });

      const result = await checkFavorite('prop-123');

      expect(result.is_favorite).toBe(true);
      expect(result.favorite_id).toBe('fav-123');
    });

    it('returns false for non-favorited property', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ is_favorite: false, favorite_id: null }),
      });

      const result = await checkFavorite('prop-456');

      expect(result.is_favorite).toBe(false);
      expect(result.favorite_id).toBeNull();
    });

    it('sends request to correct endpoint', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ is_favorite: false, favorite_id: null }),
      });

      await checkFavorite('prop-123');

      const [url] = (global.fetch as jest.Mock).mock.calls[0];
      expect(url).toContain('/favorites/check/prop-123');
    });
  });
});

describe('Collections API', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (global.fetch as jest.Mock) = jest.fn();
  });

  describe('getCollections', () => {
    it('fetches all collections', async () => {
      const mockCollections: CollectionListResponse = {
        collections: [],
        total: 0,
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockCollections,
      });

      await getCollections();

      expect(global.fetch).toHaveBeenCalledTimes(1);
      const [url] = (global.fetch as jest.Mock).mock.calls[0];
      expect(url).toContain('/collections');
    });

    it('returns collections with total count', async () => {
      const mockCollections: CollectionListResponse = {
        collections: [
          {
            id: 'col-1',
            name: 'My Favorites',
            is_default: true,
            created_at: '2024-01-01T00:00:00Z',
          },
        ],
        total: 1,
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockCollections,
      });

      const result = await getCollections();

      expect(result.collections).toHaveLength(1);
      expect(result.collections[0].name).toBe('My Favorites');
      expect(result.total).toBe(1);
    });
  });

  describe('createCollection', () => {
    it('creates a new collection', async () => {
      const mockCollection = {
        id: 'col-new',
        name: 'Berlin Apartments',
        is_default: false,
        created_at: '2024-01-01T00:00:00Z',
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockCollection,
      });

      const result = await createCollection({ name: 'Berlin Apartments' });

      expect(result.name).toBe('Berlin Apartments');
      expect(result.is_default).toBe(false);
    });

    it('includes description in request body', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          id: 'col-new',
          name: 'Test',
          is_default: false,
          created_at: '2024-01-01T00:00:00Z',
        }),
      });

      await createCollection({
        name: 'Test',
        description: 'Test collection description',
      });

      const [, options] = (global.fetch as jest.Mock).mock.calls[0];
      const body = JSON.parse(options?.body as string);
      expect(body.description).toBe('Test collection description');
    });

    it('sends POST request to correct endpoint', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          id: 'col-new',
          name: 'Test',
          is_default: false,
          created_at: '2024-01-01T00:00:00Z',
        }),
      });

      await createCollection({ name: 'Test' });

      const [url, options] = (global.fetch as jest.Mock).mock.calls[0];
      expect(url).toContain('/collections');
      expect(options?.method).toBe('POST');
    });
  });
});
