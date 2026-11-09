import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import SavedSearchesPage from '../page';
import * as api from '@/lib/api';
import type { SavedSearch } from '@/lib/types';

// Mock lucide-react icons
jest.mock('lucide-react', () => ({
  ...jest.requireActual('lucide-react'),
  AlertCircle: (props: React.SVGProps<SVGSVGElement>) => (
    <svg data-testid="alert-circle-icon" {...props} />
  ),
  Loader2: (props: React.SVGProps<SVGSVGElement>) => (
    <svg data-testid="loader-icon" {...props} />
  ),
  RefreshCw: (props: React.SVGProps<SVGSVGElement>) => (
    <svg data-testid="refresh-icon" {...props} />
  ),
  Search: (props: React.SVGProps<SVGSVGElement>) => <svg data-testid="search-icon" {...props} />,
  Trash2: (props: React.SVGProps<SVGSVGElement>) => <svg data-testid="trash-icon" {...props} />,
}));

// Mock the API module
jest.mock('@/lib/api', () => {
  class MockApiError extends Error {
    public category?: string;
    constructor(
      message: string,
      public status: number,
      public request_id?: string
    ) {
      super(message);
      this.name = 'ApiError';
    }
  }
  return {
    getSavedSearches: jest.fn(),
    deleteSavedSearch: jest.fn(),
    toggleSavedSearchAlert: jest.fn(),
    ApiError: MockApiError,
  };
});

const mockSearches: SavedSearch[] = [
  {
    id: 'search-1',
    user_id: 'user-1',
    name: 'Berlin Apartments',
    description: 'Looking for 2-room apartments in Berlin',
    filters: {
      city: 'Berlin',
      min_price: 100000,
      max_price: 500000,
      property_types: ['apartment'],
    },
    alert_frequency: 'daily',
    is_active: true,
    notify_on_new: true,
    notify_on_price_drop: false,
    created_at: '2024-01-15T10:00:00Z',
    updated_at: '2024-01-20T14:30:00Z',
    use_count: 5,
  },
  {
    id: 'search-2',
    user_id: 'user-1',
    name: 'Munich Houses',
    filters: { city: 'Munich', min_rooms: 3, max_rooms: 5 },
    alert_frequency: 'weekly',
    is_active: false,
    notify_on_new: false,
    notify_on_price_drop: true,
    created_at: '2024-02-01T08:00:00Z',
    updated_at: '2024-02-10T12:00:00Z',
    use_count: 2,
  },
];

