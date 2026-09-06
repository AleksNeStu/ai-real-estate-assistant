/**
 * Tools API: mortgage calculator, TCO calculator, investment analysis,
 * neighborhood quality, property comparison, price analysis, location analysis,
 * valuation, legal check, address enrichment, advanced investment, rent-vs-buy,
 * listing generation, commute time.
 */

import type {
  MortgageInput,
  MortgageResult,
  TCOInput,
  TCOResult,
  TCOComparisonInput,
  TCOComparisonResult,
  TCOLocationDefaults,
  AvailableLocationsResponse,
  InvestmentAnalysisInput,
  InvestmentAnalysisResult,
  NeighborhoodQualityInput,
  NeighborhoodQualityResult,
  // Task #39: Advanced Investment Analytics
  AdvancedInvestmentInput,
  AdvancedInvestmentResult,
  PortfolioAnalysisInput,
  PortfolioAnalysisResult,
  // Task #42: Rent vs Buy Calculator
  RentVsBuyInput,
  RentVsBuyResult,
  // Task #54: Listing Generation
  ListingGenerationRequest,
  ListingGenerationResult,
  // Task #51: Commute Time Analysis
  CommuteTimeRequest,
  CommuteTimeResponse,
  CommuteRankingRequest,
  CommuteRankingResponse,
} from '../types';

import { getApiUrl, buildHeaders, safeFetch, handleResponse } from './client';

// Re-export client types used in signatures
export type { ApiErrorCategory } from './client';
export { ApiError } from './client';

export async function calculateMortgage(input: MortgageInput): Promise<MortgageResult> {
  const response = await fetch(`${getApiUrl()}/tools/mortgage-calculator`, {
    method: 'POST',
    headers: buildHeaders(),
    body: JSON.stringify(input),
  });
  return handleResponse<MortgageResult>(response);
}

export async function calculateTCO(input: TCOInput): Promise<TCOResult> {
  const response = await fetch(`${getApiUrl()}/tools/tco-calculator`, {
    method: 'POST',
    headers: buildHeaders(),
    body: JSON.stringify(input),
  });
  return handleResponse<TCOResult>(response);
}

// Task #52: TCO Comparison API
export async function compareTCO(input: TCOComparisonInput): Promise<TCOComparisonResult> {
  const response = await fetch(`${getApiUrl()}/tools/tco-comparison`, {
    method: 'POST',
    headers: buildHeaders(),
    body: JSON.stringify(input),
  });
  return handleResponse<TCOComparisonResult>(response);
}

// Task #52: Location Defaults API
export async function getTCOLocationDefaults(
  country: string,
  region?: string
): Promise<TCOLocationDefaults> {
  const params = new URLSearchParams({ country });
  if (region) {
    params.append('region', region);
  }
  const response = await fetch(`${getApiUrl()}/tools/tco-location-defaults?${params.toString()}`, {
    method: 'GET',
    headers: buildHeaders(),
  });
  return handleResponse<TCOLocationDefaults>(response);
}

export async function getTCOAvailableLocations(): Promise<AvailableLocationsResponse> {
  const response = await fetch(`${getApiUrl()}/tools/tco-available-locations`, {
    method: 'GET',
    headers: buildHeaders(),
  });
  return handleResponse<AvailableLocationsResponse>(response);
}

export async function calculateInvestment(
  input: InvestmentAnalysisInput
): Promise<InvestmentAnalysisResult> {
  const response = await fetch(`${getApiUrl()}/tools/investment-analysis`, {
    method: 'POST',
    headers: buildHeaders(),
    body: JSON.stringify(input),
  });
  return handleResponse<InvestmentAnalysisResult>(response);
}

export async function neighborhoodQualityApi(
  input: NeighborhoodQualityInput
): Promise<NeighborhoodQualityResult> {
  const response = await fetch(`${getApiUrl()}/tools/neighborhood-quality`, {
    method: 'POST',
    headers: buildHeaders(),
    body: JSON.stringify(input),
  });
  return handleResponse<NeighborhoodQualityResult>(response);
}

/**
 * Convenience function to get neighborhood badge data for a property.
 * Can be used directly on property cards with property data.
 *
 * @param property - Property object with id, latitude, longitude, city, neighborhood
 * @returns Neighborhood quality result for badge display
 */
