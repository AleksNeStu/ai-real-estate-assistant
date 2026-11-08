import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { formatMessage } from 'next-intl';
import AgentsPage from '../page';
import * as api from '@/lib/api';
import en from '../../../../../messages/en.json';
import type { AgentProfile } from '@/lib/types';

/**
 * Resolve a message from the English catalogue. The key is the fallback: that is
 * exactly what the next-intl mock renders while the translation fragments are
 * still waiting for the central merge into the catalogues.
 */
const copy = (namespace: string, key: string, params?: Record<string, unknown>): string => {
  const value = [namespace, key]
    .join('.')
    .split('.')
    .reduce<unknown>(
      (acc, part) => (acc as Record<string, unknown> | undefined)?.[part],
      en as unknown
    );
  return typeof value === 'string' ? formatMessage(value, params) : key;
};

// Mock @/lib/api
jest.mock('@/lib/api', () => ({
  getAgents: jest.fn(),
}));

// Mock lucide-react icons
jest.mock('lucide-react', () => {
  const icons = [
    'Search',
    'SlidersHorizontal',
    'RefreshCw',
    'Users',
    'X',
    'MapPin',
    'Star',
    'Briefcase',
    'Award',
    'Phone',
    'Mail',
  ];
  const mock: Record<string, React.FC<{ className?: string; 'aria-hidden'?: boolean }>> = {};
  icons.forEach((name) => {
    mock[name] = (props: { className?: string }) => (
      <svg data-testid={`icon-${name}`} className={props.className} />
    );
  });
  return mock;
});

// Mock UI components
jest.mock('@/components/ui/card', () => ({
  Card: ({ children, className }: { children: React.ReactNode; className?: string }) => (
    <div className={className}>{children}</div>
  ),
  CardContent: ({ children, className }: { children: React.ReactNode; className?: string }) => (
    <div className={className}>{children}</div>
  ),
}));

jest.mock('@/components/ui/input', () => ({
  Input: (props: React.InputHTMLAttributes<HTMLInputElement>) => <input {...props} />,
}));

jest.mock('@/components/ui/label', () => ({
  Label: ({
    children,
    ...props
  }: { children: React.ReactNode } & React.LabelHTMLAttributes<HTMLLabelElement>) => (
    <label {...props}>{children}</label>
  ),
}));

jest.mock('@/components/ui/select', () => ({
  Select: ({
    children,
    value,
    onValueChange,
  }: {
    children: React.ReactNode;
    value?: string;
    onValueChange?: (v: string) => void;
  }) => (
    <div data-testid="select" data-value={value}>
      {children}
    </div>
  ),
  SelectContent: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  SelectItem: ({ children, value }: { children: React.ReactNode; value: string }) => (
    <div data-value={value}>{children}</div>
  ),
  SelectTrigger: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  SelectValue: ({ placeholder }: { placeholder?: string }) => <span>{placeholder}</span>,
}));

jest.mock('@/components/ui/button', () => ({
  Button: ({
    children,
    onClick,
    disabled,
    variant,
    size,
    ...props
  }: {
    children: React.ReactNode;
    onClick?: () => void;
    disabled?: boolean;
    variant?: string;
    size?: string;
  }) => (
    <button onClick={onClick} disabled={disabled} {...props}>
      {children}
    </button>
  ),
}));

jest.mock('@/components/ui/skeleton', () => ({
  Skeleton: (props: { className?: string }) => (
    <div data-testid="skeleton" className={props.className} />
  ),
}));

jest.mock('@/components/ui/badge', () => ({
  Badge: ({
    children,
    variant,
    className,
  }: {
    children: React.ReactNode;
    variant?: string;
    className?: string;
  }) => (
    <span data-variant={variant} className={className}>
      {children}
    </span>
  ),
}));

