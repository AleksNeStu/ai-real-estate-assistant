import { fireEvent, render, screen, waitFor } from '@testing-library/react';

import { DataCoverage } from '@/components/landing/data-coverage';
import { WaitlistForm } from '@/components/landing/waitlist-form';

/**
 * The landing has one job the rest of the site does not: it turns a visitor
 * into a lead. These two tests watch that it does it honestly - the numbers
 * on the page are the catalogue's own, and the waitlist posts a real lead
 * with its own source and its consent.
 */

function mockFetch(handler: (url: string, init?: RequestInit) => unknown) {
  const fetchMock = jest.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    const body = handler(url, init);
    return {
      ok: true,
      status: 200,
      json: async () => body,
    } as unknown as Response;
  });
  global.fetch = fetchMock as unknown as typeof fetch;
  return fetchMock;
}

describe('the catalogue statistics on the landing', () => {
  it('shows what the catalogue actually holds', async () => {
    mockFetch(() => ({
      total: 252,
      agents: 15,
      cities: [
        { name: 'Warsaw', count: 62 },
        { name: 'Kraków', count: 58 },
      ],
      currencies: ['PLN'],
    }));

    render(<DataCoverage />);

    await waitFor(() => {
      expect(screen.getByText('252 properties · 15 agents')).toBeInTheDocument();
    });
    expect(screen.getByText('Warsaw')).toBeInTheDocument();
    expect(screen.getByText('Kraków')).toBeInTheDocument();
    expect(screen.getByText('No live feed runs on this demo.')).toBeInTheDocument();
  });
});

describe('the PropVector AI waitlist', () => {
  it('posts the address as a lead with its own source and its consent', async () => {
    const fetchMock = mockFetch(() => ({}));

    render(<WaitlistForm />);

    fireEvent.change(screen.getByLabelText('E-mail for the PropVector AI launch'), {
      target: { value: 'a@b.co' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Notify me' }));

    await waitFor(() => {
      const call = fetchMock.mock.calls.find(([url]) => String(url).endsWith('/leads/visitor'));
      expect(call).toBeDefined();
      const body = JSON.parse((call?.[1]?.body as string) ?? '{}');
      expect(body.email).toBe('a@b.co');
      expect(body.source).toBe('propvector_waitlist');
      expect(body.consent_given).toBe(true);
      expect(typeof body.visitor_id).toBe('string');
    });
  });
});
