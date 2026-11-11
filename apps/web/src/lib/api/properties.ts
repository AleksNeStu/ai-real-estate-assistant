/**
 * Properties API: one property, its price history and its comparables.
 *
 * These three calls feed the property page - the route that shows a single
 * listing. The search answers with many; this answers with one.
 */

import type { Property, PriceSnapshot } from '../types';

import { getApiUrl, buildHeaders, safeFetch, handleResponse } from './client';

export interface RelatedPropertiesResponse {
  properties: Property[];
  count: number;
}

export interface PropertyPriceHistoryResponse {
  property_id: string;
  snapshots: PriceSnapshot[];
  total: number;
}

/**
 * One property, by its id.
 *
 * The page is public, so this call carries no session: a visitor who clicks a
 * listing is nobody until they sign in.
 */
export async function getProperty(propertyId: string): Promise<Property> {
  const response = await safeFetch(
    `${getApiUrl()}/properties/${encodeURIComponent(propertyId)}`,
    {
      method: 'GET',
      headers: buildHeaders(),
    }
  );
  return handleResponse<Property>(response);
}

/**
 * The recorded price points of one property.
 */
export async function getPropertyPriceHistory(
  propertyId: string
): Promise<PropertyPriceHistoryResponse> {
  const response = await safeFetch(
    `${getApiUrl()}/properties/${encodeURIComponent(propertyId)}/price-history`,
    {
      method: 'GET',
      headers: buildHeaders(),
    }
  );
  return handleResponse<PropertyPriceHistoryResponse>(response);
}

/**
 * The comparables: the other listings of the same city and type.
 */
export async function getRelatedProperties(
  propertyId: string,
  limit = 6
): Promise<RelatedPropertiesResponse> {
  const response = await safeFetch(
    `${getApiUrl()}/properties/${encodeURIComponent(propertyId)}/related?limit=${limit}`,
    {
      method: 'GET',
      headers: buildHeaders(),
    }
  );
  return handleResponse<RelatedPropertiesResponse>(response);
}
