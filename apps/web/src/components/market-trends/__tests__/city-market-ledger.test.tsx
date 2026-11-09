import { fireEvent, render, screen } from '@testing-library/react';

import { CityMarketLedger } from '../city-market-ledger';
import { summariseCity } from '../city-market-stats';
import type { Property, SearchResultItem } from '@/lib/types';

/**
 * The catalogue as a ledger.
 *
 * The row is the control, and a city the catalogue holds nothing for keeps
 * its row - so the test covers the empty city as much as the covered one.
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
    price: 912000,
    currency: 'PLN',
    area_sqm: 52,
    ...overrides,
  } as Property;
}

function makeResults(properties: Property[]): SearchResultItem[] {
  return properties.map((property, index) => ({ property, score: 0.95 - index * 0.05 }));
}

const warsaw = summariseCity(
  'Warsaw',
  makeResults([
    makeProperty({ id: 'p1', price: 912000, area_sqm: 52 }),
    makeProperty({ id: 'p2', price: 389000, area_sqm: 40 }),
    makeProperty({ id: 'p3', price: 2450000, area_sqm: 140 }),
  ])
);

const lublin = summariseCity('Lublin', []);

describe('CityMarketLedger', () => {
  it('names every city of the catalogue', () => {
    render(<CityMarketLedger cities={[warsaw, lublin]} selected={null} onSelect={() => {}} />);

    expect(screen.getByText('Warsaw')).toBeInTheDocument();
    expect(screen.getByText('Lublin')).toBeInTheDocument();
  });

  it('writes the count and the prices of the covered city', () => {
    render(<CityMarketLedger cities={[warsaw]} selected={null} onSelect={() => {}} />);

    expect(screen.getByText('3')).toBeInTheDocument();
    // 912 000 is written compact, so the column fits.
    expect(screen.getByText('1.3M')).toBeInTheDocument();
    expect(screen.getByText('389K')).toBeInTheDocument();
    expect(screen.getByText('2.5M')).toBeInTheDocument();
    // The price per m² is written out: a rounded 14.9K is a different number.
    expect(screen.getByText('14,921')).toBeInTheDocument();
  });

  it('writes a dash for a city the catalogue holds nothing for', () => {
    render(<CityMarketLedger cities={[lublin]} selected={null} onSelect={() => {}} />);

    expect(screen.getAllByText('—')).toHaveLength(4);
    expect(screen.getByText('0')).toBeInTheDocument();
  });

  it('says the unit the prices are read in', () => {
    render(<CityMarketLedger cities={[warsaw]} selected={null} onSelect={() => {}} />);

    expect(screen.getByText('zł/m²')).toBeInTheDocument();
    expect(screen.getByText(/Prices in zł/)).toBeInTheDocument();
  });

  it('marks the selected row', () => {
    render(<CityMarketLedger cities={[warsaw, lublin]} selected="Warsaw" onSelect={() => {}} />);

    const rows = screen.getAllByTestId('city-row');
    expect(rows[0].getAttribute('aria-pressed')).toBe('true');
    expect(rows[1].getAttribute('aria-pressed')).toBe('false');
  });

  it('picks the city that was clicked', () => {
    const onSelect = jest.fn();
    render(<CityMarketLedger cities={[warsaw, lublin]} selected={null} onSelect={onSelect} />);

    fireEvent.click(screen.getAllByTestId('city-row')[1]);

    expect(onSelect).toHaveBeenCalledWith('Lublin');
  });
});
