import { render, screen, waitFor } from '@testing-library/react';

import { HeroInstrument } from '@/components/landing/hero-instrument';
import { formatMapPinPrice } from '@/lib/format';

/**
 * The hero instrument is the landing's claim to a working product: the
 * parsed query, the matches, and the map they sit on.
 *
 * It used to draw a lattice of its own - a grid with three price chips on
 * it - so the panel could never show a map, while the README promised "a
 * parsed query, a map and three priced rows". These tests hold the panel to
 * that promise: the map is the real one, it gets the real coordinates, and
 * the pin says the same price the row underneath it says.
 */

jest.mock('@/components/landing/hero-map', () => ({
  __esModule: true,
  default: ({
    points,
  }: {
    points: { id: string; lat: number; lon: number }[];
  }) => (
    <div data-testid="hero-map" data-count={points.length}>
      {points.map((point) => `${point.id}@${point.lat},${point.lon}`).join(' ')}
    </div>
  ),
}));

const RESULTS = [
  {
    property: {
      id: 'prop-a',
      title: 'Two rooms in Kazimierz',
      price: 322000,
      currency: 'PLN',
      city: 'Kraków',
      district: 'Kazimierz',
      rooms: 2,
      area_sqm: 60,
      latitude: 50.0553,
      longitude: 19.9445,
    },
    score: 0.95,
  },
  {
    property: {
      id: 'prop-b',
      title: 'Two rooms in Nowa Huta',
      price: 4100,
      currency: 'PLN',
      city: 'Kraków',
      district: 'Nowa Huta',
      rooms: 3,
      area_sqm: 90,
      latitude: 50.2147,
      longitude: 20.1952,
    },
    score: 0.9,
  },
];

function mockSearch() {
  global.fetch = jest.fn(async () => ({
    ok: true,
    status: 200,
    json: async () => ({ count: RESULTS.length, results: RESULTS }),
  })) as unknown as typeof fetch;
}

describe('the map of the hero instrument', () => {
  beforeEach(() => {
    mockSearch();
  });

  it('puts the matches on the map with their own coordinates', async () => {
    render(<HeroInstrument query="2-bedroom apartment in Kraków under 500k" locale="en" />);

    await waitFor(() => {
      expect(screen.getByTestId('hero-map')).toBeInTheDocument();
    });

    const map = screen.getByTestId('hero-map');
    expect(map).toHaveAttribute('data-count', '2');
    expect(map.textContent).toContain('prop-a@50.0553,19.9445');
    expect(map.textContent).toContain('prop-b@50.2147,20.1952');
  });

  it('shows the matches as priced rows under the map', async () => {
    render(<HeroInstrument query="2-bedroom apartment in Kraków under 500k" locale="en" />);

    await waitFor(() => {
      expect(screen.getByText(/322.000/)).toBeInTheDocument();
    });
    expect(screen.getByText(/Kazimierz/)).toBeInTheDocument();
  });
});

describe('the pin on the map', () => {
  // The currency format separates the code from the number with a
  // non-breaking space, so the assertions compare the readable form.
  const pin = (price?: number, currency = 'PLN', locale = 'pl-PL') =>
    formatMapPinPrice(price, currency, locale).replace(/[\s  ]/g, '');

  it('says the price the row underneath it says', () => {
    // The chip used to print thousands with no magnitude check: 322 000 zł
    // became "322k" and 4 100 zł became "4k". Carrying the currency into the
    // chip was not enough either — 2 100 zł still read as "2.1K", which is a
    // DIFFERENT price from the one the row prints.
    expect(pin(322000)).toBe('322000zł');
    expect(pin(4100)).toBe('4100zł');
    expect(pin(3000)).toBe('3000zł');
  });

  it('shortens only the prices that are too long for a chip', () => {
    // The same rule the search map's popup uses: below a million the exact
    // price, above it the compact one.
    expect(pin(1200000)).toContain('mln');
  });

  it('speaks the same spelling as the row', () => {
    expect(formatMapPinPrice(322000, 'PLN', 'pl-PL')).toContain('322');
    expect(formatMapPinPrice(322000, 'PLN', 'pl-PL')).not.toContain('K');
  });

  it('never leaves the pin empty', () => {
    expect(formatMapPinPrice(undefined, 'PLN', 'en')).toBe('—');
  });
});
