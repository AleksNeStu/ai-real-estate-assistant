/**
 * Tests for attribution.ts — the arrival slot, the outbound click, and the
 * locale both of them carry.
 */

import { jest } from '@jest/globals';

(globalThis as unknown as { fetch: jest.Mock }).fetch = jest.fn();
const mockFetch = globalThis.fetch as jest.Mock;

import { currentSlot, reportArrival, reportOutbound } from '../attribution';

beforeEach(() => {
  jest.clearAllMocks();
  mockFetch.mockReset();
  mockFetch.mockResolvedValue({ ok: true } as Response);
  window.history.pushState({}, '', '/');
});

describe('currentSlot', () => {
  it('reads the slot from the query string', () => {
    window.history.pushState({}, '', '/pl/properties?from=hero');
    expect(currentSlot()).toBe('hero');
  });

  it('returns null when there is no slot', () => {
    window.history.pushState({}, '', '/pl/properties');
    expect(currentSlot()).toBeNull();
  });
});

describe('reportArrival', () => {
  it('sends the slot and the locale of the route', async () => {
    window.history.pushState({}, '', '/pl/properties?from=hero');

    await reportArrival();

    expect(mockFetch).toHaveBeenCalledTimes(1);
    const [url, opts] = mockFetch.mock.calls[0];
    expect(url).toBe('/api/v1/leads/track');
    const body = JSON.parse(opts.body);
    expect(body.metadata).toEqual({ slot: 'hero' });
    expect(body.locale).toBe('pl');
  });

  it('sends the English locale for an English route', async () => {
    window.history.pushState({}, '', '/en/properties?from=hero');

    await reportArrival();

    const body = JSON.parse(mockFetch.mock.calls[0][1].body);
    expect(body.locale).toBe('en');
  });

  it('sends no locale on a page that is not under one', async () => {
    window.history.pushState({}, '', '/properties?from=hero');

    await reportArrival();

    const body = JSON.parse(mockFetch.mock.calls[0][1].body);
    expect(body.locale).toBeUndefined();
  });

  it('does not report when there is no slot', async () => {
    window.history.pushState({}, '', '/pl/properties');

    await reportArrival();

    expect(mockFetch).not.toHaveBeenCalled();
  });

  it('drops the slot from the address bar', async () => {
    window.history.pushState({}, '', '/pl/properties?from=hero');

    await reportArrival();

    expect(window.location.search).toBe('');
  });
});

describe('reportOutbound', () => {
  it('sends the click and the locale of the route', async () => {
    window.history.pushState({}, '', '/pl/landing');

    await reportOutbound('https://studio.example', 'hero', 'spring');

    expect(mockFetch).toHaveBeenCalledTimes(1);
    const [url, opts] = mockFetch.mock.calls[0];
    expect(url).toBe('/api/v1/analytics/outbound');
    const body = JSON.parse(opts.body);
    expect(body.target).toBe('https://studio.example');
    expect(body.slot).toBe('hero');
    expect(body.campaign).toBe('spring');
    expect(body.locale).toBe('pl');
  });

  it('sends the English locale for an English route', async () => {
    window.history.pushState({}, '', '/en/landing');

    await reportOutbound('https://studio.example', 'hero');

    const body = JSON.parse(mockFetch.mock.calls[0][1].body);
    expect(body.locale).toBe('en');
  });

  it('sends no locale on a page that is not under one', async () => {
    window.history.pushState({}, '', '/landing');

    await reportOutbound('https://studio.example', 'hero');

    const body = JSON.parse(mockFetch.mock.calls[0][1].body);
    expect(body.locale).toBeUndefined();
  });
});
