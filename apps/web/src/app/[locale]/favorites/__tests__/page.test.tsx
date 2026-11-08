import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import FavoritesPage from '../page';

// Mock lucide-react icons
jest.mock('lucide-react', () => ({
  ...jest.requireActual('lucide-react'),
  Loader2: (props: React.SVGProps<SVGSVGElement>) => <svg data-testid="loader-icon" {...props} />,
  Heart: (props: React.SVGProps<SVGSVGElement>) => <svg data-testid="heart-icon" {...props} />,
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

// Mock PropertyCard
jest.mock('@/components/property', () => ({
  PropertyCard: ({ property }: { property: { id: string } }) => (
    <div data-testid={`property-card-${property.id}`}>Property {property.id}</div>
  ),
}));

// Default mock implementations
const mockLoadFavorites = jest.fn().mockResolvedValue(undefined);
const mockRefreshCollections = jest.fn().mockResolvedValue(undefined);
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
};

jest.mock('@/contexts/AuthContext', () => ({
  useAuth: () => mockAuthState,
}));

jest.mock('@/contexts/FavoritesContext', () => ({
  useFavorites: () => mockFavoritesState,
}));

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

  it('shows sign in prompt when not authenticated', () => {
    mockAuthState = {
      isAuthenticated: false,
      isLoading: false,
      user: null,
    };

    render(<FavoritesPage />);

    expect(screen.getByText('Sign in to view your favorites')).toBeInTheDocument();
    expect(screen.getByText('Sign In')).toBeInTheDocument();
  });

  it('shows empty state when authenticated with no favorites', () => {
    render(<FavoritesPage />);

    expect(screen.getByText('No favorites yet')).toBeInTheDocument();
    expect(screen.getByText('Browse Properties')).toBeInTheDocument();
  });

  it('shows favorites list when authenticated with data', () => {
    mockFavoritesState = {
      ...mockFavoritesState,
      favorites: [
        {
          id: 'fav-1',
          user_id: 'user-1',
          property_id: 'prop-1',
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          is_available: true,
          property: {
            id: 'prop-1',
            title: 'Nice Apartment',
            price: 500000,
            city: 'Berlin',
            address: 'Main St 1',
            area: 80,
            rooms: 3,
            property_type: 'apartment',
            status: 'available',
            latitude: 52.52,
            longitude: 13.405,
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
          },
        },
      ],
    };

    render(<FavoritesPage />);

    expect(screen.getByText('1 saved property')).toBeInTheDocument();
    expect(screen.getByTestId('property-card-prop-1')).toBeInTheDocument();
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
