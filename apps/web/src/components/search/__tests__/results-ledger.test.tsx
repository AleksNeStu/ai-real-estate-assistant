import { render, screen } from '@testing-library/react';

import { ResultsLedger } from '../results-ledger';
import type { Property, SearchResultItem } from '@/lib/types';

/**
 * The results as a ledger of prices.
 *
 * The card that used to draw them needs the account and the favourites, so
 * the doubles stand in for it here - the ledger itself is what is under test.
 */
jest.mock('@/components/property', () => ({
  HeartButton: ({ propertyId }: { propertyId: string }) => (
    <button type="button" data-testid={`heart-${propertyId}`}>
      heart
    </button>
  ),
  ListingGenerator: ({ propertyId }: { propertyId: string }) => (
    <div data-testid={`listing-${propertyId}`}>listing</div>
  ),
}));

jest.mock('@/components/search/relevance-rating', () => ({
  RelevanceRating: ({ propertyId }: { propertyId: string }) => (
    <div data-testid={`rating-${propertyId}`}>rating</div>
  ),
}));

function makeProperty(overrides: Partial<Property> = {}): Property {
  return {
    id: 'p1',
    title: 'Modern Apartment',
    city: 'Berlin',
    district: 'Mitte',
    property_type: 'apartment',
    listing_type: 'rent',
    has_parking: false,
    has_garden: false,
    has_pool: false,
    has_garage: false,
    has_bike_room: false,
    price: 1200,
    currency: 'EUR',
    rooms: 2,
    area_sqm: 75,
    ...overrides,
  };
}

function makeResults(properties: Property[]): SearchResultItem[] {
  return properties.map((property, index) => ({ property, score: 0.95 - index * 0.05 }));
}

describe('ResultsLedger', () => {
  it('renders one row per listing, each carrying the property-card test id', () => {
    render(
      <ResultsLedger
        results={makeResults([
          makeProperty({ id: 'p1' }),
          makeProperty({ id: 'p2', title: 'Cozy Studio' }),
        ])}
        query="Berlin"
      />
    );

    const rows = screen.getAllByTestId('property-card');
    expect(rows).toHaveLength(2);
    expect(rows[0]).toHaveTextContent('Modern Apartment');
    expect(rows[1]).toHaveTextContent('Cozy Studio');
  });

  it('renders the price once', () => {
    render(
      <ResultsLedger
        results={makeResults([makeProperty({ price: 500000, currency: 'USD' })])}
        query="Berlin"
      />
    );

    // One price per listing: a second copy of it would break the specs that
    // find the price by its text.
    expect(screen.getAllByText('$500,000')).toHaveLength(1);
  });

  it('renders the price of a listing without one as a request', () => {
    render(
      <ResultsLedger
        results={makeResults([makeProperty({ price: undefined })])}
        query="Berlin"
      />
    );

    expect(screen.getByText('Price on request')).toBeInTheDocument();
  });

  it('names a listing without a title', () => {
    render(
      <ResultsLedger
        results={makeResults([makeProperty({ title: undefined })])}
        query="Berlin"
      />
    );

    expect(screen.getByText('Untitled Property')).toBeInTheDocument();
  });

  it('renders the place and the facts of a listing', () => {
    render(
      <ResultsLedger
        results={makeResults([makeProperty({ address: 'Mitte 1, Berlin' })])}
        query="Berlin"
      />
    );

    expect(screen.getByText('Mitte 1, Berlin')).toBeInTheDocument();
    // The facts share one line, so they are matched as a part of it.
    expect(screen.getByText(/2 beds/)).toBeInTheDocument();
    expect(screen.getByText(/75 m²/)).toBeInTheDocument();
  });

  it('renders the empty state when there is nothing to list', () => {
    render(<ResultsLedger results={[]} query="Berlin" />);

    expect(screen.getByText('No Results Found')).toBeInTheDocument();
    expect(screen.queryByTestId('property-card')).not.toBeInTheDocument();
  });
});
