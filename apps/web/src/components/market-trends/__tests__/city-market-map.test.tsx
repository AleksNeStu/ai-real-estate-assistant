import { render, screen } from '@testing-library/react';
import type { ReactNode } from 'react';

import { CityMarketMap } from '../city-market-map';
import { summariseCity } from '../city-market-stats';
import type { Property, SearchResultItem } from '@/lib/types';

/**
 * The catalogue on the map.
 *
 * The map is a pane, not a picture: it draws one marker per city and hands
 * the pick back. The theme filter lives on the tile pane, so the tiles follow
 * the dark theme - the test asserts the map asks for that pane.
 */
const getPaneMock = jest.fn(() => ({ style: {} as CSSStyleDeclaration }));

jest.mock('leaflet', () => ({
  divIcon: jest.fn(() => ({})),
}));

jest.mock('react-leaflet', () => ({
  MapContainer: ({ children }: { children: ReactNode }) => <div data-testid="map">{children}</div>,
  TileLayer: () => <div data-testid="tile" />,
  Marker: ({
    children,
    position,
    eventHandlers,
  }: {
    children: ReactNode;
    position: unknown;
    eventHandlers?: { click?: () => void };
  }) => (
    <div data-testid="marker" data-position={JSON.stringify(position)}>
      <button type="button" data-testid="marker-click" onClick={() => eventHandlers?.click?.()}>
        click
      </button>
      {children}
    </div>
  ),
  useMap: () => ({ getPane: getPaneMock }),
}));

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

describe('CityMarketMap', () => {
  beforeEach(() => {
    getPaneMock.mockClear();
  });

  it('draws one marker per city of the catalogue', () => {
    const cities = [
      summariseCity('Warsaw', makeResults([makeProperty()])),
      summariseCity('Lublin', []),
    ];

    render(<CityMarketMap cities={cities} selected={null} onSelect={() => {}} />);

    expect(screen.getAllByTestId('marker')).toHaveLength(2);
  });

  it('places the marker of a city at that city', () => {
    const cities = [summariseCity('Warsaw', makeResults([makeProperty()]))];

    render(<CityMarketMap cities={cities} selected={null} onSelect={() => {}} />);

    expect(screen.getByTestId('marker').getAttribute('data-position')).toBe('[52.2297,21.0122]');
  });

  it('hands the picked city back', () => {
    const onSelect = jest.fn();
    const cities = [
      summariseCity('Warsaw', makeResults([makeProperty()])),
      summariseCity('Lublin', []),
    ];

    render(<CityMarketMap cities={cities} selected={null} onSelect={onSelect} />);

    screen.getAllByTestId('marker-click')[1].click();

    expect(onSelect).toHaveBeenCalledWith('Lublin');
  });

  it('says what the two kinds of marker mean', () => {
    const cities = [summariseCity('Warsaw', makeResults([makeProperty()]))];

    render(<CityMarketMap cities={cities} selected={null} onSelect={() => {}} />);

    expect(screen.getByText('listings in catalogue')).toBeInTheDocument();
    expect(screen.getByText('no listings yet')).toBeInTheDocument();
  });

  it('filters the tile pane, so the tiles follow the dark theme', () => {
    const cities = [summariseCity('Warsaw', makeResults([makeProperty()]))];

    render(<CityMarketMap cities={cities} selected={null} onSelect={() => {}} />);

    expect(getPaneMock).toHaveBeenCalledWith('tilePane');
  });
});
