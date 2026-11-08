import { render, screen } from '@testing-library/react';

import { PropertyCard } from '../property-card';
import type { Property } from '@/lib/types';

// The card records a view of the property in the visitor's profile. The
// test is about what the card shows, not about the tracking.
jest.mock('@/hooks/useLeadTracking', () => ({
  useLeadTracking: () => ({
    trackPropertyView: () => ({ stopTracking: jest.fn() }),
  }),
}));

// The heart button drags the favourites context and the router into the
// test; the card is not about the favourite.
jest.mock('../heart-button', () => ({
  HeartButton: () => null,
}));

const listing: Property = {
  id: 'prop-0001',
  title: 'Two-room apartment in Kazimierz',
  address: 'ul. Długa 42, Kazimierz, Kraków, Poland',
  city: 'Kraków',
  country: 'Poland',
  property_type: 'apartment',
  listing_type: 'sale',
  price: 620000,
  currency: 'PLN',
  rooms: 2,
  bathrooms: 1,
  area_sqm: 58,
};

describe('PropertyCard', () => {
  it('shows the title of the listing', () => {
    render(<PropertyCard property={listing} />);

    expect(screen.getByText('Two-room apartment in Kazimierz')).toBeInTheDocument();
  });

  it('shows the address of the listing', () => {
    render(<PropertyCard property={listing} />);

    expect(screen.getByText('ul. Długa 42, Kazimierz, Kraków, Poland')).toBeInTheDocument();
  });

  it('falls back to the city when the listing carries no address', () => {
    const { address: _address, ...withoutAddress } = listing;
    render(<PropertyCard property={withoutAddress} />);

    expect(screen.getByText('Kraków, Poland')).toBeInTheDocument();
  });

  it('falls back to a placeholder when the listing carries no title', () => {
    const { title: _title, ...withoutTitle } = listing;
    render(<PropertyCard property={withoutTitle} />);

    expect(screen.getByText('Untitled Property')).toBeInTheDocument();
  });
});
