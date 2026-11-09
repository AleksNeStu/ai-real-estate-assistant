import type { SearchResultItem } from '@/lib/types';

/**
 * The catalogue of cities the overview reads.
 *
 * The eight cities are the ones the demo catalogue serves, plus the four that
 * are on the map but hold nothing yet. A city with no listings is still a
 * row: the point of the route is what the catalogue covers and what it does
 * not, and a row that is simply missing says nothing.
 *
 * The coordinates are the cities' own - a map of Poland does not need the
 * catalogue to tell it where Warsaw is.
 */
export interface CityCatalogueEntry {
  /** The name the catalogue knows the city by. */
  name: string;
  /** The name the city is written with in the interface. */
  label: string;
  lat: number;
  lon: number;
}

export const CITY_CATALOGUE: CityCatalogueEntry[] = [
  { name: 'Warsaw', label: 'Warsaw', lat: 52.2297, lon: 21.0122 },
  { name: 'Krakow', label: 'Kraków', lat: 50.0647, lon: 19.945 },
  { name: 'Wroclaw', label: 'Wrocław', lat: 51.1079, lon: 17.0385 },
  { name: 'Gdansk', label: 'Gdańsk', lat: 54.352, lon: 18.6466 },
  { name: 'Poznan', label: 'Poznań', lat: 52.4064, lon: 16.9252 },
  { name: 'Lodz', label: 'Łódź', lat: 51.7592, lon: 19.456 },
  { name: 'Katowice', label: 'Katowice', lat: 50.2649, lon: 19.0238 },
  { name: 'Lublin', label: 'Lublin', lat: 51.2465, lon: 22.5684 },
];

export interface CityMarketSummary {
  /** The name the catalogue knows the city by. */
  city: string;
  /** The name the city is written with in the interface. */
  label: string;
  country: string;
  /** How many listings the catalogue holds for the city. */
  listingCount: number;
  /** The average asking price of those listings, or null when there are none. */
  avgPrice: number | null;
  minPrice: number | null;
  maxPrice: number | null;
  /** The average price per m², or null when no listing carries an area. */
  pricePerSqm: number | null;
  /** The currency the listings of this city are priced in. */
  currency?: string;
  lat: number;
  lon: number;
}

/**
 * What one city is worth, computed from the listings it has.
 *
 * Every number here comes out of the listings themselves: the average, the
 * smallest and the largest price, and the price per square metre. A city the
 * catalogue holds nothing for gets nulls, not zeroes - a zero average would
 * read as "the market is worth nothing", and the difference matters.
 */
export function summariseCity(
  city: string,
  results: SearchResultItem[]
): CityMarketSummary {
  const entry = CITY_CATALOGUE.find((c) => c.name === city) ?? {
    name: city,
    label: city,
    lat: 52.2297,
    lon: 21.0122,
  };

  const prices = results
    .map((item) => item.property?.price)
    .filter((price): price is number => typeof price === 'number' && price > 0);

  const perSqm = results
    .map((item) => item.property)
    .filter(
      (property): property is NonNullable<typeof property> =>
        typeof property?.price === 'number' &&
        property.price > 0 &&
        typeof property.area_sqm === 'number' &&
        property.area_sqm > 0
    )
    .map((property) => (property.price as number) / (property.area_sqm as number));

  const currency = results.find((item) => item.property?.currency)?.property?.currency;

  return {
    city: entry.name,
    label: entry.label,
    country: results[0]?.property?.country ?? 'Poland',
    listingCount: results.length,
    avgPrice: prices.length ? Math.round(prices.reduce((a, b) => a + b, 0) / prices.length) : null,
    minPrice: prices.length ? Math.min(...prices) : null,
    maxPrice: prices.length ? Math.max(...prices) : null,
    pricePerSqm: perSqm.length
      ? Math.round(perSqm.reduce((a, b) => a + b, 0) / perSqm.length)
      : null,
    currency,
    lat: entry.lat,
    lon: entry.lon,
  };
}

/**
 * The summaries of the whole catalogue, in the catalogue's order.
 *
 * Cities the catalogue holds nothing for are kept, with null numbers - the
 * route says what is missing as plainly as what is there.
 */
export function summariseCities(
  listingsByCity: Record<string, SearchResultItem[]>
): CityMarketSummary[] {
  return CITY_CATALOGUE.map((city) => summariseCity(city.name, listingsByCity[city.name] ?? []));
}

/**
 * The highest price any city in the catalogue reaches.
 *
 * It is the scale of the price-range bar: one ceiling for every city, so the
 * bars of two cities can be read against each other.
 */
export function priceScale(summaries: CityMarketSummary[]): number {
  const highest = summaries.reduce((max, summary) => Math.max(max, summary.maxPrice ?? 0), 0);
  return highest > 0 ? highest : 1;
}

/**
 * The currency unit a price is written in.
 *
 * The interface says the unit once, in the note under the ledger, and the
 * numbers stay bare - the same way the prototype writes them.
 */
export function currencyUnit(currency?: string): string {
  switch (currency) {
    case 'PLN':
      return 'zł';
    case 'EUR':
      return '€';
    case 'USD':
      return '$';
    default:
      return currency ?? '—';
  }
}
