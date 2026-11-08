import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { OAuthButtons } from '../OAuthButtons';
import { getCapabilities } from '@/lib/api';
import { oauthLogin } from '@/lib/auth';
import { toast } from 'sonner';

jest.mock('@/lib/api', () => ({
  getCapabilities: jest.fn(),
}));

jest.mock('@/lib/auth', () => ({
  oauthLogin: jest.fn(),
}));

jest.mock('sonner', () => ({
  toast: { error: jest.fn() },
}));

const capabilities = (google: boolean, apple: boolean) => ({
  auth: {
    jwt_enabled: false,
    oauth: { google, apple },
  },
  email: { enabled: false, provider: 'dummy' },
  llm: { demo_mode: true, default_provider: 'zai' },
  observability: { error_tracking: false },
});

describe('OAuthButtons', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders no button when the deployment has no OAuth provider', async () => {
    (getCapabilities as jest.Mock).mockResolvedValue(capabilities(false, false));

    render(<OAuthButtons />);

    await waitFor(() => expect(getCapabilities).toHaveBeenCalled());
    expect(screen.queryByRole('button', { name: /google/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /apple/i })).not.toBeInTheDocument();
  });

  it('renders only the provider the backend reports as configured', async () => {
    (getCapabilities as jest.Mock).mockResolvedValue(capabilities(true, false));

    render(<OAuthButtons />);

    await waitFor(() =>
      expect(screen.getByRole('button', { name: /google/i })).toBeInTheDocument()
    );
    expect(screen.queryByRole('button', { name: /apple/i })).not.toBeInTheDocument();
  });

  it('renders both providers when both are configured', async () => {
    (getCapabilities as jest.Mock).mockResolvedValue(capabilities(true, true));

    render(<OAuthButtons />);

    await waitFor(() =>
      expect(screen.getByRole('button', { name: /google/i })).toBeInTheDocument()
    );
    expect(screen.getByRole('button', { name: /apple/i })).toBeInTheDocument();
  });

  it('renders no button when the capability endpoint cannot be reached', async () => {
    (getCapabilities as jest.Mock).mockRejectedValue(new Error('network down'));

    render(<OAuthButtons />);

    await waitFor(() => expect(getCapabilities).toHaveBeenCalled());
    expect(screen.queryByRole('button', { name: /google/i })).not.toBeInTheDocument();
  });

  it('reports a human sentence instead of the raw API detail', async () => {
    (getCapabilities as jest.Mock).mockResolvedValue(capabilities(true, false));
    (oauthLogin as jest.Mock).mockRejectedValue(new Error('Google OAuth is not enabled'));

    render(<OAuthButtons />);

    const button = await screen.findByRole('button', { name: /google/i });
    fireEvent.click(button);

    await waitFor(() => expect(toast.error).toHaveBeenCalledWith('Authentication failed'));
    // The raw API string must never reach the visitor.
    expect(toast.error).not.toHaveBeenCalledWith('Google OAuth is not enabled');
  });
});
