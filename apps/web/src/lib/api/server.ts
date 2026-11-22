/**
 * The server-side reading of the catalogue.
 *
 * The browser reaches the backend through the Next.js proxy (`/api/v1` on the
 * same origin). A server component has no browser and no same-origin to lean
 * on: it talks to the backend directly, over the deployment's own network -
 * `BACKEND_API_URL` inside the compose network, the public API URL outside
 * it.
 *
 * The property page reads its listing here, on the server, so the page that
 * a crawler receives already carries the listing: its title, its price, its
 * address, its structured data. Before this, the page was a client component
 * that fetched after the fact, and a crawler that did not run the JavaScript
 * saw an empty shell.
 *
 * Every read here is best-effort: a catalogue that cannot be reached must not
 * take the page down with it. The caller decides what to do with a `null`.
 */

import type { Property } from '../types';
import type { ValuationResponse } from './tools';
import type { ValuationSubject } from '../valuation-slug';

/** The backend's API root, for a server-side read. */
export function serverApiUrl(): string {
  const internal = process.env.BACKEND_API_URL?.trim();
  if (internal) return internal.replace(/\/$/, '');
  const publicUrl = process.env.NEXT_PUBLIC_API_URL?.trim();
  if (publicUrl && publicUrl.startsWith('http')) return publicUrl.replace(/\/$/, '');
  return 'http://localhost:8000/api/v1';
}

/**
 * One listing, read on the server.
 *
 * Returns `null` when the listing does not exist or the catalogue cannot be
 * reached - the two cases the page renders differently but neither of which
 * is an error worth a stack trace.
 */
export async function fetchServerProperty(propertyId: string): Promise<Property | null> {
  if (!propertyId) return null;
  try {
    const response = await fetch(
      `${serverApiUrl()}/properties/${encodeURIComponent(propertyId)}`,
      {
        headers: { Accept: 'application/json' },
        // The catalogue of a deployment changes; a page that names one listing
        // may be asked for again long after it was rendered.
        next: { revalidate: 300 },
      },
    );
    if (!response.ok) return null;
    const data = (await response.json()) as Property;
    return data && typeof data === 'object' ? data : null;
  } catch {
    return null;
  }
}

/**
 * The comparables of one listing, read on the server.
 */
export async function fetchServerRelated(
  propertyId: string,
  limit = 3,
): Promise<Property[]> {
  try {
    const response = await fetch(
      `${serverApiUrl()}/properties/${encodeURIComponent(propertyId)}/related?limit=${limit}`,
      { headers: { Accept: 'application/json' }, next: { revalidate: 300 } },
    );
    if (!response.ok) return [];
    const data = (await response.json()) as { properties?: Property[] };
    return Array.isArray(data?.properties) ? data.properties : [];
  } catch {
    return [];
  }
}

/**
 * The key the server-side read carries.
 *
 * The browser never sees it: the proxy injects it on the way in, and the
 * server-side read injects it on the way to the backend. A deployment that
 * has none reads the catalogue's public routes and gets nothing from the
 * tools - which is the same thing the proxy does.
 */
function serverApiKey(): string | undefined {
  const primary = process.env.API_ACCESS_KEY?.trim();
  if (primary) return primary;
  const rotated = process.env.API_ACCESS_KEYS?.split(',')
    .map((value) => value.trim())
    .find((value) => Boolean(value));
  return rotated || undefined;
}

/**
 * One valuation, read on the server.
 *
 * The shareable valuation page renders its answer on the server, so a crawler
 * that does not run the JavaScript receives the number, the sales it rests on
 * and the period they cover - not an empty shell.
 *
 * Returns `null` when the register cannot answer for that place: the
 * endpoint answers 404 when it holds too few sales to price anything, and
 * that is a page without an estimate, not an error.
 *
 * The answer is held for a minute. A page reads it twice - once for its
 * metadata, once for its body - and the register does not move that fast;
 * without the hold the register would be read twice for one page view.
 */
const VALUATION_MEMO_TTL_MS = 60_000;
const VALUATION_MEMO_MAX = 500;
const valuationMemo = new Map<string, { at: number; value: ValuationResponse | null }>();

export async function fetchServerValuation(
  subject: ValuationSubject,
): Promise<ValuationResponse | null> {
  const city = subject.city?.trim();
  if (!city) return null;

  const street = subject.street?.trim();
  const key = serverApiKey();
  const memoKey = [city, street ?? '', subject.area_sqm ?? '', subject.rooms ?? ''].join('|');

  const memoised = valuationMemo.get(memoKey);
  if (memoised && Date.now() - memoised.at < VALUATION_MEMO_TTL_MS) {
    return memoised.value;
  }

  let value: ValuationResponse | null = null;
  try {
    const response = await fetch(`${serverApiUrl()}/tools/valuation`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
        ...(key ? { 'X-API-Key': key } : {}),
      },
      body: JSON.stringify({
        city,
        street: street || undefined,
        area_sqm: subject.area_sqm ?? undefined,
        rooms: subject.rooms ?? undefined,
      }),
      // The register is a moving target, but a page that is asked for again
      // a minute later does not need a different answer.
      cache: 'no-store',
    });
    if (response.ok) {
      const data = (await response.json()) as ValuationResponse;
      value = data && typeof data === 'object' ? data : null;
    }
  } catch {
    value = null;
  }

  valuationMemo.set(memoKey, { at: Date.now(), value });
  // The memo is bounded: a public site can be asked about any address, and
  // an unbounded map is a leak with a long tail.
  if (valuationMemo.size > VALUATION_MEMO_MAX) {
    const oldest = [...valuationMemo.entries()].sort(
      (left, right) => left[1].at - right[1].at,
    );
    for (const [key] of oldest.slice(0, oldest.length - VALUATION_MEMO_MAX + 1)) {
      valuationMemo.delete(key);
    }
  }
  return value;
}
