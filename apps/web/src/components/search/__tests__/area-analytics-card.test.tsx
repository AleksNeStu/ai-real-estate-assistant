import { render, screen } from '@testing-library/react';

import { AreaAnalyticsCard } from '../area-analytics-card';
import type { Property, SearchResultItem } from '@/lib/types';

/**
 * The area analytics card, over the map.
 *
 * Every number on the card is computed from the listings the search
 * returned, so the cases that break a median are the cases worth a test: no
 * listings, a listing without a price, a listing without an area, and a
 * single listing in the area.
 */
function makeProperty(overrides: Partial<Property> = {}): Property {
  return {
    id: 'p1',
    title: 'Modern Apartment',
    city: 'Kraków',
    district: 'Nowa Huta',
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
    year_built: 2010,
    ...overrides,
  };
}

function makeResults(properties: Property[]): SearchResultItem[] {
  return properties.map((property, index) => ({ property, score: 0.95 - index * 0.05 }));
}

describe('AreaAnalyticsCard', () => {
  it('says so when there is nothing to analyse', () => {
    render(<AreaAnalyticsCard results={[]} />);

    expect(screen.getByText('Nothing to analyse yet')).toBeInTheDocument();
    // The card labels itself, but there is no statistic to state.
    expect(screen.getByText('area analytics')).toBeInTheDocument();
    expect(screen.queryByText('—')).not.toBeInTheDocument();
  });

  it('names the area the listings stand in', () => {
    render(<AreaAnalyticsCard results={makeResults([makeProperty()])} />);

    expect(screen.getByText('Nowa Huta')).toBeInTheDocument();
    expect(screen.getByText('area analytics')).toBeInTheDocument();
  });

  it('reads the three statistics of a single listing', () => {
    render(<AreaAnalyticsCard results={makeResults([makeProperty()])} />);

    // 500 000 over 50 m² is 10 000 zł per m², one listing, built in 2010.
    expect(screen.getByText('10,000')).toBeInTheDocument();
    expect(screen.getByText('PLN/m²')).toBeInTheDocument();
    expect(screen.getByText('1')).toBeInTheDocument();
    expect(screen.getByText('2010')).toBeInTheDocument();
  });

  it('takes the median of the listings in the area', () => {
    render(
      <AreaAnalyticsCard
        results={makeResults([
          makeProperty({ id: 'p1', price: 500000, area_sqm: 50, year_built: 2010 }),
          makeProperty({ id: 'p2', price: 1000000, area_sqm: 50, year_built: 2014 }),
          makeProperty({ id: 'p3', price: 1500000, area_sqm: 50, year_built: 2012 }),
        ])}
      />
    );

    // 10 000, 20 000 and 30 000 zł per m² - the middle one is the median.
    expect(screen.getByText('20,000')).toBeInTheDocument();
    expect(screen.getByText('3')).toBeInTheDocument();
    expect(screen.getByText('2012')).toBeInTheDocument();
  });

  it('leaves out a listing without a price', () => {
    render(
      <AreaAnalyticsCard
        results={makeResults([
          makeProperty({ id: 'p1', price: 500000, area_sqm: 50 }),
          makeProperty({ id: 'p2', price: undefined, area_sqm: 50 }),
        ])}
      />
    );

    // The listing without a price is still a listing in the area.
    expect(screen.getByText('2')).toBeInTheDocument();
    expect(screen.getByText('10,000')).toBeInTheDocument();
  });

  it('leaves out a listing without an area', () => {
    render(
      <AreaAnalyticsCard
        results={makeResults([
          makeProperty({ id: 'p1', price: 500000, area_sqm: 50 }),
          makeProperty({ id: 'p2', price: 500000, area_sqm: undefined }),
        ])}
      />
    );

    expect(screen.getByText('2')).toBeInTheDocument();
    expect(screen.getByText('10,000')).toBeInTheDocument();
  });

  it('has no median per m² when no listing carries both a price and an area', () => {
    render(
      <AreaAnalyticsCard
        results={makeResults([makeProperty({ price: undefined, area_sqm: undefined })])}
      />
    );

    expect(screen.getByText('—')).toBeInTheDocument();
    expect(screen.getByText('1')).toBeInTheDocument();
  });

  it('has no median year when no listing carries one', () => {
    render(
      <AreaAnalyticsCard
        results={makeResults([makeProperty({ year_built: undefined })])}
      />
    );

    expect(screen.getByText('—')).toBeInTheDocument();
    expect(screen.queryByText('2010')).not.toBeInTheDocument();
  });

  it('counts the area with the most listings', () => {
    render(
      <AreaAnalyticsCard
        results={makeResults([
          makeProperty({ id: 'p1', district: 'Nowa Huta' }),
          makeProperty({ id: 'p2', district: 'Nowa Huta' }),
          makeProperty({ id: 'p3', district: 'Czyżyny' }),
        ])}
      />
    );

    expect(screen.getByText('Nowa Huta')).toBeInTheDocument();
    expect(screen.getByText('2')).toBeInTheDocument();
    expect(screen.queryByText('Czyżyny')).not.toBeInTheDocument();
  });
});
