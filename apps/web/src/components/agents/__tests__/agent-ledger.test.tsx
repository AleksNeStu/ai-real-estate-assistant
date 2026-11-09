import { render, screen } from '@testing-library/react';

import { AgentLedger } from '../agent-ledger';
import type { AgentProfile } from '@/lib/types';

function makeAgent(overrides: Partial<AgentProfile> = {}): AgentProfile {
  return {
    id: 'a1',
    user_id: 'u1',
    name: 'Anna Kowalczyk',
    agency_name: 'Agencja Wisła',
    average_rating: 4.9,
    total_reviews: 128,
    total_sales: 212,
    total_rentals: 87,
    is_verified: true,
    is_active: true,
    specialties: ['Residential'],
    languages: ['PL', 'EN'],
    service_areas: ['Kraków'],
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-06-01T00:00:00Z',
    ...overrides,
  };
}

describe('AgentLedger', () => {
  it('renders one row per agent', () => {
    render(
      <AgentLedger
        locale="en"
        agents={[makeAgent(), makeAgent({ id: 'a2', name: 'Piotr Zieliński' })]}
      />
    );

    expect(screen.getAllByTestId('agent-row')).toHaveLength(2);
  });

  it('names the agent, the agency and the areas it covers', () => {
    render(<AgentLedger locale="en" agents={[makeAgent()]} />);

    expect(screen.getByText('Anna Kowalczyk')).toBeInTheDocument();
    expect(screen.getByText('Agencja Wisła')).toBeInTheDocument();
    expect(screen.getByText('Kraków')).toBeInTheDocument();
  });

  it('shows the rating and the review count', () => {
    render(<AgentLedger locale="en" agents={[makeAgent()]} />);

    expect(screen.getByText('★ 4.9')).toBeInTheDocument();
    expect(screen.getByText('128')).toBeInTheDocument();
  });

  it('marks a verified agent and leaves an unverified one unmarked', () => {
    render(
      <AgentLedger
        locale="en"
        agents={[makeAgent(), makeAgent({ id: 'a2', name: 'Piotr Zieliński', is_verified: false })]}
      />
    );

    expect(screen.getByText('Verified')).toBeInTheDocument();
  });

  it('links every row to the agent profile', () => {
    render(<AgentLedger locale="en" agents={[makeAgent()]} />);

    const row = screen.getByTestId('agent-row');
    expect(row).toHaveAttribute('href', '/en/agents/a1');
  });

  it('says so when an agent has no rating yet', () => {
    render(<AgentLedger locale="en" agents={[makeAgent({ average_rating: 0 })]} />);

    expect(screen.getByText(/★ —/)).toBeInTheDocument();
  });
});
