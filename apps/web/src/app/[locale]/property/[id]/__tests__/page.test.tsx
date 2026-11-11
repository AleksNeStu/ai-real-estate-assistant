import React from 'react';
import { act, render, screen, waitFor } from '@testing-library/react';

import PropertyView from '../property-view';
import * as api from '@/lib/api';
import type { Property } from '@/lib/types';

jest.mock('@/lib/api', () => ({
  getProperty: jest.fn(),
  getRelatedProperties: jest.fn(),
}));

jest.mock('next/navigation', () => ({
  useRouter: () => ({ push: jest.fn(), replace: jest.fn() }),
  useSearchParams: () => new URLSearchParams(),
  usePathname: () => '/en/property/listing-1',
}));

// The heart button reaches the i18n routing module, which is ESM and cannot
// be loaded by the test runtime. The button itself is covered on its own.
jest.mock('@/components/property/heart-button', () => ({
  HeartButton: () => <div data-testid="heart-button" />,
}));

jest.mock('@/components/property/MortgageEstimate', () => ({
  MortgageEstimate: () => <div data-testid="mortgage-estimate" />,
}));

jest.mock('@/components/property/NeighborhoodSummary', () => ({
  NeighborhoodSummary: () => <div data-testid="neighborhood-summary" />,
}));

jest.mock('@/components/property/property-card', () => ({
  PropertyCard: ({ property }: { property: Property }) => (
    <div data-testid="property-card">{property.title}</div>
  ),
}));

const mockProperty: Property = {
  id: 'listing-1',
  title: 'Bright two-room apartment',
  description: 'A sunny apartment close to the park.',
  city: 'Kraków',
  country: 'Poland',
  district: 'Stare Miasto',
  neighborhood: 'Kazimierz',
  address: 'Brzozowa 12',
  latitude: 50.0614,
  longitude: 19.9374,
  property_type: 'apartment',
  listing_type: 'rent',
  rooms: 2,
  bathrooms: 1,
  area_sqm: 54,
  floor: 3,
  total_floors: 6,
  year_built: 2015,
  energy_rating: 'B',
  price: 2800,
  currency: 'PLN',
  price_per_sqm: 51.85,
  has_parking: false,
  has_garden: false,
  has_pool: false,
  has_garage: false,
  has_bike_room: true,
  has_elevator: true,
  images: ['https://example.test/photo.jpg'],
  source_url: 'https://example.test/listing/listing-1',
  source_platform: 'demo-portal',
};

const mockRelated: Property[] = [
  {
    id: 'listing-2',
    title: 'Similar flat nearby',
    city: 'Kraków',
    property_type: 'apartment',
    listing_type: 'rent',
    price: 2900,
    currency: 'PLN',
    has_parking: false,
    has_garden: false,
    has_pool: false,
    has_garage: false,
    has_bike_room: false,
  },
];

/**
 * The page, rendered.
 *
 * The route is a server component now: it reads the listing on the server
 * and hands it to this view. The view is what the reader interacts with, and
 * it still reads the listing itself when it arrives without one - which is
 * what the tests below exercise.
 */
async function renderPage(propertyId: string) {
  await act(async () => {
    render(<PropertyView propertyId={propertyId} />);
  });
}

describe('the listing page', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (api.getProperty as jest.Mock).mockResolvedValue(mockProperty);
    (api.getRelatedProperties as jest.Mock).mockResolvedValue({
      properties: mockRelated,
      count: 1,
    });
  });

  it('renders the listing itself', async () => {
    await renderPage('listing-1');

    await waitFor(() => {
      expect(screen.getByText('Bright two-room apartment')).toBeInTheDocument();
    });

    expect(screen.getByText(/Brzozowa 12/)).toBeInTheDocument();
  });

  it('renders the price and the numbers of the listing', async () => {
    await renderPage('listing-1');

    await waitFor(() => {
      expect(screen.getByText('Bright two-room apartment')).toBeInTheDocument();
    });

    // The price, the area and the room count are the three numbers a reader
    // decides on.
    expect(screen.getByText(/2,800/)).toBeInTheDocument();
    expect(screen.getAllByText('54 m²').length).toBeGreaterThan(0);
    expect(screen.getAllByText('2').length).toBeGreaterThan(0);
  });

  it('renders the details the catalogue holds', async () => {
    await renderPage('listing-1');

    await waitFor(() => {
      expect(screen.getByText('Bright two-room apartment')).toBeInTheDocument();
    });

    expect(screen.getByText('2015')).toBeInTheDocument();
    expect(screen.getByText('apartment')).toBeInTheDocument();
    expect(screen.getByText('rent')).toBeInTheDocument();
  });

  it('renders the comparables', async () => {
    await renderPage('listing-1');

    await waitFor(() => {
      expect(screen.getByText('Similar flat nearby')).toBeInTheDocument();
    });
  });

  it('reports a listing the catalogue does not hold', async () => {
    (api.getProperty as jest.Mock).mockRejectedValue(new Error('Property not found'));

    await renderPage('missing');

    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument();
    });
  });

  it('keeps the page when the comparables cannot be read', async () => {
    (api.getRelatedProperties as jest.Mock).mockRejectedValue(new Error('boom'));

    await renderPage('listing-1');

    await waitFor(() => {
      expect(screen.getByText('Bright two-room apartment')).toBeInTheDocument();
    });

    expect(screen.queryByText('Similar flat nearby')).not.toBeInTheDocument();
  });
});
