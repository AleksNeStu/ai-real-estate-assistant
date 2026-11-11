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
