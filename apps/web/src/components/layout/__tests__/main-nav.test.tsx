import React from 'react';
import { render, screen } from '@testing-library/react';

import { MainNav } from '../main-nav';
import { usePathname } from '@/i18n/navigation';
import { useAuth } from '@/contexts/AuthContext';
import type { AuthContextType } from '@/contexts/AuthContext';

// `next-intl/navigation` is mocked globally, but `@/i18n/navigation` calls
// `createNavigation(routing)` at import time and the global mock does not
// export it — so the module has to be mocked per file.
jest.mock('@/i18n/navigation', () => ({
  Link: ({
    children,
    href,
    ...rest
  }: { children: React.ReactNode; href: string } & React.AnchorHTMLAttributes<HTMLAnchorElement>) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
  usePathname: jest.fn(() => '/'),
  useRouter: jest.fn(() => ({ push: jest.fn(), replace: jest.fn(), prefetch: jest.fn() })),
  redirect: jest.fn(),
  getPathname: jest.fn(() => '/'),
}));

jest.mock('@/contexts/AuthContext', () => ({
  useAuth: jest.fn(),
}));

jest.mock('@/components/auth/UserMenu', () => ({
  UserMenu: () => null,
}));

jest.mock('@/components/ui/language-switcher', () => ({
  LanguageSwitcher: () => null,
}));

const mockUsePathname = usePathname as jest.MockedFunction<typeof usePathname>;
const mockUseAuth = useAuth as jest.MockedFunction<typeof useAuth>;

function setAuth(overrides: Partial<AuthContextType> = {}) {
  mockUseAuth.mockReturnValue({
    user: null,
    isLoading: false,
    isAuthenticated: false,
    isDemoMode: false,
    error: null,
    ...overrides,
  } as AuthContextType);
}

describe('MainNav', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockUsePathname.mockReturnValue('/');
    setAuth();
  });

  it('renders the main navigation landmark with an accessible name', () => {
    render(<MainNav />);

    expect(screen.getByRole('navigation', { name: 'mainNavigation' })).toBeInTheDocument();
  });

  it('renders a link for every primary route', () => {
    render(<MainNav />);

    for (const label of [
      'search',
      'favorites',
      'documents',
      'cities',
      'assistant',
      'analytics',
      'agents',
      'knowledge',
      'settings',
    ]) {
      expect(screen.getByRole('link', { name: label })).toBeInTheDocument();
    }
  });

  it('points each route link at the matching path', () => {
    render(<MainNav />);

    expect(screen.getByRole('link', { name: 'search' })).toHaveAttribute('href', '/search');
    expect(screen.getByRole('link', { name: 'agents' })).toHaveAttribute('href', '/agents');
    expect(screen.getByRole('link', { name: 'knowledge' })).toHaveAttribute('href', '/knowledge');
  });

  it('marks the current route with aria-current', () => {
    mockUsePathname.mockReturnValue('/agents');
    render(<MainNav />);

    expect(screen.getByRole('link', { name: 'agents' })).toHaveAttribute('aria-current', 'page');
    expect(screen.getByRole('link', { name: 'search' })).not.toHaveAttribute('aria-current');
  });

  describe('demo mode', () => {
    it('keeps the demo-accessible routes visible', () => {
      setAuth({ isDemoMode: true });
      render(<MainNav />);

      for (const label of [
        'search',
        'cities',
        'analytics',
        'knowledge',
        'agents',
      ]) {
        expect(screen.getByRole('link', { name: label })).toBeInTheDocument();
      }
    });

    it('hides the routes that need an account', () => {
      setAuth({ isDemoMode: true });
      render(<MainNav />);

      expect(screen.queryByRole('link', { name: 'favorites' })).not.toBeInTheDocument();
      expect(screen.queryByRole('link', { name: 'documents' })).not.toBeInTheDocument();
      expect(screen.queryByRole('link', { name: 'settings' })).not.toBeInTheDocument();
    });

    it('shows the account-only routes outside demo mode', () => {
      setAuth({ isDemoMode: false });
      render(<MainNav />);

      expect(screen.getByRole('link', { name: 'favorites' })).toBeInTheDocument();
      expect(screen.getByRole('link', { name: 'documents' })).toBeInTheDocument();
      expect(screen.getByRole('link', { name: 'settings' })).toBeInTheDocument();
    });
  });
});
