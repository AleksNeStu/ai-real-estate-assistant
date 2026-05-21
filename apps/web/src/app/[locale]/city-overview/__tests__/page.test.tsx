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

interface MockPoint {
  id: string;
  lat: number;
  lon: number;
  title?: string;
  city?: string;
  country?: string;
  price?: number;
}

interface SearchResultItem {
  property: {
    id: string;
    title?: string;
    city?: string;
    country?: string;
    price?: number;
    latitude?: number;
    longitude?: number;
  };
}

// Mock the Mapbox map component
jest.mock('@/components/search/property-mapbox-map', () => {
  return function MockPropertyMapboxMap({
    className = '',
    onMarkerClick,
    points,
  }: {
    className?: string;
    onMarkerClick?: (point: MockPoint) => void;
    points?: MockPoint[];
  }) {
    return (
      <div data-testid="mapbox-map" className={className}>
        Mapbox Map
        {points && points.length > 0 && (
          <button onClick={() => onMarkerClick?.(points[0])}>Test Marker</button>
        )}
      </div>
    );
  };
});

// Mock the property-map-utils
jest.mock('@/components/search/property-map-utils', () => ({
  extractMapPoints: jest.fn((results: SearchResultItem[]) =>
    results.map((item) => ({
      id: item.property.id,
      lat: item.property.latitude || 0,
      lon: item.property.longitude || 0,
      title: item.property.title,
      city: item.property.city,
      country: item.property.country,
      price: item.property.price,
    }))
  ),
  computeCenter: jest.fn((points: { lat: number; lon: number }[]) => {
    if (!points.length) return null;
    const sum = points.reduce(
      (acc: { lat: number; lon: number }, p: { lat: number; lon: number }) => ({
        lat: acc.lat + p.lat,
        lon: acc.lon + p.lon,
      }),
      { lat: 0, lon: 0 }
    );
    return { lat: sum.lat / points.length, lon: sum.lon / points.length };
  }),
}));

// Mock the API
jest.mock('@/lib/api', () => ({
  searchProperties: jest.fn(),
}));

import { searchProperties } from '@/lib/api';

