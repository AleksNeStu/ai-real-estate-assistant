import {
  CITY_CATALOGUE,
  currencyUnit,
  priceScale,
  summariseCities,
  summariseCity,
} from '../city-market-stats';
import type { Property, SearchResultItem } from '@/lib/types';

/**
 * What a city is worth, computed from the listings it has.
 *
 * The cases that break a summary are the cases worth a test: a city with no
 * listings at all, a listing without a price, and a listing without an area.
 */
function makeProperty(overrides: Partial<Property> = {}): Property {
  return {
    id: 'p1',
    title: 'Apartment',
    city: 'Kraków',
    country: 'Poland',
    property_type: 'apartment',
    listing_type: 'sale',
    has_parking: false,
    has_garden: false,
    has_pool: false,
    has_garage: false,
    has_bike_room: false,
    price: 500000,
    currency: 'PLN',
    area_sqm: 50,
    ...overrides,
  } as Property;
}

function makeResults(properties: Property[]): SearchResultItem[] {
  return properties.map((property, index) => ({ property, score: 0.95 - index * 0.05 }));
}

describe('summariseCity', () => {
  it('reads the count, the average and the range of the listings', () => {
    const summary = summariseCity(
      'Krakow',
      makeResults([
        makeProperty({ id: 'p1', price: 400000 }),
        makeProperty({ id: 'p2', price: 600000 }),
        makeProperty({ id: 'p3', price: 800000 }),
      ])
    );

    expect(summary.city).toBe('Krakow');
    expect(summary.label).toBe('Kraków');
    expect(summary.listingCount).toBe(3);
    expect(summary.avgPrice).toBe(600000);
    expect(summary.minPrice).toBe(400000);
    expect(summary.maxPrice).toBe(800000);
  });

  it('computes the price per square metre from the listings', () => {
    const summary = summariseCity(
      'Krakow',
      makeResults([
        makeProperty({ id: 'p1', price: 500000, area_sqm: 50 }),
        makeProperty({ id: 'p2', price: 900000, area_sqm: 50 }),
      ])
    );

    // 10 000 and 18 000 zł per m² - the average of the two.
    expect(summary.pricePerSqm).toBe(14000);
  });

  it('leaves out a listing without a price', () => {
    const summary = summariseCity(
      'Krakow',
      makeResults([
        makeProperty({ id: 'p1', price: 500000 }),
        makeProperty({ id: 'p2', price: undefined }),
      ])
    );

    // The listing without a price is still a listing in the city.
    expect(summary.listingCount).toBe(2);
    expect(summary.avgPrice).toBe(500000);
  });

  it('leaves out a listing without an area from the price per m²', () => {
    const summary = summariseCity(
      'Krakow',
      makeResults([
        makeProperty({ id: 'p1', price: 500000, area_sqm: 50 }),
        makeProperty({ id: 'p2', price: 500000, area_sqm: undefined }),
      ])
    );

    expect(summary.listingCount).toBe(2);
    expect(summary.pricePerSqm).toBe(10000);
  });

  it('has no numbers at all for a city the catalogue holds nothing for', () => {
    const summary = summariseCity('Lublin', []);

    expect(summary.listingCount).toBe(0);
    expect(summary.avgPrice).toBeNull();
    expect(summary.minPrice).toBeNull();
    expect(summary.maxPrice).toBeNull();
    expect(summary.pricePerSqm).toBeNull();
  });

  it('carries the currency the listings are priced in', () => {
    const summary = summariseCity('Warsaw', makeResults([makeProperty({ currency: 'EUR' })]));

    expect(summary.currency).toBe('EUR');
  });
});

describe('summariseCities', () => {
  it('keeps the cities the catalogue holds nothing for', () => {
    const summaries = summariseCities({
      Warsaw: makeResults([makeProperty({ id: 'p1' })]),
    });

    expect(summaries).toHaveLength(CITY_CATALOGUE.length);
    expect(summaries[0].city).toBe('Warsaw');
    expect(summaries[0].listingCount).toBe(1);
    // Lodz holds nothing, and still gets a row.
    const lodz = summaries.find((city) => city.city === 'Lodz');
    expect(lodz).toBeDefined();
    expect(lodz?.listingCount).toBe(0);
  });
});

describe('priceScale', () => {
  it('is the highest price the catalogue reaches', () => {
    const scale = priceScale([
      summariseCity('Warsaw', makeResults([makeProperty({ price: 400000 })])),
      summariseCity('Krakow', makeResults([makeProperty({ price: 900000 })])),
    ]);

    expect(scale).toBe(900000);
  });

  it('never divides by zero', () => {
    expect(priceScale([])).toBe(1);
  });
});

describe('currencyUnit', () => {
  it('writes the unit the price is read in', () => {
    expect(currencyUnit('PLN')).toBe('zł');
    expect(currencyUnit('EUR')).toBe('€');
    expect(currencyUnit('USD')).toBe('$');
    expect(currencyUnit('CHF')).toBe('CHF');
    expect(currencyUnit(undefined)).toBe('—');
  });
});
