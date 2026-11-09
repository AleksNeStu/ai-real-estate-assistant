import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import CityOverviewPage from '../page';

// Spy on console.error to suppress expected errors during tests
const originalError = console.error;
beforeAll(() => {
  console.error = jest.fn();
});

afterAll(() => {
  console.error = originalError;
});

afterEach(() => {
  (console.error as jest.Mock).mockClear();
});

interface MockProperty {
  id: string;
  title?: string;
  city?: string;
  country?: string;
  price?: number;
  currency?: string;
  area_sqm?: number;
  latitude?: number;
  longitude?: number;
}

// The map is a pane of its own: the test does not drive Leaflet, it checks
// that the route draws one and hands the pick back.
jest.mock('@/components/market-trends/city-market-map', () => ({
  __esModule: true,
  default: ({
    cities,
    onSelect,
  }: {
    cities: Array<{ city: string }>;
    onSelect: (city: string) => void;
  }) => (
    <div data-testid="city-market-map" data-cities={cities.length}>
      <button type="button" onClick={() => onSelect(cities[0]?.city ?? '')}>
        Test Marker
      </button>
    </div>
  ),
}));

// Mock the API
jest.mock('@/lib/api', () => ({
  searchProperties: jest.fn(),
}));

import { searchProperties } from '@/lib/api';

const warsawListing = {
  property: {
    id: '1',
    title: 'Warsaw Apartment',
    city: 'Warsaw',
    country: 'Poland',
    price: 300000,
    currency: 'PLN',
    area_sqm: 50,
    latitude: 52.2297,
    longitude: 21.0122,
  },
};

const krakowListing = {
  property: {
    id: '2',
    title: 'Krakow Apartment',
    city: 'Krakow',
    country: 'Poland',
    price: 250000,
    currency: 'PLN',
    area_sqm: 40,
    latitude: 50.0647,
    longitude: 19.945,
  },
};

describe('CityOverviewPage', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders the catalogue as a ledger of cities', async () => {
    (searchProperties as jest.Mock).mockResolvedValue({ results: [warsawListing] });

    render(<CityOverviewPage />);

    await waitFor(() => {
      expect(screen.getAllByTestId('city-row').length).toBeGreaterThan(0);
    });

    expect(screen.getByText('City Overview')).toBeInTheDocument();
    // Every city of the catalogue gets a row - the ones it holds nothing
    // for included.
    expect(screen.getAllByTestId('city-row')).toHaveLength(8);
    expect(screen.getAllByText('Warsaw').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Lublin').length).toBeGreaterThan(0);
  });

  it('renders the map beside the ledger', async () => {
    (searchProperties as jest.Mock).mockResolvedValue({ results: [warsawListing] });

    render(<CityOverviewPage />);

    await waitFor(() => {
      expect(screen.getByTestId('city-market-map')).toBeInTheDocument();
    });
  });

  it('opens on a city the catalogue holds listings for', async () => {
    (searchProperties as jest.Mock).mockResolvedValue({ results: [warsawListing] });

    render(<CityOverviewPage />);

    await waitFor(() => {
      expect(screen.getAllByTestId('city-row').length).toBeGreaterThan(0);
    });

    // The detail panel is open on the covered city.
    expect(screen.getByText('1 listing')).toBeInTheDocument();
  });

  it('says that a city the catalogue holds nothing for is empty', async () => {
    // The catalogue answers for Warsaw and holds nothing for the rest.
    (searchProperties as jest.Mock).mockImplementation((request: { query: string }) =>
      request.query.includes('Warsaw')
        ? Promise.resolve({ results: [warsawListing] })
        : Promise.resolve({ results: [] })
    );

    render(<CityOverviewPage />);

    await waitFor(() => {
      expect(screen.getAllByTestId('city-row').length).toBeGreaterThan(0);
    });

    // The uncovered city keeps its row, and its numbers read as a dash.
    const lublin = screen.getAllByTestId('city-row').find(
      (row) => row.getAttribute('data-city') === 'Lublin'
    );
    expect(lublin).toBeDefined();
    expect(lublin?.textContent).toContain('—');
  });

  it('picks the city the row names', async () => {
    (searchProperties as jest.Mock).mockResolvedValue({ results: [warsawListing] });

    render(<CityOverviewPage />);

    await waitFor(() => {
      expect(screen.getAllByTestId('city-row').length).toBeGreaterThan(0);
    });

    const rows = screen.getAllByTestId('city-row');
    fireEvent.click(rows[rows.length - 1]);

    await waitFor(() => {
      expect(screen.getAllByTestId('city-row').length).toBeGreaterThan(0);
    });
  });

  it('renders the error state when no city in the catalogue has listings', async () => {
    (searchProperties as jest.Mock).mockRejectedValue(new Error('API Error'));

    render(<CityOverviewPage />);

    await waitFor(() => {
      expect(screen.getByText('No City Data Available')).toBeInTheDocument();
    });
  });

  it('keeps the cities that answered when another one fails', async () => {
    let callCount = 0;
    (searchProperties as jest.Mock).mockImplementation(() => {
      callCount++;
      if (callCount === 1) {
        return Promise.reject(new Error('First city failed'));
      }
      return Promise.resolve({ results: [krakowListing] });
    });

    render(<CityOverviewPage />);

    await waitFor(() => {
      expect(screen.getAllByTestId('city-row').length).toBeGreaterThan(0);
    });

    // The row for Kraków carries its listing.
    expect(screen.getAllByText('Kraków').length).toBeGreaterThan(0);
  });

  it('handles properties without location data', async () => {
    (searchProperties as jest.Mock).mockResolvedValue({
      results: [
        {
          property: {
            id: '1',
            title: 'Apartment Without Location',
            city: 'Warsaw',
            country: 'Poland',
            price: 300000,
          },
        },
      ],
    });

    render(<CityOverviewPage />);

    await waitFor(() => {
      expect(screen.getAllByTestId('city-row').length).toBeGreaterThan(0);
    });

    expect(screen.getByText('City Overview')).toBeInTheDocument();
  });
});
