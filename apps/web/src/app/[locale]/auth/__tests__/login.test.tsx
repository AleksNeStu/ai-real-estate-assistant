import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import LoginPage from '../login/page';
import { login } from '@/lib/auth';

// Shared mock push reference so the module-level next/navigation mock uses it
const mockPush = jest.fn();

// Mock useRouter and useSearchParams
jest.mock('next/navigation', () => ({
  useRouter: () => ({ push: mockPush, replace: jest.fn(), prefetch: jest.fn() }),
  useSearchParams: () => new URLSearchParams(),
}));

// The global next-intl mock returns the raw translation key. The page renders
// user-visible English, so the mock resolves the real `en` messages.
jest.mock('next-intl', () => {
  const messages = jest.requireActual<Record<string, unknown>>('../../../../../messages/en.json');
  const resolve = (path: string): unknown =>
    path.split('.').reduce<unknown>(
      (acc, part) =>
        acc && typeof acc === 'object' ? (acc as Record<string, unknown>)[part] : undefined,
      messages
    );
  const interpolate = (template: string, params?: Record<string, unknown>) =>
    params
      ? template.replace(/\{(\w+)\}/g, (match, name) =>
          name in params ? String(params[name]) : match
        )
      : template;
  return {
    useTranslations:
      (namespace?: string) =>
      (key: string, params?: Record<string, unknown>) => {
        const value = resolve(namespace ? `${namespace}.${key}` : key);
        return typeof value === 'string' ? interpolate(value, params) : key;
      },
    useLocale: () => 'en',
    useMessages: () => messages,
    NextIntlClientProvider: ({ children }: { children: React.ReactNode }) => children,
  };
});

// Mock hooks and modules used by the login page
jest.mock('@/hooks/useAuth', () => ({
  useAuth: () => ({
    refreshUser: jest.fn().mockResolvedValue(undefined),
  }),
}));
jest.mock('@/lib/auth', () => ({
  login: jest.fn().mockResolvedValue(undefined),
  oauthLogin: jest.fn().mockResolvedValue(undefined),
}));
jest.mock('@/components/auth/OAuthButtons', () => ({
  OAuthButtons: ({ isLoading }: { isLoading: boolean }) => (
    <div data-testid="oauth-buttons">OAuth {isLoading ? 'loading' : 'ready'}</div>
  ),
}));

describe('LoginPage', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    window.localStorage.clear();
  });

  it('renders login form correctly', () => {
    render(<LoginPage />);
    expect(screen.getByText('Welcome back')).toBeInTheDocument();
    expect(screen.getByLabelText('Email')).toBeInTheDocument();
    expect(screen.getByLabelText('Password')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument();
  });

  it('submits form with correct values', async () => {
    render(<LoginPage />);

    const emailInput = screen.getByLabelText('Email');
    const passwordInput = screen.getByLabelText('Password');
    const submitButton = screen.getByRole('button', { name: /sign in/i });

    fireEvent.change(emailInput, { target: { value: 'test@example.com' } });
    fireEvent.change(passwordInput, { target: { value: 'password123' } });

    fireEvent.click(submitButton);

    // Check loading state
    expect(submitButton).toBeDisabled();
    expect(document.querySelector('.animate-spin')).toBeTruthy();

    // Wait for the mocked login call and the redirect to the locale root
    await waitFor(() => {
      expect(login).toHaveBeenCalledWith('test@example.com', 'password123');
      expect(mockPush).toHaveBeenCalledWith('/en');
    });
  });

  it('shows an error message when login fails', async () => {
    (login as jest.Mock).mockRejectedValueOnce(new Error('Invalid credentials'));

    render(<LoginPage />);

    const emailInput = screen.getByLabelText('Email');
    const passwordInput = screen.getByLabelText('Password');
    const submitButton = screen.getByRole('button', { name: /sign in/i });

    fireEvent.change(emailInput, { target: { value: 'test@example.com' } });
    fireEvent.change(passwordInput, { target: { value: 'wrong' } });
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent('Invalid credentials');
    });
    expect(mockPush).not.toHaveBeenCalled();
  });
});
