import { render, screen, waitFor } from '@testing-library/react';

import ForgotPasswordPage from '../forgot-password/page';
import VerifyEmailPage from '../verify-email/page';
import { getCapabilities } from '@/lib/api';
import { verifyEmail } from '@/lib/auth';

/**
 * The two screens that talk about mail.
 *
 * A deployment that cannot send mail must not promise a mail: the
 * capabilities endpoint is the truth, and the copy follows it. The reset
 * link of such a deployment is printed in the API log instead of being
 * mailed, and the page says so.
 */

jest.mock('@/lib/api', () => ({
  getCapabilities: jest.fn(),
}));

jest.mock('@/lib/auth', () => ({
  verifyEmail: jest.fn(),
}));

jest.mock('next/navigation', () => ({
  useRouter: () => ({ push: jest.fn(), replace: jest.fn(), prefetch: jest.fn() }),
  useSearchParams: () => new URLSearchParams('token=abc'),
  usePathname: () => '/',
  useParams: () => ({}),
}));

const capabilities = (emailEnabled: boolean) => ({
  auth: {
    jwt_enabled: true,
    demo_user_bypass: false,
    oauth: { google: false, apple: false },
  },
  email: { enabled: emailEnabled, provider: emailEnabled ? 'smtp' : 'dummy' },
  llm: { demo_mode: true, mode: 'local-model', provider: 'ollama', model: 'demo' },
  lead_capture: { waitlist_enabled: emailEnabled },
  observability: { error_tracking: false },
});

describe('the auth screens that talk about mail', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    // The verification never settles: the page stays in its waiting state,
    // which is where the copy about the mail is written.
    (verifyEmail as jest.Mock).mockReturnValue(new Promise(() => {}));
  });

  it('tells the reader on the reset page that the link is printed in the log', async () => {
    (getCapabilities as jest.Mock).mockResolvedValue(capabilities(false));

    render(<ForgotPasswordPage />);

    await waitFor(() =>
      expect(
        screen.getByText(/printed in the API log instead of being mailed/i)
      ).toBeInTheDocument()
    );
  });

  it('does not warn about the log when the deployment really sends mail', async () => {
    (getCapabilities as jest.Mock).mockResolvedValue(capabilities(true));

    render(<ForgotPasswordPage />);

    await waitFor(() => expect(getCapabilities).toHaveBeenCalled());
    expect(
      screen.queryByText(/printed in the API log instead of being mailed/i)
    ).not.toBeInTheDocument();
  });

  it('does not promise a confirmation link on the verify page when no mail leaves', async () => {
    (getCapabilities as jest.Mock).mockResolvedValue(capabilities(false));

    render(<VerifyEmailPage />);

    await waitFor(() =>
      expect(
        screen.queryByText(/sent a verification link to your e-mail/i)
      ).not.toBeInTheDocument()
    );
    expect(screen.getByText(/sends no e-mail/i)).toBeInTheDocument();
  });

  it('promises the confirmation link when the deployment really sends mail', async () => {
    (getCapabilities as jest.Mock).mockResolvedValue(capabilities(true));

    render(<VerifyEmailPage />);

    await waitFor(() =>
      expect(
        screen.getByText(/sent a verification link to your e-mail/i)
      ).toBeInTheDocument()
    );
  });
});