export async function getNeighborhoodBadge(property: {
  id?: string;
  latitude?: number;
  longitude?: number;
  city?: string;
  neighborhood?: string;
}): Promise<NeighborhoodQualityResult> {
  return neighborhoodQualityApi({
    property_id: property.id || 'unknown',
    latitude: property.latitude,
    longitude: property.longitude,
    city: property.city,
    neighborhood: property.neighborhood,
  });
}

export async function comparePropertiesApi(propertyIds: string[]) {
  const response = await fetch(`${getApiUrl()}/tools/compare-properties`, {
    method: 'POST',
    headers: buildHeaders(),
    body: JSON.stringify({ property_ids: propertyIds }),
  });
  return handleResponse<{
    properties: Array<{
      id?: string;
      price?: number;
      price_per_sqm?: number;
      city?: string;
      rooms?: number;
      bathrooms?: number;
      area_sqm?: number;
      year_built?: number;
      property_type?: string;
    }>;
    summary: { count: number; min_price?: number; max_price?: number; price_difference?: number };
  }>(response);
}

export async function priceAnalysisApi(query: string) {
  const response = await fetch(`${getApiUrl()}/tools/price-analysis`, {
    method: 'POST',
    headers: buildHeaders(),
    body: JSON.stringify({ query }),
  });
  return handleResponse<{
    query: string;
    count: number;
    average_price?: number;
    median_price?: number;
    min_price?: number;
    max_price?: number;
    average_price_per_sqm?: number;
    median_price_per_sqm?: number;
    distribution_by_type: Record<string, number>;
  }>(response);
}

export async function locationAnalysisApi(propertyId: string) {
  const response = await fetch(`${getApiUrl()}/tools/location-analysis`, {
    method: 'POST',
    headers: buildHeaders(),
    body: JSON.stringify({ property_id: propertyId }),
  });
  return handleResponse<{
    property_id: string;
    city?: string;
    neighborhood?: string;
    lat?: number;
    lon?: number;
  }>(response);
}

export async function valuationApi(propertyId: string) {
  const response = await fetch(`${getApiUrl()}/tools/valuation`, {
    method: 'POST',
    headers: buildHeaders(),
    body: JSON.stringify({ property_id: propertyId }),
  });
  return handleResponse<{ property_id: string; estimated_value: number }>(response);
}

export async function legalCheckApi(text: string) {
  const response = await fetch(`${getApiUrl()}/tools/legal-check`, {
    method: 'POST',
    headers: buildHeaders(),
    body: JSON.stringify({ text }),
  });
  return handleResponse<{ risks: Array<Record<string, unknown>>; score: number }>(response);
}

export async function enrichAddressApi(address: string) {
  const response = await fetch(`${getApiUrl()}/tools/enrich-address`, {
    method: 'POST',
    headers: buildHeaders(),
    body: JSON.stringify({ address }),
  });
  return handleResponse<{ address: string; data: Record<string, unknown> }>(response);
}

// ============================================================================
// Task #39: Advanced Investment Analytics
// ============================================================================

/**
 * Calculate advanced investment analysis with multi-year projections,
 * tax implications, appreciation scenarios, and risk assessment.
 */
export async function calculateAdvancedInvestment(
  input: AdvancedInvestmentInput
): Promise<AdvancedInvestmentResult> {
  const response = await safeFetch(`${getApiUrl()}/tools/advanced-investment-analysis`, {
    method: 'POST',
    headers: buildHeaders(),
    credentials: 'include',
    body: JSON.stringify(input),
  });
  return handleResponse<AdvancedInvestmentResult>(response);
}

/**
 * Analyze a portfolio of investment properties including aggregate metrics,
 * diversification scores, and risk assessment.
 */
export async function analyzePortfolio(
  input: PortfolioAnalysisInput
): Promise<PortfolioAnalysisResult> {
  const response = await safeFetch(`${getApiUrl()}/tools/portfolio-analysis`, {
    method: 'POST',
    headers: buildHeaders(),
    credentials: 'include',
    body: JSON.stringify(input),
  });
  return handleResponse<PortfolioAnalysisResult>(response);
}

/**
 * Task #42: Calculate rent vs buy comparison.
 * Compares the financial implications of renting vs buying a property over time,
 * including break-even analysis, opportunity costs, and tax benefits.
 */
