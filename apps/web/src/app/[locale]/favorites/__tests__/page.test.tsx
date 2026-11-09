import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import FavoritesPage from '../page';

// Mock lucide-react icons
jest.mock('lucide-react', () => ({
  ...jest.requireActual('lucide-react'),
  Loader2: (props: React.SVGProps<SVGSVGElement>) => <svg data-testid="loader-icon" {...props} />,
  Trash2: (props: React.SVGProps<SVGSVGElement>) => <svg data-testid="trash-icon" {...props} />,
  FolderPlus: (props: React.SVGProps<SVGSVGElement>) => (
    <svg data-testid="folder-plus-icon" {...props} />
  ),
}));

// Mock next/link
jest.mock('next/link', () => {
  return function MockLink({ children, href }: { children: React.ReactNode; href: string }) {
    return <a href={href}>{children}</a>;
  };
});

// Default mock implementations
const mockLoadFavorites = jest.fn().mockResolvedValue(undefined);
const mockRefreshCollections = jest.fn().mockResolvedValue(undefined);
const mockToggleFavorite = jest.fn().mockResolvedValue(false);
const mockAddCollection = jest.fn().mockResolvedValue({
  id: 'col-new',
  user_id: 'user-1',
  name: 'New Collection',
  description: '',
  is_default: false,
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
  favorite_count: 0,
});

let mockAuthState = {
  isAuthenticated: true,
  isLoading: false,
  user: { id: 'user-1', email: 'test@test.com' },
};

let mockFavoritesState = {
  favorites: [],
  collections: [],
  isLoading: false,
  error: null,
  loadFavoritesWithProperties: mockLoadFavorites,
  refreshCollections: mockRefreshCollections,
  addCollection: mockAddCollection,
  toggleFavorite: mockToggleFavorite,
};

jest.mock('@/contexts/AuthContext', () => ({
  useAuth: () => mockAuthState,
}));

jest.mock('@/contexts/FavoritesContext', () => ({
  useFavorites: () => mockFavoritesState,
}));

const favourite = {
  id: 'fav-1',
  user_id: 'user-1',
  property_id: 'prop-1',
  collection_id: null,
  notes: 'Viewing Sat 14 Nov, 10:30',
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
  is_available: true,
  property: {
    id: 'prop-1',
    title: 'Nice Apartment',
    price: 500000,
    currency: 'EUR',
    city: 'Berlin',
    neighborhood: 'Mitte',
    address: 'Main St 1',
    area_sqm: 80,
    rooms: 3,
    property_type: 'apartment' as const,
    listing_type: 'sale' as const,
    has_parking: false,
    has_garden: false,
    has_pool: false,
    has_garage: false,
    has_bike_room: false,
  },
};

describe('FavoritesPage', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    // Reset to authenticated default
    mockAuthState = {
      isAuthenticated: true,
      isLoading: false,
      user: { id: 'user-1', email: 'test@test.com' },
    };
    mockFavoritesState = {
      favorites: [],
      collections: [],
      isLoading: false,
      error: null,
      loadFavoritesWithProperties: mockLoadFavorites,
      refreshCollections: mockRefreshCollections,
      addCollection: mockAddCollection,
      toggleFavorite: mockToggleFavorite,
    };
  });

  it('renders without crashing', () => {
    render(<FavoritesPage />);
    expect(screen.getByText('My Favorites')).toBeInTheDocument();
  });

  it('shows loading spinner when auth is loading', () => {
    mockAuthState = {
      isAuthenticated: false,
      isLoading: true,
      user: null,
    };

    render(<FavoritesPage />);

    expect(screen.getByRole('status')).toBeInTheDocument();
  });

  it('shows the sign-in prompt when not authenticated', () => {
    mockAuthState = {
      isAuthenticated: false,
      isLoading: false,
      user: null,
    };

    render(<FavoritesPage />);

    expect(screen.getByRole('link', { name: 'Sign In' })).toBeInTheDocument();
  });

  it('shows empty state when authenticated with no favorites', () => {
    render(<FavoritesPage />);

    expect(screen.getByText('No favorites yet')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Browse Properties' })).toBeInTheDocument();
  });

  it('shows the saved count of the collection', () => {
    mockFavoritesState = { ...mockFavoritesState, favorites: [favourite] };

    render(<FavoritesPage />);

    expect(screen.getByText('1 saved property')).toBeInTheDocument();
  });

  it('draws the listing as a card with the price, the note and the street', () => {
    mockFavoritesState = { ...mockFavoritesState, favorites: [favourite] };

    render(<FavoritesPage />);

    expect(screen.getByTestId('favorite-card')).toBeInTheDocument();
    expect(screen.getByText('Nice Apartment')).toBeInTheDocument();
    // The price is mono, so it is written the way the locale writes money.
    expect(screen.getByText('€500,000')).toBeInTheDocument();
    // The note is part of the object, not decoration.
    expect(screen.getByText('Viewing Sat 14 Nov, 10:30')).toBeInTheDocument();
    expect(screen.getByText('Main St 1')).toBeInTheDocument();
  });

  it('removes a favourite when the remove button is pressed', async () => {
    mockFavoritesState = { ...mockFavoritesState, favorites: [favourite] };

    render(<FavoritesPage />);

    fireEvent.click(screen.getByRole('button', { name: 'Remove' }));

    await waitFor(() => {
      expect(mockToggleFavorite).toHaveBeenCalledWith('prop-1');
    });
    expect(mockLoadFavorites).toHaveBeenCalled();
  });

  it('shows unavailable property when property is null', () => {
    mockFavoritesState = {
      ...mockFavoritesState,
      favorites: [
        {
          id: 'fav-2',
          user_id: 'user-1',
          property_id: 'prop-delisted',
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          is_available: false,
          property: undefined,
        },
      ],
    };

    render(<FavoritesPage />);

    expect(screen.getByText('Property no longer available')).toBeInTheDocument();
    expect(screen.getByText('ID: prop-delisted')).toBeInTheDocument();
  });

  it('shows error alert when error is set', () => {
    mockFavoritesState = {
      ...mockFavoritesState,
      error: 'Failed to load favorites',
    };

    render(<FavoritesPage />);

    expect(screen.getByRole('alert')).toBeInTheDocument();
    expect(screen.getByText('Failed to load favorites')).toBeInTheDocument();
  });

  it('calls loadFavorites and refreshCollections on mount when authenticated', () => {
    render(<FavoritesPage />);

    expect(mockLoadFavorites).toHaveBeenCalled();
    expect(mockRefreshCollections).toHaveBeenCalled();
  });

  it('renders the collection rail with the count the API carries', () => {
    mockFavoritesState = {
      ...mockFavoritesState,
      collections: [
        {
          id: 'col-001',
          user_id: 'user-1',
          name: 'Family Homes',
          is_default: false,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          favorite_count: 4,
        },
      ],
    };

    render(<FavoritesPage />);

    const option = screen.getByRole('option', { name: /family homes/i });
    expect(option).toBeInTheDocument();
    expect(screen.getByRole('option', { name: /all favorites/i })).toBeInTheDocument();
    expect(screen.getByText('4')).toBeInTheDocument();
  });

  it('renders New Collection button', () => {
    render(<FavoritesPage />);

    expect(screen.getByText('New Collection')).toBeInTheDocument();
  });

  it('opens new collection modal on button click', () => {
    render(<FavoritesPage />);

    fireEvent.click(screen.getByText('New Collection'));

    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(screen.getByText('Create')).toBeInTheDocument();
    expect(screen.getByText('Cancel')).toBeInTheDocument();
  });
});