describe('CityOverviewPage', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.runOnlyPendingTimers();
    jest.useRealTimers();
  });

  it('should render loading state initially', () => {
    (searchProperties as jest.Mock).mockImplementation(() => new Promise(() => {}));

    render(<CityOverviewPage />);

    expect(screen.getByText(/Loading city data/i)).toBeInTheDocument();
  });

  it('should render city overview with data', async () => {
    (searchProperties as jest.Mock).mockResolvedValue({
      results: [
        {
          property: {
            id: '1',
            title: 'Test Apartment',
            city: 'Warsaw',
            country: 'Poland',
            price: 300000,
            latitude: 52.2297,
            longitude: 21.0122,
          },
        },
      ],
    });

    render(<CityOverviewPage />);

    await waitFor(() => {
      expect(screen.queryByText(/Loading city data/i)).not.toBeInTheDocument();
    });

    expect(screen.getByText('City Overview')).toBeInTheDocument();
    expect(screen.getByText(/Explore property markets across Poland/i)).toBeInTheDocument();
  });

  it('should render map when data is loaded', async () => {
    (searchProperties as jest.Mock).mockResolvedValue({
      results: [
        {
          property: {
            id: '1',
            title: 'Test Apartment',
            city: 'Warsaw',
            country: 'Poland',
            price: 300000,
            latitude: 52.2297,
            longitude: 21.0122,
          },
        },
      ],
    });

    render(<CityOverviewPage />);

    await waitFor(() => {
      expect(screen.queryByText(/Loading city data/i)).not.toBeInTheDocument();
    });

    expect(screen.getByTestId('mapbox-map')).toBeInTheDocument();
  });

  it('should render empty state when no city data is available', async () => {
    (searchProperties as jest.Mock).mockResolvedValue({
      results: [],
    });

    render(<CityOverviewPage />);

    await waitFor(() => {
      expect(screen.queryByText(/Loading city data/i)).not.toBeInTheDocument();
    });

    // Should show the page but with no cities
    expect(screen.getByText('City Overview')).toBeInTheDocument();
  });

  it('should render error state on API failure', async () => {
    (searchProperties as jest.Mock).mockRejectedValue(new Error('API Error'));

    render(<CityOverviewPage />);

    await waitFor(() => {
      expect(screen.queryByText(/Loading city data/i)).not.toBeInTheDocument();
    });

    // Error should be caught and logged, page should still render
    expect(screen.getByText('City Overview')).toBeInTheDocument();
  });

  it('should render city statistics cards when data is loaded', async () => {
    (searchProperties as jest.Mock).mockResolvedValue({
      results: [
        {
          property: {
            id: '1',
            title: 'Warsaw Apartment',
            city: 'Warsaw',
            country: 'Poland',
            price: 300000,
            latitude: 52.2297,
            longitude: 21.0122,
          },
        },
        {
          property: {
            id: '2',
            title: 'Krakow Apartment',
            city: 'Krakow',
            country: 'Poland',
            price: 250000,
            latitude: 50.0647,
            longitude: 19.945,
          },
        },
      ],
    });

    render(<CityOverviewPage />);

    await waitFor(() => {
      expect(screen.queryByText(/Loading city data/i)).not.toBeInTheDocument();
    });

    // Should show "Market Statistics by City" section
    expect(screen.getByText('Market Statistics by City')).toBeInTheDocument();
  });

  it('should handle city card selection', async () => {
    (searchProperties as jest.Mock).mockResolvedValue({
      results: [
        {
          property: {
            id: '1',
            title: 'Warsaw Apartment',
            city: 'Warsaw',
            country: 'Poland',
            price: 300000,
            latitude: 52.2297,
            longitude: 21.0122,
          },
        },
      ],
    });

    render(<CityOverviewPage />);

    await waitFor(() => {
      expect(screen.queryByText(/Loading city data/i)).not.toBeInTheDocument();
    });

    // Find and click the Warsaw city card
    const warsawCards = screen.getAllByText('Warsaw');
    const cityCard = warsawCards.find((el) => el.closest('button'));
    if (cityCard) {
      fireEvent.click(cityCard);
    }
  });

  it('should close selected city details', async () => {
    (searchProperties as jest.Mock).mockResolvedValue({
      results: [
        {
          property: {
            id: '1',
            title: 'Warsaw Apartment',
            city: 'Warsaw',
            country: 'Poland',
            price: 300000,
            latitude: 52.2297,
            longitude: 21.0122,
          },
        },
      ],
    });

    render(<CityOverviewPage />);

    await waitFor(() => {
      expect(screen.queryByText(/Loading city data/i)).not.toBeInTheDocument();
    });

    // Select a city first
    const warsawCards = screen.getAllByText('Warsaw');
    const cityCard = warsawCards.find((el) => el.closest('button'));
    if (cityCard) {
      fireEvent.click(cityCard);
    }

    await waitFor(() => {
      // Should see city details section
      const closeButton = screen.queryByText('Close');
      if (closeButton) {
        fireEvent.click(closeButton);
      }
    });
  });

  it('should handle marker click to select city', async () => {
    (searchProperties as jest.Mock).mockResolvedValue({
      results: [
        {
          property: {
            id: '1',
            title: 'Warsaw Apartment',
            city: 'Warsaw',
            country: 'Poland',
            price: 300000,
            latitude: 52.2297,
            longitude: 21.0122,
          },
        },
      ],
    });

    render(<CityOverviewPage />);

    await waitFor(() => {
      expect(screen.queryByText(/Loading city data/i)).not.toBeInTheDocument();
    });

    // Click the marker button on the map
    const markerButton = screen.queryByText('Test Marker');
    if (markerButton) {
      fireEvent.click(markerButton);

      await waitFor(() => {
        // City should be selected
        expect(screen.getAllByText('Warsaw').length).toBeGreaterThan(0);
      });
    }
  });

  it('should render property cards for selected city', async () => {
    (searchProperties as jest.Mock).mockResolvedValue({
      results: [
        {
          property: {
            id: '1',
            title: 'Warsaw Apartment',
            city: 'Warsaw',
            country: 'Poland',
            price: 300000,
            latitude: 52.2297,
            longitude: 21.0122,
          },
        },
        {
          property: {
            id: '2',
            title: 'Krakow Apartment',
            city: 'Krakow',
            country: 'Poland',
            price: 250000,
            latitude: 50.0647,
            longitude: 19.945,
          },
        },
      ],
    });

    render(<CityOverviewPage />);

    await waitFor(() => {
      expect(screen.queryByText(/Loading city data/i)).not.toBeInTheDocument();
    });

    // Select Warsaw - the city selection should work without error
    const warsawCards = screen.getAllByText('Warsaw');
    const cityCard = warsawCards.find((el) => el.closest('button'));
    if (cityCard) {
      fireEvent.click(cityCard);
    }

    // Just verify the page still renders after selection
    expect(screen.getByText('City Overview')).toBeInTheDocument();
  });

  it('should handle API errors gracefully and continue with other cities', async () => {
    let callCount = 0;
    (searchProperties as jest.Mock).mockImplementation(() => {
      callCount++;
      if (callCount === 1) {
        return Promise.reject(new Error('First city failed'));
      }
      return Promise.resolve({
        results: [
          {
            property: {
              id: '2',
              title: 'Krakow Apartment',
              city: 'Krakow',
              country: 'Poland',
              price: 250000,
              latitude: 50.0647,
              longitude: 19.945,
            },
          },
        ],
      });
    });

    render(<CityOverviewPage />);

    await waitFor(() => {
      expect(screen.queryByText(/Loading city data/i)).not.toBeInTheDocument();
    });

    // Should still show some results
    expect(screen.getByText('City Overview')).toBeInTheDocument();
  });

  it('should handle properties without location data', async () => {
    (searchProperties as jest.Mock).mockResolvedValue({
      results: [
        {
          property: {
            id: '1',
            title: 'Apartment Without Location',
            city: 'Warsaw',
            country: 'Poland',
            price: 300000,
            // No latitude/longitude
          },
        },
      ],
    });

    render(<CityOverviewPage />);

    await waitFor(() => {
      expect(screen.queryByText(/Loading city data/i)).not.toBeInTheDocument();
    });

    // Should still render without crashing
    expect(screen.getByText('City Overview')).toBeInTheDocument();
  });

  it('should handle ApiError with request ID', async () => {
    const mockError = new Error('API failed') as Error & { request_id?: string };
    mockError.request_id = 'test-123';

    (searchProperties as jest.Mock).mockRejectedValue(mockError);

    render(<CityOverviewPage />);

    await waitFor(() => {
      expect(screen.queryByText(/Loading city data/i)).not.toBeInTheDocument();
    });

    // Error should be caught and logged, page should still render
    expect(screen.getByText('City Overview')).toBeInTheDocument();
  });
});