export async function calculateRentVsBuy(input: RentVsBuyInput): Promise<RentVsBuyResult> {
  const response = await safeFetch(`${getApiUrl()}/tools/rent-vs-buy`, {
    method: 'POST',
    headers: buildHeaders(),
    credentials: 'include',
    body: JSON.stringify(input),
  });
  return handleResponse<RentVsBuyResult>(response);
}

// ============================================================================
// Task #54: Listing Generation
// ============================================================================

/**
 * Generate AI-powered listing content for a property.
 *
 * Generates:
 * - Property description with customizable tone and language
 * - Multiple headline variants for different platforms
 * - Platform-specific social media content
 *
 * All generated content respects platform character limits.
 */
export async function generateListing(
  input: ListingGenerationRequest
): Promise<ListingGenerationResult> {
  const response = await safeFetch(`${getApiUrl()}/tools/generate-listing`, {
    method: 'POST',
    headers: buildHeaders(),
    credentials: 'include',
    body: JSON.stringify(input),
  });
  return handleResponse<ListingGenerationResult>(response);
}

// Task #51: Commute Time Analysis

/**
 * Calculate commute time from a single property to a destination.
 * Uses Google Routes API for accurate routing with real-time traffic.
 */
export async function calculateCommuteTime(
  input: CommuteTimeRequest
): Promise<CommuteTimeResponse> {
  const response = await safeFetch(`${getApiUrl()}/tools/commute-time`, {
    method: 'POST',
    headers: buildHeaders(),
    credentials: 'include',
    body: JSON.stringify(input),
  });
  return handleResponse<CommuteTimeResponse>(response);
}

/**
 * Rank multiple properties by commute time to a destination.
 * Returns properties sorted by commute duration (fastest first).
 */
export async function rankPropertiesByCommute(
  input: CommuteRankingRequest
): Promise<CommuteRankingResponse> {
  const response = await safeFetch(`${getApiUrl()}/tools/commute-ranking`, {
    method: 'POST',
    headers: buildHeaders(),
    credentials: 'include',
    body: JSON.stringify(input),
  });
  return handleResponse<CommuteRankingResponse>(response);
}

// ============================================================================
// v5.1: AI Price Forecast with Multi-Year Projection
// ============================================================================

export interface PriceForecastRequest {
  property_id?: string;
  property_features?: Record<string, unknown>;
  horizon_years?: number[];
}

export interface ForecastPoint {
  years_ahead: number;
  estimated_value: number;
  lower_bound: number;
  upper_bound: number;
}

export interface PriceForecastResponse {
  current_estimate: number;
  currency: string;
  horizon_years: number[];
  forecast: ForecastPoint[];
  confidence: number;
  drivers: string[];
  explanation: string;
  comparables_used: number;
  median_price_per_sqm?: number | null;
  neighborhood_median_price_per_sqm?: number | null;
  disclaimer: string;
}

/**
 * Estimate current value and project value at 1y/3y/5y horizons.
 *
 * Either property_id OR property_features must be supplied.
 */
export async function priceForecastApi(
  input: PriceForecastRequest
): Promise<PriceForecastResponse> {
  const response = await safeFetch(`${getApiUrl()}/tools/price-forecast`, {
    method: 'POST',
    headers: buildHeaders(),
    credentials: 'include',
    body: JSON.stringify(input),
  });
  return handleResponse<PriceForecastResponse>(response);
}

// ============================================================================
// v5.1: AI Neighborhood One-Liner
// ============================================================================

export interface NeighborhoodSummaryRequest {
  city?: string;
  neighborhood?: string;
  property_type?: string;
  rooms?: number;
  area_sqm?: number;
  language?: string;
  max_sentences?: number;
}

export interface NeighborhoodSummaryResponse {
  summary: string;
  language: string;
}

/**
 * Generate a 2-3 sentence AI summary of a neighborhood.
 */
export async function neighborhoodSummaryApi(
  input: NeighborhoodSummaryRequest
): Promise<NeighborhoodSummaryResponse> {
  const response = await safeFetch(`${getApiUrl()}/tools/neighborhood-summary`, {
    method: 'POST',
    headers: buildHeaders(),
    credentials: 'include',
    body: JSON.stringify(input),
  });
  return handleResponse<NeighborhoodSummaryResponse>(response);
}
