/**
 * Tests for tools.ts API module.
 * Covers all 16 exported async functions: mortgage calculator, TCO calculator,
 * TCO comparison, location defaults, available locations, investment analysis,
 * neighborhood quality, property comparison, price analysis, location analysis,
 * valuation, legal check, address enrichment, advanced investment, portfolio
 * analysis, rent-vs-buy, listing generation, commute time, commute ranking.
 */

import { describe, it, expect, jest, beforeEach } from '@jest/globals';

// Mock fetch globally before any imports
const mockFetch = jest.fn();
(globalThis as unknown as { fetch: jest.Mock }).fetch = mockFetch;

import {
  calculateMortgage,
  calculateTCO,
  compareTCO,
  getTCOLocationDefaults,
  getTCOAvailableLocations,
  calculateInvestment,
  neighborhoodQualityApi,
  getNeighborhoodBadge,
  comparePropertiesApi,
  priceAnalysisApi,
  locationAnalysisApi,
  valuationApi,
  legalCheckApi,
  enrichAddressApi,
  calculateAdvancedInvestment,
  analyzePortfolio,
  calculateRentVsBuy,
  generateListing,
  calculateCommuteTime,
  rankPropertiesByCommute,
  ApiError,
} from '@/lib/api/tools';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const API_BASE = '/api/v1';

function createMockResponse(data: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    statusText: status === 200 ? 'OK' : 'Error',
    headers: new Headers({ 'X-Request-ID': 'req-test-123' }),
    json: async () => data,
    text: async () => JSON.stringify(data),
  } as Response;
}

function createErrorResponse(message: string, status: number) {
  const body = { detail: message };
  return {
    ok: false,
    status,
    statusText: 'Error',
    headers: new Headers({ 'X-Request-ID': 'req-err-001' }),
    json: async () => body,
    text: async () => JSON.stringify(body),
  } as Response;
}

