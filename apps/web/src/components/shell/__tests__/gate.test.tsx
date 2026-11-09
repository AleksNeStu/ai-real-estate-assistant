import { render, screen, waitFor } from '@testing-library/react';

import { AccountGate } from '@/components/shell/gate';
import { useAuth } from '@/contexts/AuthContext';
import { useCapabilities } from '@/hooks/useCapabilities';

/**
 * The gate decides whether an account route is open.
 *
 * It has three answers, and the wrong one is costly: a gate on a deployment
 * that lets everyone in throws away a working page, and a missing gate on a
 * deployment that needs an account shows a page whose data never arrives.
 * Both answers come from the backend, so these tests give the gate those two
 * answers and watch what it does.
 */

jest.mock('@/contexts/AuthContext', () => ({
  useAuth: jest.fn(),
}));

jest.mock('@/hooks/useCapabilities', () => ({
  useCapabilities: jest.fn(),
}));

const mockAuth = useAuth as jest.MockedFunction<typeof useAuth>;
const mockCapabilities = useCapabilities as jest.MockedFunction<typeof useCapabilities>;

function capabilities(overrides: Record<string, unknown> = {}) {
  return {
    capabilities: {
      auth: { jwt_enabled: true, demo_user_bypass: false, oauth: { google: false, apple: false } },
      email: { enabled: false, provider: 'dummy' },
      llm: { demo_mode: true, mode: 'provider', provider: 'minimax', model: 'MiniMax-M3.1-Flash' },
      lead_capture: { waitlist_enabled: false },
      observability: { error_tracking: false },
      ...overrides,
    },
    loading: false,
  } as unknown as ReturnType<typeof useCapabilities>;
}

function auth(overrides: Record<string, unknown> = {}) {
  return {
    user: null,
    isLoading: false,
    isAuthenticated: false,
    isDemoMode: false,
    error: null,
    login: jest.fn(),
    register: jest.fn(),
    logout: jest.fn(),
    refreshUser: jest.fn(),
    clearError: jest.fn(),
    setIsDemoMode: jest.fn(),
    ...overrides,
  } as unknown as ReturnType<typeof useAuth>;
}

describe('the gate on the account routes', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockAuth.mockReturnValue(auth());
    mockCapabilities.mockReturnValue(capabilities());
  });

  it('asks for an account when the deployment needs one', async () => {
    render(
      <AccountGate route="favorites">
        <div>the favourites page</div>
      </AccountGate>
    );

    await waitFor(() => {
      expect(screen.getByText('Your shortlists')).toBeInTheDocument();
    });
    expect(screen.getByText('/favorites · needs an account')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Sign in' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Create an account' })).toBeInTheDocument();
    expect(screen.queryByText('the favourites page')).not.toBeInTheDocument();
  });

  it('says what the account gives', async () => {
    render(
      <AccountGate route="usage">
        <div>the usage page</div>
      </AccountGate>
    );

    await waitFor(() => {
      expect(screen.getByText('What happened on your deployment')).toBeInTheDocument();
    });
    expect(screen.getByText('after sign-in you get')).toBeInTheDocument();
    expect(screen.getByText('One screen for the whole activity')).toBeInTheDocument();
  });

  it('lets a signed-in visitor through', async () => {
    mockAuth.mockReturnValue(auth({ isAuthenticated: true, user: { id: 'u1' } }));

    render(
      <AccountGate route="favorites">
        <div>the favourites page</div>
      </AccountGate>
    );

    await waitFor(() => {
      expect(screen.getByText('the favourites page')).toBeInTheDocument();
    });
    expect(screen.queryByText('Your shortlists')).not.toBeInTheDocument();
  });

  it('lets a visitor through when the deployment hands out a demo user', async () => {
    mockCapabilities.mockReturnValue(
      capabilities({
        auth: { jwt_enabled: true, demo_user_bypass: true, oauth: { google: false, apple: false } },
      })
    );

    render(
      <AccountGate route="favorites">
        <div>the favourites page</div>
      </AccountGate>
    );

    await waitFor(() => {
      expect(screen.getByText('the favourites page')).toBeInTheDocument();
    });
    expect(screen.queryByText('Your shortlists')).not.toBeInTheDocument();
  });

  it('lets a visitor through when the deployment has no accounts at all', async () => {
    mockCapabilities.mockReturnValue(
      capabilities({
        auth: { jwt_enabled: false, demo_user_bypass: false, oauth: { google: false, apple: false } },
      })
    );

    render(
      <AccountGate route="favorites">
        <div>the favourites page</div>
      </AccountGate>
    );

    await waitFor(() => {
      expect(screen.getByText('the favourites page')).toBeInTheDocument();
    });
  });

  it('lets a visitor through when the deployment cannot be asked', async () => {
    // A capabilities endpoint that does not answer must not hide the app.
    mockCapabilities.mockReturnValue({ capabilities: null, loading: false });

    render(
      <AccountGate route="favorites">
        <div>the favourites page</div>
      </AccountGate>
    );

    await waitFor(() => {
      expect(screen.getByText('the favourites page')).toBeInTheDocument();
    });
  });
});
