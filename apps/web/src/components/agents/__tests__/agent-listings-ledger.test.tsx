import { render, screen, fireEvent } from '@testing-library/react';

import { AgentListingsLedger } from '../agent-listings-ledger';
import type { AgentListing, Property } from '@/lib/types';

function makeProperty(overrides: Partial<Property> = {}): Property {
  return {
    id: 'p1',
    title: '2 rooms, 46 m²',
    address: 'os. Centrum C',
    city: 'Kraków',
    property_type: 'apartment',
    listing_type: 'sale',
    has_parking: false,
    has_garden: false,
    has_pool: false,
    has_garage: false,
    has_bike_room: false,
    price: 489000,
    currency: 'PLN',
    rooms: 2,
    area_sqm: 46,
    ...overrides,
  };
}

function makeListing(overrides: Partial<AgentListing> = {}): AgentListing {
  return {
    id: 'l1',
    agent_id: 'a1',
    property_id: 'p1',
    listing_type: 'sale',
    is_primary: true,
    is_active: true,
    created_at: '2024-01-01T00:00:00Z',
    property: makeProperty(),
    ...overrides,
  };
}

describe('AgentListingsLedger', () => {
  it('renders one row per listing', () => {
    render(
      <AgentListingsLedger
        listings={[makeListing(), makeListing({ id: 'l2', property_id: 'p2' })]}
        selectedPropertyId={null}
        onSelect={jest.fn()}
        onSchedule={jest.fn()}
      />
    );

    expect(screen.getAllByTestId('property-card')).toHaveLength(2);
  });

  it('shows the price of the listing', () => {
    render(
      <AgentListingsLedger
        listings={[makeListing()]}
        selectedPropertyId={null}
        onSelect={jest.fn()}
        onSchedule={jest.fn()}
      />
    );

    expect(screen.getByText('PLN 489,000')).toBeInTheDocument();
  });

  it('shows the price per square metre', () => {
    render(
      <AgentListingsLedger
        listings={[makeListing()]}
        selectedPropertyId={null}
        onSelect={jest.fn()}
        onSchedule={jest.fn()}
      />
    );

    expect(screen.getByText('10,630 PLN/m²')).toBeInTheDocument();
  });

  it('picks the listing when the row is clicked', () => {
    const onSelect = jest.fn();
    render(
      <AgentListingsLedger
        listings={[makeListing()]}
        selectedPropertyId={null}
        onSelect={onSelect}
        onSchedule={jest.fn()}
      />
    );

    fireEvent.click(screen.getByTestId('property-card'));

    expect(onSelect).toHaveBeenCalledWith('p1');
  });

  it('asks for a viewing of the picked listing', () => {
    const onSelect = jest.fn();
    const onSchedule = jest.fn();
    render(
      <AgentListingsLedger
        listings={[makeListing()]}
        selectedPropertyId={null}
        onSelect={onSelect}
        onSchedule={onSchedule}
      />
    );

    fireEvent.click(screen.getByRole('button', { name: 'Schedule Viewing' }));

    expect(onSelect).toHaveBeenCalledWith('p1');
    expect(onSchedule).toHaveBeenCalledWith('p1');
  });
});
