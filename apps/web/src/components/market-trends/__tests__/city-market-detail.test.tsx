import { render, screen } from '@testing-library/react';

import { CityMarketDetail } from '../city-market-detail';
import { summariseCity } from '../city-market-stats';
import type { Property, SearchResultItem } from '@/lib/types';

/**
 * The city in detail.
 *
 * The panel draws a bar on one scale for the whole catalogue, and it says
 * plainly what is missing when the catalogue holds nothing for the city.
 */
function makeProperty(overrides: Partial<Property> = {}): Property {
  return {
    id: 'p1',
    title: 'Apartment',
    city: 'Warsaw',
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

const warsaw = summariseCity(
  'Warsaw',
  makeResults([
    makeProperty({ id: 'p1', price: 400000 }),
    makeProperty({ id: 'p2', price: 600000 }),
  ])
);

const lublin = summariseCity('Lublin', []);

describe('CityMarketDetail', () => {
  it('says nothing when no city is selected', () => {
    const { container } = render(<CityMarketDetail city={null} scale={1000000} />);

    expect(container).toBeEmptyDOMElement();
  });

  it('names the city and how many listings it holds', () => {
    render(<CityMarketDetail city={warsaw} scale={1000000} />);

    expect(screen.getByText('Warsaw')).toBeInTheDocument();
    expect(screen.getByText('2 listings')).toBeInTheDocument();
  });

  it('draws the price range on the scale of the catalogue', () => {
    render(<CityMarketDetail city={warsaw} scale={1000000} />);

    const bar = screen.getByTestId('price-range');
    // The range sits between 40 % and 60 % of the scale.
    expect(bar.querySelector('.bg-foreground')).toHaveStyle({
      left: '40%',
      width: '20%',
    });
    // The average marker stands at 50 %.
    expect(bar.querySelector('.bg-action')).toHaveStyle({ left: '50%' });
  });

  it('writes the three prices of the range', () => {
    render(<CityMarketDetail city={warsaw} scale={1000000} />);

    expect(screen.getByText('400,000')).toBeInTheDocument();
    expect(screen.getByText('avg 500,000')).toBeInTheDocument();
    expect(screen.getByText('600,000')).toBeInTheDocument();
  });

  it('offers the search of the city and the market trends', () => {
    render(<CityMarketDetail city={warsaw} scale={1000000} />);

    expect(screen.getByRole('link', { name: 'Search Warsaw' })).toHaveAttribute(
      'href',
      '/en/search?q=properties%20in%20Warsaw'
    );
    expect(screen.getByRole('link', { name: 'Market trends →' })).toHaveAttribute(
      'href',
      '/en/market-trends'
    );
  });

  it('says what is missing for a city the catalogue holds nothing for', () => {
    render(<CityMarketDetail city={lublin} scale={1000000} />);

    expect(screen.getByText(/holds no listings in Lublin/)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Open data sources →' })).toHaveAttribute(
      'href',
      '/en/admin#data-sources'
    );
    expect(screen.queryByTestId('price-range')).not.toBeInTheDocument();
  });
});
