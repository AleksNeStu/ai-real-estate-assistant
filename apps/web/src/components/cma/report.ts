import type { CMAReport } from '@/lib/types';

/**
 * The report as the API actually sends it.
 *
 * `CMAReport` in `lib/types` nests the subject under `subject_property` and
 * the market under `market_context`. The API sends neither: it returns the
 * subject flat (`subject_price`, `subject_area_sqm`, ...) and the market
 * flat (`market_trend`, `market_avg_price_per_sqm`, ...). The two shapes
 * disagree, and the flat one is the one on the wire - so the wizard reads
 * the flat fields and says so here.
 */
export interface CMAReportResponse extends CMAReport {
  subject_property_id?: string;
  subject_address?: string | null;
  subject_city?: string | null;
  subject_district?: string | null;
  subject_price?: number | null;
  subject_area_sqm?: number | null;
  subject_rooms?: number | null;
  subject_year_built?: number | null;
  subject_property_type?: string;
  market_trend?: string | null;
  market_avg_price_per_sqm?: number | null;
  market_inventory_days?: number | null;
}

/**
 * What the subject is asking for.
 *
 * The API sends the asking price with the report, and the wizard also
 * holds the property the reader picked - either of them is the number, and
 * the report's own wins when both are there.
 */
export function subjectPriceOf(
  report: CMAReportResponse | null,
  fallback?: number | null
): number | null {
  if (report && typeof report.subject_price === 'number') return report.subject_price;
  if (typeof fallback === 'number') return fallback;
  return null;
}