// Mock AgentCard component
jest.mock('@/components/agents/agent-card', () => ({
  AgentCard: ({ agent }: { agent: AgentProfile; locale: string }) => (
    <div data-testid={`agent-card-${agent.id}`}>
      <span>{agent.name || 'Agent'}</span>
      <span>{agent.agency_name}</span>
    </div>
  ),
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
  page_size: 12,
  total_pages: 1,
};

describe('AgentsPage', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (api.getAgents as jest.Mock).mockResolvedValue(mockAgentsResponse);
  });

  it('renders the agents page heading', async () => {
    render(<AgentsPage params={Promise.resolve({ locale: 'en' })} />);

    await waitFor(() => {
      // The mock resolves the real `en` catalogue, so we check the copy a reader sees
      expect(screen.getByText('Find an Agent')).toBeInTheDocument();
    });
  });

  it('renders the subtitle text', async () => {
    render(<AgentsPage params={Promise.resolve({ locale: 'en' })} />);

    await waitFor(() => {
      expect(screen.getByText('Connect with professional real estate agents')).toBeInTheDocument();
    });
  });

  it('shows loading skeletons initially', () => {
    (api.getAgents as jest.Mock).mockImplementation(() => new Promise(() => {}));

    render(<AgentsPage params={Promise.resolve({ locale: 'en' })} />);

    const skeletons = screen.getAllByTestId('skeleton');
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it('renders agent cards after loading', async () => {
    render(<AgentsPage params={Promise.resolve({ locale: 'en' })} />);

    await waitFor(() => {
      expect(screen.getByTestId('agent-card-agent-1')).toBeInTheDocument();
    });

    expect(screen.getByTestId('agent-card-agent-2')).toBeInTheDocument();
  });

  it('displays total count of agents', async () => {
    render(<AgentsPage params={Promise.resolve({ locale: 'en' })} />);

    await waitFor(() => {
      expect(
        screen.getByText(copy('pages.agents.pagination', 'found', { count: 2 }))
      ).toBeInTheDocument();
    });
  });

  it('shows singular "agent" text when only 1 result', async () => {
    (api.getAgents as jest.Mock).mockResolvedValue({
      items: [mockAgents[0]],
      total: 1,
      page: 1,
      page_size: 12,
      total_pages: 1,
    });

    render(<AgentsPage params={Promise.resolve({ locale: 'en' })} />);

    await waitFor(() => {
      expect(
        screen.getByText(copy('pages.agents.pagination', 'found', { count: 1 }))
      ).toBeInTheDocument();
    });
  });

  it('renders the search input', async () => {
    render(<AgentsPage params={Promise.resolve({ locale: 'en' })} />);

    await waitFor(() => {
      expect(screen.getByPlaceholderText('Search by city...')).toBeInTheDocument();
    });
  });

  it('renders the Apply Filters button', async () => {
    render(<AgentsPage params={Promise.resolve({ locale: 'en' })} />);

    await waitFor(() => {
      expect(screen.getByText('Apply Filters')).toBeInTheDocument();
    });
  });

  it('renders the refresh button', async () => {
    render(<AgentsPage params={Promise.resolve({ locale: 'en' })} />);

    await waitFor(() => {
      expect(screen.getByTestId('icon-RefreshCw')).toBeInTheDocument();
    });
  });

  it('shows empty state when no agents are returned', async () => {
    (api.getAgents as jest.Mock).mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      page_size: 12,
      total_pages: 0,
    });

    render(<AgentsPage params={Promise.resolve({ locale: 'en' })} />);

    await waitFor(() => {
      expect(screen.getByText('No agents found')).toBeInTheDocument();
    });

    expect(screen.getByText('Try adjusting your filters or search criteria')).toBeInTheDocument();
  });

  it('shows error state when API fails', async () => {
    (api.getAgents as jest.Mock).mockRejectedValue(new Error('Network error'));

    render(<AgentsPage params={Promise.resolve({ locale: 'en' })} />);

    await waitFor(() => {
      expect(screen.getByText('Network error')).toBeInTheDocument();
    });

    expect(screen.getByText('Retry')).toBeInTheDocument();
  });

  it('retries loading when retry button is clicked', async () => {
    (api.getAgents as jest.Mock)
      .mockRejectedValueOnce(new Error('Network error'))
      .mockResolvedValueOnce(mockAgentsResponse);

    render(<AgentsPage params={Promise.resolve({ locale: 'en' })} />);

    await waitFor(() => {
      expect(screen.getByText('Retry')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Retry'));

    await waitFor(() => {
      expect(screen.getByTestId('agent-card-agent-1')).toBeInTheDocument();
    });
  });

  it('triggers API call with filter params', async () => {
    render(<AgentsPage params={Promise.resolve({ locale: 'en' })} />);

    await waitFor(() => {
      expect(api.getAgents).toHaveBeenCalledWith(
        expect.objectContaining({
          sort_by: 'rating',
          sort_order: 'desc',
          page: 1,
          page_size: 12,
        })
      );
    });
  });

  it('renders pagination when total pages exceed 1', async () => {
    (api.getAgents as jest.Mock).mockResolvedValue({
      items: mockAgents,
      total: 25,
      page: 1,
      page_size: 12,
      total_pages: 3,
    });

    render(<AgentsPage params={Promise.resolve({ locale: 'en' })} />);

    await waitFor(() => {
      expect(screen.getByText('Previous')).toBeInTheDocument();
      expect(screen.getByText('Next')).toBeInTheDocument();
      expect(
        screen.getByText(copy('pages.agents.pagination', 'page', { page: 1, total: 3 }))
      ).toBeInTheDocument();
    });
  });

  it('disables Previous button on first page', async () => {
    (api.getAgents as jest.Mock).mockResolvedValue({
      items: mockAgents,
      total: 25,
      page: 1,
      page_size: 12,
      total_pages: 3,
    });

    render(<AgentsPage params={Promise.resolve({ locale: 'en' })} />);

    await waitFor(() => {
      const prevButton = screen.getByText('Previous').closest('button');
      expect(prevButton).toBeDisabled();
    });
  });

  it('navigates to next page when Next is clicked', async () => {
    (api.getAgents as jest.Mock).mockResolvedValue({
      items: mockAgents,
      total: 25,
      page: 1,
      page_size: 12,
      total_pages: 3,
    });

    render(<AgentsPage params={Promise.resolve({ locale: 'en' })} />);

    await waitFor(() => {
      expect(screen.getByText('Next')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Next'));

    await waitFor(() => {
      expect(api.getAgents).toHaveBeenCalledWith(
        expect.objectContaining({
          page: 2,
        })
      );
    });
  });

  it('does not render pagination when only one page', async () => {
    render(<AgentsPage params={Promise.resolve({ locale: 'en' })} />);

    await waitFor(() => {
      expect(screen.getByTestId('agent-card-agent-1')).toBeInTheDocument();
    });

    expect(screen.queryByText('Previous')).not.toBeInTheDocument();
    expect(screen.queryByText('Next')).not.toBeInTheDocument();
  });
});
