/**
 * The place pages: what the official register holds for a city or a district.
 *
 * A place has no flat to price, so there is no estimate here - there is the
 * price a square metre costs there, the registered sales that figure is
 * measured on, the period those sales cover and the sales themselves. The
 * four belong together, and the endpoint always sends them together.
 */

import type { ValuationComparable } from './tools';

/** One district of a city, and the link that names it. */
export interface PlaceDistrict {
  name: string;
  slug: string;
}

/** One city the site knows, and the districts it stands on. */
export interface PlaceSummary {
  name: string;
  slug: string;
  register_city: string;
  districts: PlaceDistrict[];
}

/** The places of this deployment. */
export interface PlaceCatalogue {
  places: PlaceSummary[];
}

/** What the register says about a place, and on what evidence. */
export interface PlaceFigures {
  place: string;
  slug: string;
  district: string;
  district_slug: string;
  median_price_per_sqm: number | null;
  first_quartile_price_per_sqm: number | null;
  third_quartile_price_per_sqm: number | null;
  currency: string;
  source: string;
  confidence: string | null;
  sample_size: number;
  registered_count: number | null;
  comparison_area: string | null;
  period_start: string | null;
  period_end: string | null;
  notes: string[];
  comparables: ValuationComparable[];
  districts: PlaceDistrict[];
}
