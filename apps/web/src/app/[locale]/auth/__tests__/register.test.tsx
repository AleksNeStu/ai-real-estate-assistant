import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import RegisterPage from '../register/page';

// Mock next-intl is handled globally via __mocks__/next-intl.tsx
// The mock useTranslations returns the key itself, e.g. t('register.fullNameLabel') => 'register.fullNameLabel'

// Shared mock push reference so the module-level next/navigation mock uses it
const mockPush = jest.fn();

// Override next/navigation mock for this test file
jest.mock('next/navigation', () => ({
  useRouter: () => ({ push: mockPush, replace: jest.fn(), prefetch: jest.fn() }),
  useSearchParams: () => new URLSearchParams(),
  usePathname: () => '/',
  useParams: () => ({}),
}));

// Mock hooks and modules used by the register page
jest.mock('@/hooks/useAuth', () => ({
  useAuth: () => ({
    refreshUser: jest.fn().mockResolvedValue(undefined),
  }),
}));
jest.mock('@/lib/auth', () => ({
  register: jest.fn().mockResolvedValue(undefined),
}));
jest.mock('@/components/auth/OAuthButtons', () => ({
  OAuthButtons: ({ isLoading }: { isLoading: boolean }) => (
    <div data-testid="oauth-buttons">OAuth {isLoading ? 'loading' : 'ready'}</div>
  ),
}));

describe('RegisterPage', () => {
  beforeEach(() => {
    jest.useFakeTimers();
    jest.clearAllMocks();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it('renders registration form correctly', () => {
    render(<RegisterPage />);
    // The mock resolves the real `en` catalogue, so the form shows the copy a reader sees
    expect(screen.getByText('Create an account')).toBeInTheDocument();
    expect(screen.getByLabelText('Full Name')).toBeInTheDocument();
    expect(screen.getByLabelText('Email')).toBeInTheDocument();
    expect(screen.getByLabelText('Password')).toBeInTheDocument();
    // Submit button text is t('register.submit')
    expect(screen.getByRole('button', { name: /create account/i })).toBeInTheDocument();
  });

  it('submits form with correct values', async () => {
    render(<RegisterPage />);

    const nameInput = screen.getByLabelText('Full Name');
    const emailInput = screen.getByLabelText('Email');
    const passwordInput = screen.getByLabelText('Password');
    const submitButton = screen.getByRole('button', { name: /create account/i });

    fireEvent.change(nameInput, { target: { value: 'John Doe' } });
    fireEvent.change(emailInput, { target: { value: 'test@example.com' } });
    fireEvent.change(passwordInput, { target: { value: 'password123' } });

    fireEvent.click(submitButton);

    // Check loading state
    expect(submitButton).toBeDisabled();
    expect(document.querySelector('.animate-spin')).toBeTruthy();

    // Fast-forward time wrapped in act
    act(() => {
      jest.runAllTimers();
    });

    // Wait for mock API call
    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith('/');
    });
  });
});
