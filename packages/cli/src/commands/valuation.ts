/**
 * `propvector valuation` - value an address or a catalogue property.
 *
 * The answer comes from the official register of notarial prices when the
 * place is named by its address, and from the catalogue when it is named by
 * its id. The client does not choose between them: it sends what it was
 * told and prints what came back.
 */

import type { ApiClient } from '../client.js';
import { OPERATIONS } from '../contract.js';
import type { ValuationRequest, ValuationResponse } from '../generated/openapi.js';
import { field, formatMoney, formatNumber } from '../format.js';

export interface ValuationOptions {
  readonly city?: string;
  readonly street?: string;
  readonly areaSqm?: number;
  readonly rooms?: number;
  readonly propertyId?: string;
}

/** The request the contract describes, with only the fields that were given. */
export function buildValuationRequest(options: ValuationOptions): ValuationRequest {
  const request: ValuationRequest = {};
  if (options.city) request.city = options.city;
  if (options.street) request.street = options.street;
  if (options.areaSqm !== undefined) request.area_sqm = options.areaSqm;
  if (options.rooms !== undefined) request.rooms = options.rooms;
  if (options.propertyId) request.property_id = options.propertyId;
  return request;
}

export async function runValuation(
  client: ApiClient,
  options: ValuationOptions,
): Promise<ValuationResponse> {
  return client.post<ValuationResponse>(
    OPERATIONS.valuation.relative,
    buildValuationRequest(options),
  );
}

/** The answer as a person reads it. */
export function formatValuation(valuation: ValuationResponse): string {
  const lines: string[] = [];
  const currency = valuation.currency || 'PLN';

  lines.push(field('estimated value', formatMoney(valuation.estimated_value, currency)));

  if (valuation.low !== null && valuation.low !== undefined) {
    lines.push(
      field(
        'range',
        `${formatMoney(valuation.low, currency)} - ${formatMoney(valuation.high, currency)}`,
      ),
    );
  }
  if (valuation.price_per_sqm_median !== null && valuation.price_per_sqm_median !== undefined) {
    lines.push(
      field('price per m2', `${formatMoney(valuation.price_per_sqm_median, currency)}/m2`),
    );
  }
  if (valuation.comparison_area) {
    lines.push(field('comparison area', valuation.comparison_area));
  }
  if (valuation.period_start || valuation.period_end) {
    lines.push(
      field('period', `${valuation.period_start ?? '?'} - ${valuation.period_end ?? '?'}`),
    );
  }
  if (valuation.sample_size !== null && valuation.sample_size !== undefined) {
    lines.push(field('sales in the sample', formatNumber(valuation.sample_size)));
  }
  if (valuation.source) {
    lines.push(field('source', valuation.source));
  }
  if (valuation.confidence) {
    lines.push(field('confidence', valuation.confidence));
  }

  const comparables = valuation.comparables ?? [];
  if (comparables.length) {
    lines.push('');
    lines.push(`comparables (${comparables.length}):`);
    for (const comparable of comparables) {
      lines.push(
        `  ${comparable.address} - ${formatNumber(comparable.area_sqm)} m2 - ` +
          `${formatMoney(comparable.price, currency)} - ` +
          `${formatMoney(comparable.price_per_sqm, currency)}/m2 - ` +
          `${comparable.transaction_date}`,
      );
    }
  }

  const notes = valuation.notes ?? [];
  if (notes.length) {
    lines.push('');
    for (const note of notes) lines.push(`note: ${note}`);
  }

  return lines.join('\n');
}