function expectCalledWithPath(pathPrefix: string) {
  const calledUrl = mockFetch.mock.calls[0][0] as string;
  expect(calledUrl).toContain(pathPrefix);
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('tools.ts API', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockFetch.mockReset();
  });

  // =========================================================================
  // calculateMortgage
  // =========================================================================

  describe('calculateMortgage', () => {
    it('calculates mortgage via POST', async () => {
      const result = { monthly_payment: 1500, total_interest: 50000 };
      mockFetch.mockResolvedValueOnce(createMockResponse(result));

      const input = { loan_amount: 300000, interest_rate: 5.0, loan_term_years: 30 };
      const response = await calculateMortgage(input);

      expect(mockFetch).toHaveBeenCalledTimes(1);
      expectCalledWithPath(`${API_BASE}/tools/mortgage-calculator`);
      const init = mockFetch.mock.calls[0][1] as RequestInit;
      expect(init.method).toBe('POST');
      expect(JSON.parse(init.body as string)).toEqual(input);
      expect(response.monthly_payment).toBe(1500);
    });

    it('throws ApiError on server error', async () => {
      mockFetch.mockResolvedValueOnce(createErrorResponse('Server error', 500));

      await expect(
        calculateMortgage({ loan_amount: 100000, interest_rate: 5, loan_term_years: 30 })
      ).rejects.toThrow(ApiError);
    });
  });

  // =========================================================================
  // calculateTCO
  // =========================================================================

  describe('calculateTCO', () => {
    it('calculates TCO via POST', async () => {
      const result = { total_cost: 500000, monthly_tco: 2000 };
      mockFetch.mockResolvedValueOnce(createMockResponse(result));

      const input = { property_price: 300000, country: 'PL' };
      const response = await calculateTCO(input);

      expectCalledWithPath(`${API_BASE}/tools/tco-calculator`);
      const init = mockFetch.mock.calls[0][1] as RequestInit;
      expect(init.method).toBe('POST');
      expect(JSON.parse(init.body as string)).toEqual(input);
      expect(response.total_cost).toBe(500000);
    });

    it('throws ApiError on 400', async () => {
      mockFetch.mockResolvedValueOnce(createErrorResponse('Bad request', 400));

      await expect(calculateTCO({ property_price: -1, country: 'XX' })).rejects.toThrow(ApiError);
    });
  });

  // =========================================================================
  // compareTCO
  // =========================================================================

  describe('compareTCO', () => {
    it('compares TCO via POST', async () => {
      const result = { properties: [], winner_index: 0 };
      mockFetch.mockResolvedValueOnce(createMockResponse(result));

      const input = {
        properties: [{ property_price: 200000 }, { property_price: 300000 }],
        country: 'PL',
      };
      const response = await compareTCO(input);

      expectCalledWithPath(`${API_BASE}/tools/tco-comparison`);
      expect(response.winner_index).toBe(0);
    });

    it('throws ApiError on error', async () => {
      mockFetch.mockResolvedValueOnce(createErrorResponse('Error', 422));

      await expect(compareTCO({ properties: [], country: 'PL' })).rejects.toThrow(ApiError);
    });
  });

  // =========================================================================
  // getTCOLocationDefaults
  // =========================================================================

  describe('getTCOLocationDefaults', () => {
    it('fetches location defaults with country only', async () => {
      const result = { property_tax_rate: 0.02, notary_fees_percent: 0.015 };
      mockFetch.mockResolvedValueOnce(createMockResponse(result));

      const response = await getTCOLocationDefaults('PL');

      const calledUrl = mockFetch.mock.calls[0][0] as string;
      expect(calledUrl).toContain(`${API_BASE}/tools/tco-location-defaults?`);
      expect(calledUrl).toContain('country=PL');
      expect(calledUrl).not.toContain('region');
      expect(response.property_tax_rate).toBe(0.02);
    });

    it('appends region when provided', async () => {
      mockFetch.mockResolvedValueOnce(createMockResponse({}));

      await getTCOLocationDefaults('DE', 'Bavaria');

      const calledUrl = mockFetch.mock.calls[0][0] as string;
      expect(calledUrl).toContain('country=DE');
      expect(calledUrl).toContain('region=Bavaria');
    });

    it('throws on error', async () => {
      mockFetch.mockResolvedValueOnce(createErrorResponse('Not found', 404));

      await expect(getTCOLocationDefaults('XX')).rejects.toThrow(ApiError);
    });
  });

  // =========================================================================
  // getTCOAvailableLocations
  // =========================================================================

  describe('getTCOAvailableLocations', () => {
    it('fetches available locations via GET', async () => {
      const result = { locations: ['PL', 'DE', 'ES'] };
      mockFetch.mockResolvedValueOnce(createMockResponse(result));

      const response = await getTCOAvailableLocations();

      expectCalledWithPath(`${API_BASE}/tools/tco-available-locations`);
      const init = mockFetch.mock.calls[0][1] as RequestInit;
      expect(init.method).toBe('GET');
      expect(response.locations).toEqual(['PL', 'DE', 'ES']);
    });

    it('throws on error', async () => {
      mockFetch.mockResolvedValueOnce(createErrorResponse('Server error', 500));

      await expect(getTCOAvailableLocations()).rejects.toThrow(ApiError);
    });
  });

  // =========================================================================
  // calculateInvestment
  // =========================================================================

  describe('calculateInvestment', () => {
    it('calculates investment analysis via POST', async () => {
      const result = { roi: 8.5, cap_rate: 5.2, cash_flow: 1200 };
      mockFetch.mockResolvedValueOnce(createMockResponse(result));

      const input = { property_price: 200000, monthly_rent: 1500 };
      const response = await calculateInvestment(input);

      expectCalledWithPath(`${API_BASE}/tools/investment-analysis`);
      const init = mockFetch.mock.calls[0][1] as RequestInit;
      expect(init.method).toBe('POST');
      expect(response.roi).toBe(8.5);
    });

    it('throws on error', async () => {
      mockFetch.mockResolvedValueOnce(createErrorResponse('Bad input', 422));

      await expect(calculateInvestment({ property_price: -1 })).rejects.toThrow(ApiError);
    });
  });

  // =========================================================================
  // neighborhoodQualityApi
  // =========================================================================

  describe('neighborhoodQualityApi', () => {
    it('fetches neighborhood quality via POST', async () => {
      const result = { score: 85, amenities: 90, safety: 80 };
      mockFetch.mockResolvedValueOnce(createMockResponse(result));

      const input = { property_id: 'prop-1', latitude: 50.06, longitude: 19.94 };
      const response = await neighborhoodQualityApi(input);

      expectCalledWithPath(`${API_BASE}/tools/neighborhood-quality`);
      const init = mockFetch.mock.calls[0][1] as RequestInit;
      expect(init.method).toBe('POST');
      expect(JSON.parse(init.body as string)).toEqual(input);
      expect(response.score).toBe(85);
    });

    it('throws on error', async () => {
      mockFetch.mockResolvedValueOnce(createErrorResponse('Not found', 404));

      await expect(neighborhoodQualityApi({ property_id: 'bad' })).rejects.toThrow(ApiError);
    });
  });

  // =========================================================================
  // getNeighborhoodBadge
  // =========================================================================

  describe('getNeighborhoodBadge', () => {
    it('delegates to neighborhoodQualityApi with mapped fields', async () => {
      const result = { score: 75, amenities: 80 };
      mockFetch.mockResolvedValueOnce(createMockResponse(result));

      const response = await getNeighborhoodBadge({
        id: 'prop-1',
        latitude: 50.06,
        longitude: 19.94,
        city: 'Krakow',
        neighborhood: 'Old Town',
      });

      const init = mockFetch.mock.calls[0][1] as RequestInit;
      const body = JSON.parse(init.body as string);
      expect(body.property_id).toBe('prop-1');
      expect(body.latitude).toBe(50.06);
      expect(body.city).toBe('Krakow');
      expect(body.neighborhood).toBe('Old Town');
      expect(response.score).toBe(75);
    });

    it('uses "unknown" as default property_id', async () => {
      mockFetch.mockResolvedValueOnce(createMockResponse({ score: 50 }));

      await getNeighborhoodBadge({ latitude: 50, longitude: 19 });

      const body = JSON.parse((mockFetch.mock.calls[0][1] as RequestInit).body as string);
      expect(body.property_id).toBe('unknown');
    });
  });

  // =========================================================================
  // comparePropertiesApi
  // =========================================================================

  describe('comparePropertiesApi', () => {
    it('compares properties via POST', async () => {
      const result = {
        properties: [
          { id: 'p1', price: 200000, price_per_sqm: 2000, city: 'Krakow' },
          { id: 'p2', price: 300000, price_per_sqm: 3000, city: 'Warsaw' },
        ],
        summary: { count: 2, min_price: 200000, max_price: 300000, price_difference: 100000 },
      };
      mockFetch.mockResolvedValueOnce(createMockResponse(result));

      const response = await comparePropertiesApi(['p1', 'p2']);

      expectCalledWithPath(`${API_BASE}/tools/compare-properties`);
      const init = mockFetch.mock.calls[0][1] as RequestInit;
      expect(init.method).toBe('POST');
      expect(JSON.parse(init.body as string)).toEqual({ property_ids: ['p1', 'p2'] });
      expect(response.properties).toHaveLength(2);
      expect(response.summary.price_difference).toBe(100000);
    });

    it('throws on error', async () => {
      mockFetch.mockResolvedValueOnce(createErrorResponse('Error', 500));

      await expect(comparePropertiesApi(['p1'])).rejects.toThrow(ApiError);
    });
  });

  // =========================================================================
  // priceAnalysisApi
  // =========================================================================

  describe('priceAnalysisApi', () => {
    it('analyses prices via POST', async () => {
      const result = {
        query: 'Krakow apartments',
        count: 150,
        average_price: 350000,
        median_price: 320000,
        min_price: 150000,
        max_price: 800000,
        average_price_per_sqm: 3500,
        median_price_per_sqm: 3200,
        distribution_by_type: { apartment: 100, house: 50 },
      };
      mockFetch.mockResolvedValueOnce(createMockResponse(result));

      const response = await priceAnalysisApi('Krakow apartments');

      expectCalledWithPath(`${API_BASE}/tools/price-analysis`);
      const init = mockFetch.mock.calls[0][1] as RequestInit;
      expect(init.method).toBe('POST');
      expect(JSON.parse(init.body as string)).toEqual({ query: 'Krakow apartments' });
      expect(response.count).toBe(150);
      expect(response.distribution_by_type.apartment).toBe(100);
    });

    it('throws on error', async () => {
      mockFetch.mockResolvedValueOnce(createErrorResponse('Error', 500));

      await expect(priceAnalysisApi('bad query')).rejects.toThrow(ApiError);
    });
  });

  // =========================================================================
  // locationAnalysisApi
  // =========================================================================

  describe('locationAnalysisApi', () => {
    it('analyses location via POST', async () => {
      const result = { property_id: 'prop-1', city: 'Krakow', lat: 50.06, lon: 19.94 };
      mockFetch.mockResolvedValueOnce(createMockResponse(result));

      const response = await locationAnalysisApi('prop-1');

      expectCalledWithPath(`${API_BASE}/tools/location-analysis`);
      const init = mockFetch.mock.calls[0][1] as RequestInit;
      expect(init.method).toBe('POST');
      expect(JSON.parse(init.body as string)).toEqual({ property_id: 'prop-1' });
      expect(response.city).toBe('Krakow');
    });

    it('throws on error', async () => {
      mockFetch.mockResolvedValueOnce(createErrorResponse('Not found', 404));

      await expect(locationAnalysisApi('bad-id')).rejects.toThrow(ApiError);
    });
  });

  // =========================================================================
  // valuationApi
  // =========================================================================

  describe('valuationApi', () => {
    it('gets valuation via POST', async () => {
      const result = { property_id: 'prop-1', estimated_value: 320000 };
      mockFetch.mockResolvedValueOnce(createMockResponse(result));

      const response = await valuationApi({ property_id: 'prop-1' });

      expectCalledWithPath(`${API_BASE}/tools/valuation`);
      const init = mockFetch.mock.calls[0][1] as RequestInit;
      expect(init.method).toBe('POST');
      expect(JSON.parse(init.body as string)).toEqual({ property_id: 'prop-1' });
      expect(response.estimated_value).toBe(320000);
    });

    it('throws on error', async () => {
      mockFetch.mockResolvedValueOnce(createErrorResponse('Error', 500));

      await expect(valuationApi({ property_id: 'bad' })).rejects.toThrow(ApiError);
    });
  });

  // =========================================================================
  // legalCheckApi
  // =========================================================================

  describe('legalCheckApi', () => {
    it('checks legal text via POST', async () => {
      const result = { risks: [{ type: 'warning', text: 'Check zoning' }], score: 75 };
      mockFetch.mockResolvedValueOnce(createMockResponse(result));

      const response = await legalCheckApi('Some contract text');

      expectCalledWithPath(`${API_BASE}/tools/legal-check`);
      const init = mockFetch.mock.calls[0][1] as RequestInit;
      expect(init.method).toBe('POST');
      expect(JSON.parse(init.body as string)).toEqual({ text: 'Some contract text' });
      expect(response.risks).toHaveLength(1);
      expect(response.score).toBe(75);
    });

    it('throws on error', async () => {
      mockFetch.mockResolvedValueOnce(createErrorResponse('Error', 500));

      await expect(legalCheckApi('text')).rejects.toThrow(ApiError);
    });
  });

  // =========================================================================
  // enrichAddressApi
  // =========================================================================

  describe('enrichAddressApi', () => {
    it('enriches address via POST', async () => {
      const result = { address: 'Krakow, Poland', data: { lat: 50.06, lon: 19.94 } };
      mockFetch.mockResolvedValueOnce(createMockResponse(result));

      const response = await enrichAddressApi('Krakow, Poland');

      expectCalledWithPath(`${API_BASE}/tools/enrich-address`);
      const init = mockFetch.mock.calls[0][1] as RequestInit;
      expect(init.method).toBe('POST');
      expect(JSON.parse(init.body as string)).toEqual({ address: 'Krakow, Poland' });
      expect(response.address).toBe('Krakow, Poland');
    });

    it('throws on error', async () => {
      mockFetch.mockResolvedValueOnce(createErrorResponse('Error', 500));

      await expect(enrichAddressApi('bad address')).rejects.toThrow(ApiError);
    });
  });

  // =========================================================================
  // calculateAdvancedInvestment
  // =========================================================================

  describe('calculateAdvancedInvestment', () => {
    it('calculates advanced investment via POST with credentials', async () => {
      const result = { projections: [], risk_score: 0.3 };
      mockFetch.mockResolvedValueOnce(createMockResponse(result));

      const input = { property_price: 300000, holding_period_years: 10 };
      const response = await calculateAdvancedInvestment(input);

      expectCalledWithPath(`${API_BASE}/tools/advanced-investment-analysis`);
      const init = mockFetch.mock.calls[0][1] as RequestInit;
      expect(init.method).toBe('POST');
      expect(init.credentials).toBe('include');
      expect(response.risk_score).toBe(0.3);
    });

    it('handles network failure (safeFetch)', async () => {
      mockFetch.mockRejectedValueOnce(new TypeError('Failed to fetch'));

      try {
        await calculateAdvancedInvestment({ property_price: 100000 });
        fail('Expected ApiError');
      } catch (error) {
        expect(error).toBeInstanceOf(ApiError);
        expect((error as ApiError).category).toBe('network');
      }
    });
  });

  // =========================================================================
  // analyzePortfolio
  // =========================================================================

  describe('analyzePortfolio', () => {
    it('analyzes portfolio via POST with credentials', async () => {
      const result = { total_value: 1500000, diversification_score: 0.8 };
      mockFetch.mockResolvedValueOnce(createMockResponse(result));

      const input = { properties: [{ property_id: 'p1', purchase_price: 300000 }] };
      const response = await analyzePortfolio(input);

      expectCalledWithPath(`${API_BASE}/tools/portfolio-analysis`);
      const init = mockFetch.mock.calls[0][1] as RequestInit;
      expect(init.method).toBe('POST');
      expect(init.credentials).toBe('include');
      expect(response.diversification_score).toBe(0.8);
    });

    it('throws on error', async () => {
      mockFetch.mockResolvedValueOnce(createErrorResponse('Unauthorized', 401));

      await expect(analyzePortfolio({ properties: [] })).rejects.toThrow(ApiError);
    });
  });

  // =========================================================================
  // calculateRentVsBuy
  // =========================================================================

  describe('calculateRentVsBuy', () => {
    it('calculates rent vs buy via POST with credentials', async () => {
      const result = { break_even_years: 7, recommendation: 'buy', total_buy_cost: 500000 };
      mockFetch.mockResolvedValueOnce(createMockResponse(result));

      const input = { property_price: 300000, monthly_rent: 1500, holding_period_years: 15 };
      const response = await calculateRentVsBuy(input);

      expectCalledWithPath(`${API_BASE}/tools/rent-vs-buy`);
      const init = mockFetch.mock.calls[0][1] as RequestInit;
      expect(init.method).toBe('POST');
      expect(init.credentials).toBe('include');
      expect(response.break_even_years).toBe(7);
    });

    it('throws on error', async () => {
      mockFetch.mockResolvedValueOnce(createErrorResponse('Error', 500));

      await expect(calculateRentVsBuy({ property_price: 0 })).rejects.toThrow(ApiError);
    });
  });

  // =========================================================================
  // generateListing
  // =========================================================================

  describe('generateListing', () => {
    it('generates listing via POST with credentials', async () => {
      const result = {
        description: 'Beautiful apartment',
        headlines: ['Stunning apartment in Krakow'],
        social_media: { facebook: 'Check this out!' },
      };
      mockFetch.mockResolvedValueOnce(createMockResponse(result));

      const input = { property_id: 'prop-1', tone: 'professional' as const, language: 'en' };
      const response = await generateListing(input);

      expectCalledWithPath(`${API_BASE}/tools/generate-listing`);
      const init = mockFetch.mock.calls[0][1] as RequestInit;
      expect(init.method).toBe('POST');
      expect(init.credentials).toBe('include');
      expect(response.description).toBe('Beautiful apartment');
    });

    it('throws on error', async () => {
      mockFetch.mockResolvedValueOnce(createErrorResponse('Error', 500));

      await expect(generateListing({ property_id: 'bad' })).rejects.toThrow(ApiError);
    });
  });

  // =========================================================================
  // calculateCommuteTime
  // =========================================================================

  describe('calculateCommuteTime', () => {
    it('calculates commute time via POST with credentials', async () => {
      const result = { duration_minutes: 25, distance_km: 12.5, route_summary: 'Main road' };
      mockFetch.mockResolvedValueOnce(createMockResponse(result));

      const input = {
        origin: { lat: 50.06, lng: 19.94 },
        destination: { lat: 52.22, lng: 21.01 },
        mode: 'driving' as const,
      };
      const response = await calculateCommuteTime(input);

      expectCalledWithPath(`${API_BASE}/tools/commute-time`);
      const init = mockFetch.mock.calls[0][1] as RequestInit;
      expect(init.method).toBe('POST');
      expect(init.credentials).toBe('include');
      expect(response.duration_minutes).toBe(25);
    });

    it('throws on error', async () => {
      mockFetch.mockResolvedValueOnce(createErrorResponse('Bad request', 400));

      await expect(
        calculateCommuteTime({
          origin: { lat: 0, lng: 0 },
          destination: { lat: 0, lng: 0 },
        })
      ).rejects.toThrow(ApiError);
    });
  });

  // =========================================================================
  // rankPropertiesByCommute
  // =========================================================================

  describe('rankPropertiesByCommute', () => {
    it('ranks properties by commute via POST with credentials', async () => {
      const result = {
        rankings: [
          { property_id: 'p1', duration_minutes: 15 },
          { property_id: 'p2', duration_minutes: 30 },
        ],
      };
      mockFetch.mockResolvedValueOnce(createMockResponse(result));

      const input = {
        property_ids: ['p1', 'p2'],
        destination: { lat: 52.22, lng: 21.01 },
        mode: 'transit' as const,
      };
      const response = await rankPropertiesByCommute(input);

      expectCalledWithPath(`${API_BASE}/tools/commute-ranking`);
      const init = mockFetch.mock.calls[0][1] as RequestInit;
      expect(init.method).toBe('POST');
      expect(init.credentials).toBe('include');
      expect(response.rankings).toHaveLength(2);
    });

    it('throws on error', async () => {
      mockFetch.mockResolvedValueOnce(createErrorResponse('Error', 500));

      await expect(
        rankPropertiesByCommute({
          property_ids: [],
          destination: { lat: 0, lng: 0 },
        })
      ).rejects.toThrow(ApiError);
    });
  });

  // =========================================================================
  // Re-exports
  // =========================================================================

  describe('re-exports', () => {
    it('exports ApiError class from client', () => {
      expect(ApiError).toBeDefined();
      const err = new ApiError('test', 500);
      expect(err).toBeInstanceOf(Error);
      expect(err.name).toBe('ApiError');
      expect(err.status).toBe(500);
    });
  });
});
