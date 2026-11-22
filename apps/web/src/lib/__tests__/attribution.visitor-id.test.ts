/**
 * Tests for attribution.ts — the visitor id the arrival and the outbound
 * click carry (Task #109).
 *
 * An arrival without an id is rejected by the API, and an outbound click
 * without one is filed under the literal "anonymous" - so neither row can
 * be tied to the lead the visitor already has. The id lives in a cookie and
 * is sent with both rows.
 */

import { jest } from '@jest/globals';

(globalThis as unknown as { fetch: jest.Mock }).fetch = jest.fn();
const mockFetch = globalThis.fetch as jest.Mock;

import { reportArrival, reportOutbound } from '../attribution';

/**
 * A cookie jar jsdom can keep.
 *
 * jsdom drops a `Secure` cookie on an http page, and the id is stored with
 * one - so the jar is stood in here, and the persistence of the id is
 * tested on the jar rather than on the rules of the browser.
 */
let cookieJar = '';

function installCookieJar(initial = ''): void {
  cookieJar = initial;
  Object.defineProperty(document, 'cookie', {
    get: () => cookieJar,
    set: (value: string) => {
      cookieJar = value;
    },
    configurable: true,
  });
}

beforeEach(() => {
  jest.clearAllMocks();
  mockFetch.mockReset();
  mockFetch.mockResolvedValue({ ok: true } as Response);
  installCookieJar();
  window.history.pushState({}, '', '/');
});

describe('the arrival and the visitor id', () => {
  it('sends the id the cookie holds', async () => {
    installCookieJar('visitor_id=11111111-1111-4111-8111-111111111111');
    window.history.pushState({}, '', '/pl/properties?from=hero');

    await reportArrival();

    const body = JSON.parse(mockFetch.mock.calls[0][1].body);
    expect(body.visitor_id).toBe('11111111-1111-4111-8111-111111111111');
  });

  it('keeps the rest of the arrival row', async () => {
    installCookieJar('visitor_id=v-1');
    window.history.pushState({}, '', '/pl/properties?from=hero');

    await reportArrival();

    const body = JSON.parse(mockFetch.mock.calls[0][1].body);
    expect(body.interaction_type).toBe('navigation');
    expect(body.metadata).toEqual({ slot: 'hero' });
    expect(body.locale).toBe('pl');
  });

  it('creates an id when the browser has none', async () => {
    window.history.pushState({}, '', '/pl/properties?from=hero');

    await reportArrival();

    const body = JSON.parse(mockFetch.mock.calls[0][1].body);
    expect(body.visitor_id).toMatch(
      /^[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$/
    );
  });
});

describe('the outbound click and the visitor id', () => {
  it('sends the id the cookie holds', async () => {
    installCookieJar('visitor_id=22222222-2222-4222-8222-222222222222');
    window.history.pushState({}, '', '/pl/landing');

    await reportOutbound('https://studio.example', 'hero', 'spring');

    const body = JSON.parse(mockFetch.mock.calls[0][1].body);
    expect(body.visitor_id).toBe('22222222-2222-4222-8222-222222222222');
    expect(body.target).toBe('https://studio.example');
  });
});

describe('the two rows and one visitor', () => {
  it('carries the same id in the arrival and in the outbound click', async () => {
    installCookieJar('visitor_id=33333333-3333-4333-8333-333333333333');
    window.history.pushState({}, '', '/pl/properties?from=hero');

    await reportArrival();
    await reportOutbound('https://studio.example', 'hero');

    const arrival = JSON.parse(mockFetch.mock.calls[0][1].body);
    const outbound = JSON.parse(mockFetch.mock.calls[1][1].body);
    expect(arrival.visitor_id).toBe('33333333-3333-4333-8333-333333333333');
    expect(outbound.visitor_id).toBe(arrival.visitor_id);
  });

  it('generates the id once and keeps it for the next row', async () => {
    window.history.pushState({}, '', '/pl/properties?from=hero');

    await reportArrival();
    await reportOutbound('https://studio.example', 'hero');

    const arrival = JSON.parse(mockFetch.mock.calls[0][1].body);
    const outbound = JSON.parse(mockFetch.mock.calls[1][1].body);
    expect(arrival.visitor_id).toBeTruthy();
    expect(outbound.visitor_id).toBe(arrival.visitor_id);
  });
});
