/**
 * The buyer memory API: what the platform remembers about the signed-in buyer,
 * and the erasure of it.
 *
 * The two calls are the account endpoint the legal pages name
 * (`/api/v1/me/buyer-memory`), and the buyer's id comes from the session the
 * request carries. Nothing in the URL, the query or the body can widen that
 * scope, so a call here can only ever reach the caller's own facts.
 *
 * The endpoint asks for a REAL token and not the demo bypass: a memory is
 * personal, so a shared synthetic demo user must not be listable or erasable
 * by whoever walks in. An anonymous request is a 401 - the surface treats that
 * as "the memory belongs to a signed-in account", not as a failure.
 */

import { getApiUrl, buildHeaders, safeFetch, handleResponse } from './client';

/** One stored fact, as the data subject sees it. */
export interface BuyerMemoryFact {
  id: string;
  /** What the fact is: a budget, a ruled-out area, a liked listing, ... */
  kind: string;
  /** The fact in the buyer's own words. */
  content: string;
  /** The listing the fact refers to, when it refers to one. */
  listing_id: string | null;
  confidence: number;
  source: string;
  created_at: string;
  expires_at: string | null;
}

/** Everything the platform holds about the caller. */
export interface BuyerMemoryListResponse {
  facts: BuyerMemoryFact[];
  count: number;
}

/** What the erasure removed. */
export interface BuyerMemoryDeleteResponse {
  deleted: number;
}

/**
 * Read the buyer's stored facts.
 */
export async function getBuyerMemory(): Promise<BuyerMemoryListResponse> {
  const response = await safeFetch(`${getApiUrl()}/me/buyer-memory`, {
    method: 'GET',
    headers: buildHeaders(),
    credentials: 'include',
  });
  return handleResponse<BuyerMemoryListResponse>(response);
}

/**
 * Erase the buyer's memory.
 *
 * The request carries no target: the buyer is the authenticated user, and the
 * whole memory goes.
 */
export async function deleteBuyerMemory(): Promise<BuyerMemoryDeleteResponse> {
  const response = await safeFetch(`${getApiUrl()}/me/buyer-memory`, {
    method: 'DELETE',
    headers: buildHeaders(),
    credentials: 'include',
  });
  return handleResponse<BuyerMemoryDeleteResponse>(response);
}
