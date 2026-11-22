/**
 * The valuation page in its three modes.
 *
 * The mode that matters here is the third one: the reader names a city and a
 * street, and the page asks the official register what people actually paid
 * there. The test drives the real API client and asserts on the request it
 * puts on the wire and on the answer it shows.
 *
 * Note: `jest.mock('@/lib/api')` does not work in this project (Jest 30 +
 * next/jest) — the global `fetch` is mocked instead, the way the tools page
 * test does it.
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, jest, beforeEach } from '@jest/globals';

import ValuationPage from '../page';

const mockFetch = globalThis.fetch as unknown as jest.Mock;

const REGISTER_ANSWER = {
  property_id: null,
  estimated_value: 1017012,
  currency: 'PLN',
  source: 'rcn',
  confidence: 'low',
  sample_size: 3,
  comparison_area: 'Topolowa, Kraków',
  period_start: '2026-03-16',
  period_end: '2026-08-27',
  price_per_sqm_median: 20340,
  low: 986000,
  high: 1051000,
  notes: ['Only 3 sale(s) could be found for this flat — the estimate is indicative.'],
  comparables: [
    {
      address: 'Topolowa 47',
      area_sqm: 50.0,
      price: 1017012,
      price_per_sqm: 20340,
      transaction_date: '2026-05-12',
      rooms: 2,
      floor: 3,
      deed_reference: 'A/1234/26',
    },
  ],
};

const FORECAST_ANSWER = {
  current_estimate: 489000,
  currency: 'PLN',
  horizon_years: [1, 3],
  forecast: [],
  confidence: 0.62,
  drivers: [],
  explanation: '',
  comparables_used: 0,
  disclaimer: 'Not a formal appraisal.',
};

function mockResponse(body: unknown) {
  return Promise.resolve({
    ok: true,
    status: 200,
    json: () => Promise.resolve(body),
    text: () => Promise.resolve(JSON.stringify(body)),
    headers: new Headers(),
  });
}

/** Switch to the address mode, type the address, and submit. */
function fillAddressMode() {
  render(<ValuationPage />);
  fireEvent.click(screen.getByTestId('valuation-mode-address'));
  fireEvent.change(screen.getByLabelText('City'), { target: { value: 'Kraków' } });
  fireEvent.change(screen.getByLabelText('Street'), { target: { value: 'Topolowa' } });
  fireEvent.change(screen.getByLabelText('Area (sqm)'), { target: { value: '50' } });
  fireEvent.change(screen.getByLabelText('Rooms'), { target: { value: '2' } });
  fireEvent.click(screen.getByTestId('valuation-submit'));
}

/** The body of the last request to the given endpoint. */
function lastRequestBody(path: string): Record<string, unknown> | null {
  const calls = mockFetch.mock.calls as Array<[string, RequestInit?]>;
  const call = [...calls].reverse().find(([url]) => String(url).includes(path));
  if (!call) return null;
  return JSON.parse(String(call[1]?.body ?? '{}')) as Record<string, unknown>;
}

describe('ValuationPage — the by-address mode', () => {
  beforeEach(() => {
    mockFetch.mockReset();
    mockFetch.mockImplementation((url: string) => {
      if (String(url).includes('/tools/valuation')) return mockResponse(REGISTER_ANSWER);
      if (String(url).includes('/tools/price-forecast')) return mockResponse(FORECAST_ANSWER);
      return mockResponse({});
    });
  });

  it('asks the register with the address as typed', async () => {
    fillAddressMode();

    await waitFor(() =>
      expect(mockFetch.mock.calls.some(([url]) => String(url).includes('/tools/valuation'))).toBe(
        true
      )
    );
    expect(lastRequestBody('/tools/valuation')).toEqual({
      city: 'Kraków',
      street: 'Topolowa',
      area_sqm: 50,
      rooms: 2,
    });
  });

  it('shows the estimate with the facts that made it', async () => {
    fillAddressMode();

    await waitFor(() => expect(screen.getByTestId('register-valuation')).toBeInTheDocument());
    expect(screen.getByText('Estimated value')).toBeInTheDocument();
    expect(screen.getByText('Topolowa, Kraków')).toBeInTheDocument();
    expect(screen.getByText('3 registered sales')).toBeInTheDocument();
    expect(screen.getByText('2026-03-16 → 2026-08-27')).toBeInTheDocument();
  });

  it('lists the sales the estimate rests on', async () => {
    fillAddressMode();

    await waitFor(() => expect(screen.getByText('Topolowa 47')).toBeInTheDocument());
    expect(screen.getByText(/A\/1234\/26/)).toBeInTheDocument();
  });

  it('does not forecast when the register answers', async () => {
    fillAddressMode();

    await waitFor(() =>
      expect(mockFetch.mock.calls.some(([url]) => String(url).includes('/tools/valuation'))).toBe(
        true
      )
    );
    expect(
      mockFetch.mock.calls.some(([url]) => String(url).includes('/tools/price-forecast'))
    ).toBe(false);
  });

  it('keeps the forecast horizons out of the register mode', () => {
    render(<ValuationPage />);
    fireEvent.click(screen.getByTestId('valuation-mode-address'));

    expect(screen.queryByText('Forecast horizons')).not.toBeInTheDocument();
  });
});
