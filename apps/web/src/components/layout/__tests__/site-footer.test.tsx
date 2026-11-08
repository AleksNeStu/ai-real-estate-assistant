import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';

import { SiteFooter } from '../site-footer';

// The global next-intl mock returns the raw key; make the strings readable so
// the assertions describe what the visitor sees.
jest.mock('next-intl', () => ({
  useTranslations: () => (key: string) => `t:${key}`,
}));

jest.mock('@/lib/visitor-tracking', () => ({
  getOrCreateVisitorId: jest.fn(() => 'visitor-uuid-1234'),
}));

const mockFetch = global.fetch as unknown as jest.Mock;

/** The capability payload the backend returns for a deployment without mail. */
const capabilitiesBody = {
  auth: { jwt_enabled: false, oauth: { google: false, apple: false } },
  email: { enabled: false, provider: 'dummy' },
  llm: { demo_mode: true, default_provider: 'zai' },
  observability: { error_tracking: false },
};

function mockApi({ emailEnabled = false }: { emailEnabled?: boolean } = {}) {
  mockFetch.mockImplementation((url: string) => {
    if (url.includes('/capabilities')) {
      return Promise.resolve(
        new Response(
          JSON.stringify({ ...capabilitiesBody, email: { enabled: emailEnabled, provider: emailEnabled ? 'smtp' : 'dummy' } }),
          { status: 200, headers: { 'Content-Type': 'application/json' } }
        )
      );
    }
    return Promise.resolve(
      new Response(JSON.stringify({ id: 'lead-1' }), {
        status: 201,
        headers: { 'Content-Type': 'application/json' },
      })
    );
  });
}

/** The calls that went to the lead endpoint, ignoring the capability probe. */
const leadCalls = () =>
  mockFetch.mock.calls.filter((call) => !String(call[0]).includes('/capabilities'));

describe('SiteFooter', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockFetch.mockReset();
    mockApi();
  });

  it('renders the lead capture heading, field and consent note', async () => {
    render(<SiteFooter />);

    expect(screen.getByText('t:title')).toBeInTheDocument();
    expect(screen.getByText('t:description')).toBeInTheDocument();
    expect(screen.getByLabelText('t:emailLabel')).toBeInTheDocument();
    expect(screen.getByText('t:consent')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 't:submit' })).toBeInTheDocument();

    // Let the capability probe settle so the state update happens inside the test.
    expect(await screen.findByText('t:demoNotice')).toBeInTheDocument();
  });

  it('states that this is the free version and links to the studio', async () => {
    render(<SiteFooter />);

    expect(screen.getByText('t:studioNote')).toBeInTheDocument();

    const studioLink = screen.getByRole('link', { name: 't:studioLink' });
    expect(studioLink).toHaveAttribute('href', 'https://nestlab.tech');
    expect(studioLink).toHaveAttribute('rel', expect.stringContaining('noopener'));

    expect(await screen.findByText('t:demoNotice')).toBeInTheDocument();
  });

  it('posts the email to the visitor lead endpoint', async () => {
    render(<SiteFooter />);

    fireEvent.change(screen.getByLabelText('t:emailLabel'), {
      target: { value: 'buyer@example.com' },
    });
    fireEvent.click(screen.getByRole('button', { name: 't:submit' }));

    await waitFor(() => {
      expect(leadCalls()).toHaveLength(1);
    });

    const [url, init] = leadCalls()[0] as [string, RequestInit];
    expect(url).toBe('/api/v1/leads/visitor');
    expect(init.method).toBe('POST');

    const body = JSON.parse(init.body as string);
    expect(body.email).toBe('buyer@example.com');
    expect(body.visitor_id).toBe('visitor-uuid-1234');
    expect(body.consent_given).toBe(true);
  });

  it('shows the success state after a successful submit', async () => {
    render(<SiteFooter />);

    fireEvent.change(screen.getByLabelText('t:emailLabel'), {
      target: { value: 'buyer@example.com' },
    });
    fireEvent.click(screen.getByRole('button', { name: 't:submit' }));

    expect(await screen.findByText('t:success')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 't:submit' })).not.toBeInTheDocument();
  });

  it('shows the error state when the request fails', async () => {
    mockFetch.mockImplementation((url: string) => {
      if (url.includes('/capabilities')) {
        return Promise.resolve(
          new Response(JSON.stringify(capabilitiesBody), {
            status: 200,
            headers: { 'Content-Type': 'application/json' },
          })
        );
      }
      return Promise.resolve(new Response('nope', { status: 500 }));
    });
    render(<SiteFooter />);

    fireEvent.change(screen.getByLabelText('t:emailLabel'), {
      target: { value: 'buyer@example.com' },
    });
    fireEvent.click(screen.getByRole('button', { name: 't:submit' }));

    expect(await screen.findByText('t:errorGeneric')).toBeInTheDocument();
    expect(screen.getByRole('alert')).toBeInTheDocument();
    expect(screen.queryByText('t:success')).not.toBeInTheDocument();
  });

  it('rejects an empty email without calling the API', async () => {
    render(<SiteFooter />);

    fireEvent.click(screen.getByRole('button', { name: 't:submit' }));

    expect(await screen.findByText('t:errorInvalidEmail')).toBeInTheDocument();
    expect(leadCalls()).toHaveLength(0);
  });

  it('says plainly that the demo does not send e-mail when the mail service is a dummy', async () => {
    render(<SiteFooter />);

    expect(await screen.findByText('t:demoNotice')).toBeInTheDocument();
  });

  it('drops the notice when the deployment really sends e-mail', async () => {
    mockApi({ emailEnabled: true });
    render(<SiteFooter />);

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalled();
    });
    expect(screen.queryByText('t:demoNotice')).not.toBeInTheDocument();
  });
});
