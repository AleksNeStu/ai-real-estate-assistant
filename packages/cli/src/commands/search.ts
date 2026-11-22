/**
 * `propvector search` - search the catalogue.
 *
 * The query is the only thing that is required; everything else narrows it.
 */

import type { ApiClient } from '../client.js';
import { OPERATIONS } from '../contract.js';
import type {
  SearchRequest,
  SearchResponse,
  SortField,
  SortOrder,
} from '../generated/openapi.js';
import { field, formatMoney, formatNumber } from '../format.js';

export interface SearchOptions {
  readonly query: string;
  readonly limit?: number;
  readonly sortBy?: SortField;
  readonly sortOrder?: SortOrder;
}

/** The request the contract describes, with only the fields that were given. */
export function buildSearchRequest(options: SearchOptions): SearchRequest {
  const request: SearchRequest = { query: options.query };
  if (options.limit !== undefined) request.limit = options.limit;
  if (options.sortBy) request.sort_by = options.sortBy;
  if (options.sortOrder) request.sort_order = options.sortOrder;
  return request;
}

export async function runSearch(
  client: ApiClient,
  options: SearchOptions,
): Promise<SearchResponse> {
  return client.post<SearchResponse>(OPERATIONS.search.relative, buildSearchRequest(options));
}

/** The answer as a person reads it. */
export function formatSearch(response: SearchResponse): string {
  const lines: string[] = [];
  lines.push(field('results', formatNumber(response.count)));

  for (const [index, item] of (response.results ?? []).entries()) {
    const property = item.property;
    const place = [property?.address ?? property?.title, property?.city]
      .filter((part) => Boolean(part))
      .join(', ');
    const price = formatMoney(property?.price ?? null, property?.currency ?? null);
    const area = property?.area_sqm ? `${formatNumber(property.area_sqm)} m2` : '-';
    lines.push(`  ${index + 1}. ${place || '-'} - ${price} - ${area} - score ${item.score}`);
  }

  return lines.join('\n');
}
