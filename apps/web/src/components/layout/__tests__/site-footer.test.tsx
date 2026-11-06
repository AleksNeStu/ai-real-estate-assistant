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

describe('SiteFooter', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockFetch.mockReset();
    mockFetch.mockResolvedValue(
      new Response(JSON.stringify({ id: 'lead-1' }), {
        status: 201,
        headers: { 'Content-Type': 'application/json' },
      })
    );
  });

  it('renders the lead capture heading, field and consent note', () => {
    render(<SiteFooter />);

    expect(screen.getByText('t:title')).toBeInTheDocument();
    expect(screen.getByText('t:description')).toBeInTheDocument();
    expect(screen.getByLabelText('t:emailLabel')).toBeInTheDocument();
    expect(screen.getByText('t:consent')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 't:submit' })).toBeInTheDocument();
  });

  it('posts the email to the visitor lead endpoint', async () => {
    render(<SiteFooter />);

    fireEvent.change(screen.getByLabelText('t:emailLabel'), {
      target: { value: 'buyer@example.com' },
    });
    fireEvent.click(screen.getByRole('button', { name: 't:submit' }));

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledTimes(1);
    });

    const [url, init] = mockFetch.mock.calls[0] as [string, RequestInit];
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
    mockFetch.mockResolvedValue(new Response('nope', { status: 500 }));
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
    expect(mockFetch).not.toHaveBeenCalled();
  });
});
