import React from 'react';
import { render, screen, waitFor, within } from '@testing-library/react';

import AgentsPage from '../page';
import * as api from '@/lib/api';
import type { AgentProfile } from '@/lib/types';

jest.mock('@/lib/api', () => ({
  getAgents: jest.fn(),
}));

const mockAgents: AgentProfile[] = [
  {
    id: 'agent-1',
    user_id: 'user-1',
    name: 'Anna Kowalska',
    email: 'anna@realestate.pl',
    agency_name: 'Premium Homes',
    average_rating: 4.8,
    total_reviews: 45,
    total_sales: 120,
    total_rentals: 30,
    listings_count: 14,
    is_verified: true,
    is_active: true,
    specialties: ['Residential', 'Luxury'],
    service_areas: ['Warsaw', 'Krakow'],
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-06-01T00:00:00Z',
  },
  {
    id: 'agent-2',
    user_id: 'user-2',
    name: 'Piotr Nowak',
    email: 'piotr@homes.pl',
    agency_name: 'City Realty',
    average_rating: 4.5,
    total_reviews: 30,
    total_sales: 80,
    total_rentals: 50,
    listings_count: 0,
    is_verified: false,
    is_active: true,
    specialties: ['Commercial'],
    service_areas: ['Gdansk'],
    created_at: '2024-02-01T00:00:00Z',
    updated_at: '2024-06-01T00:00:00Z',
  },
];

const mockAgentsResponse = {
  items: mockAgents,
  total: 2,
  page: 1,
  page_size: 100,
  total_pages: 1,
};

describe('AgentsPage', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (api.getAgents as jest.Mock).mockResolvedValue(mockAgentsResponse);
  });

  it('renders the agents page heading', async () => {
    render(<AgentsPage />);

    await waitFor(() => {
      expect(screen.getByText('Find an Agent')).toBeInTheDocument();
    });
  });

  it('renders the agents as a ledger, one row per agent', async () => {
    render(<AgentsPage />);

    await waitFor(() => {
      expect(screen.getAllByTestId('agent-row')).toHaveLength(2);
    });

    expect(screen.getByText('Anna Kowalska')).toBeInTheDocument();
    expect(screen.getByText('Piotr Nowak')).toBeInTheDocument();
  });

  it('counts the agents that are on screen', async () => {
    render(<AgentsPage />);

    await waitFor(() => {
      expect(screen.getByText('2 agents')).toBeInTheDocument();
    });
  });

  it('offers the cities and the specialties the catalogue names as filters', async () => {
    render(<AgentsPage />);

    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Krakow' })).toBeInTheDocument();
    });

    expect(screen.getByRole('button', { name: 'Residential' })).toBeInTheDocument();
  });

  it('shows the number of listings every agent has', async () => {
    render(<AgentsPage />);

    await waitFor(() => {
      expect(screen.getAllByTestId('agent-row')).toHaveLength(2);
    });

    const rows = screen.getAllByTestId('agent-row');
    expect(within(rows[0]).getByText('14')).toBeInTheDocument();
    // An agent with no listings has none - the column says zero, not a dash.
    expect(within(rows[1]).getByText('0')).toBeInTheDocument();
  });

  it('names the Listings column after the Reviews column', async () => {
    render(<AgentsPage />);

    await waitFor(() => {
      expect(screen.getByText('Listings')).toBeInTheDocument();
    });

    const headerCells = Array.from(screen.getByText('Listings').parentElement?.children ?? []);
    expect(headerCells.map((cell) => cell.textContent)).toEqual([
      '',
      'Agent',
      'Agency',
      'Service areas',
      'Rating',
      'Reviews',
      'Listings',
      '',
    ]);
  });

  it('says nothing where the count is unknown rather than claiming zero', async () => {
    (api.getAgents as jest.Mock).mockResolvedValue({
      items: [{ ...mockAgents[0], listings_count: undefined }],
      total: 1,
      page: 1,
      page_size: 100,
      total_pages: 1,
    });

    render(<AgentsPage />);

    await waitFor(() => {
      expect(screen.getAllByTestId('agent-row')).toHaveLength(1);
    });

    expect(within(screen.getByTestId('agent-row')).getByText('—')).toBeInTheDocument();
  });

  it('shows the empty state when no agent is left', async () => {
    (api.getAgents as jest.Mock).mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      page_size: 100,
      total_pages: 0,
    });

    render(<AgentsPage />);

    await waitFor(() => {
      expect(screen.getByText('No agents found')).toBeInTheDocument();
    });

    expect(screen.getByText('Try adjusting your filters or search criteria')).toBeInTheDocument();
  });

  it('shows the error state when the catalogue cannot be read', async () => {
    (api.getAgents as jest.Mock).mockRejectedValue(new Error('Network error'));

    render(<AgentsPage />);

    await waitFor(() => {
      expect(screen.getByText('Network error')).toBeInTheDocument();
    });

    expect(screen.getByText('Retry')).toBeInTheDocument();
  });

  it('asks the server for the catalogue, sorted by rating', async () => {
    render(<AgentsPage />);

    await waitFor(() => {
      expect(api.getAgents).toHaveBeenCalledWith(
        expect.objectContaining({
          sort_by: 'rating',
          sort_order: 'desc',
          page: 1,
        })
      );
    });
  });
});