describe('SavedSearchesPage', () => {
  const mockGetSavedSearches = api.getSavedSearches as jest.Mock;
  const mockDeleteSavedSearch = api.deleteSavedSearch as jest.Mock;
  const mockToggleAlert = api.toggleSavedSearchAlert as jest.Mock;

  beforeEach(() => {
    jest.clearAllMocks();
    // Default: return empty items to resolve loading quickly
    mockGetSavedSearches.mockResolvedValue({ items: [], total: 0 });
  });

  it('renders page title after loading', async () => {
    render(<SavedSearchesPage />);

    await waitFor(() => {
      expect(screen.getByText('Saved Searches')).toBeInTheDocument();
    });
  });

  it('shows loading state initially', () => {
    // Keep the promise pending so loading stays true
    mockGetSavedSearches.mockImplementation(() => new Promise(() => {}));

    render(<SavedSearchesPage />);

    expect(screen.getByRole('status')).toBeInTheDocument();
  });

  it('shows empty state when no saved searches', async () => {
    mockGetSavedSearches.mockResolvedValue({ items: [], total: 0 });

    render(<SavedSearchesPage />);

    await waitFor(() => {
      expect(screen.getByText('No saved searches yet')).toBeInTheDocument();
    });
  });

  it('counts the alerts that are running', async () => {
    mockGetSavedSearches.mockResolvedValue({ items: mockSearches, total: 2 });

    render(<SavedSearchesPage />);

    await waitFor(() => {
      expect(screen.getByText('1 of 2 alerts active')).toBeInTheDocument();
    });
  });

  it('renders saved search items from API', async () => {
    mockGetSavedSearches.mockResolvedValue({ items: mockSearches, total: 2 });

    render(<SavedSearchesPage />);

    await waitFor(() => {
      expect(screen.getByText('Berlin Apartments')).toBeInTheDocument();
      expect(screen.getByText('Munich Houses')).toBeInTheDocument();
    });

    // The filters are written the way the search route writes its chips.
    expect(
      screen.getByText('city = Berlin · price ≥ 100,000 · price ≤ 500,000 · type = apartment')
    ).toBeInTheDocument();
    expect(screen.getByText('city = Munich · rooms = 3-5')).toBeInTheDocument();
    // The use count and the creation date are the ones the API carried.
    expect(screen.getByText(/Used: 5 times/)).toBeInTheDocument();
    expect(screen.getByText(/Used: 2 times/)).toBeInTheDocument();
    expect(screen.getAllByText(/Created:/)).toHaveLength(2);
  });

  it('writes the rule each alert watches with', async () => {
    mockGetSavedSearches.mockResolvedValue({ items: mockSearches, total: 2 });

    render(<SavedSearchesPage />);

    await waitFor(() => {
      expect(screen.getByText('Berlin Apartments')).toBeInTheDocument();
    });

    expect(screen.getByText('New matches')).toBeInTheDocument();
    expect(screen.getByText('Price drops')).toBeInTheDocument();
    expect(screen.getByText('Daily')).toBeInTheDocument();
    expect(screen.getByText('Weekly')).toBeInTheDocument();
  });

  it('shows the switch of every search with its state', async () => {
    mockGetSavedSearches.mockResolvedValue({ items: mockSearches, total: 2 });

    render(<SavedSearchesPage />);

    await waitFor(() => {
      expect(screen.getByText('Berlin Apartments')).toBeInTheDocument();
    });

    const switches = screen.getAllByRole('switch');
    expect(switches).toHaveLength(2);
    expect(switches[0]).toHaveAttribute('aria-checked', 'true');
    expect(switches[1]).toHaveAttribute('aria-checked', 'false');
    expect(screen.getByText('Alert on')).toBeInTheDocument();
    expect(screen.getByText('Paused')).toBeInTheDocument();
  });

  it('handles delete button click with confirmation', async () => {
    // Mock window.confirm
    const confirmSpy = jest.spyOn(window, 'confirm').mockReturnValue(true);
    mockGetSavedSearches.mockResolvedValue({ items: mockSearches, total: 2 });
    mockDeleteSavedSearch.mockResolvedValue(undefined);

    render(<SavedSearchesPage />);

    await waitFor(() => {
      expect(screen.getByText('Berlin Apartments')).toBeInTheDocument();
    });

    // Click the delete button for the first search
    const deleteButtons = screen.getAllByTitle('Delete search');
    fireEvent.click(deleteButtons[0]);

    expect(confirmSpy).toHaveBeenCalledWith('Are you sure you want to delete "Berlin Apartments"?');
    await waitFor(() => {
      expect(mockDeleteSavedSearch).toHaveBeenCalledWith('search-1');
    });

    confirmSpy.mockRestore();
  });

  it('does not delete when confirmation is cancelled', async () => {
    const confirmSpy = jest.spyOn(window, 'confirm').mockReturnValue(false);
    mockGetSavedSearches.mockResolvedValue({ items: mockSearches, total: 2 });

    render(<SavedSearchesPage />);

    await waitFor(() => {
      expect(screen.getByText('Berlin Apartments')).toBeInTheDocument();
    });

    const deleteButtons = screen.getAllByTitle('Delete search');
    fireEvent.click(deleteButtons[0]);

    expect(confirmSpy).toHaveBeenCalled();
    expect(mockDeleteSavedSearch).not.toHaveBeenCalled();

    confirmSpy.mockRestore();
  });

  it('handles toggle alert button click', async () => {
    mockGetSavedSearches.mockResolvedValue({ items: mockSearches, total: 2 });
    const updatedSearch = { ...mockSearches[0], is_active: false };
    mockToggleAlert.mockResolvedValue(updatedSearch);

    render(<SavedSearchesPage />);

    await waitFor(() => {
      expect(screen.getByText('Berlin Apartments')).toBeInTheDocument();
    });

    // Click the switch of the active search (Berlin - is_active: true)
    fireEvent.click(screen.getAllByRole('switch')[0]);

    await waitFor(() => {
      expect(mockToggleAlert).toHaveBeenCalledWith('search-1', false);
    });
  });

  it('shows error state when API fails', async () => {
    const errorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
    const apiError = new Error('Network error');
    mockGetSavedSearches.mockRejectedValue(apiError);

    render(<SavedSearchesPage />);

    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument();
      expect(screen.getByText('Network error')).toBeInTheDocument();
    });

    errorSpy.mockRestore();
  });

  it('renders Refresh button', async () => {
    render(<SavedSearchesPage />);

    await waitFor(() => {
      expect(screen.getByLabelText('Refresh saved searches')).toBeInTheDocument();
    });
  });

  it('renders description when present', async () => {
    mockGetSavedSearches.mockResolvedValue({ items: mockSearches, total: 2 });

    render(<SavedSearchesPage />);

    await waitFor(() => {
      expect(screen.getByText('Looking for 2-room apartments in Berlin')).toBeInTheDocument();
    });
  });
});
