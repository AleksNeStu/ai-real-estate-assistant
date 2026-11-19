/**
 * Tests for buyer-memory.ts — reading the buyer's stored facts, erasing them,
 * and the error paths.
 */

import { jest } from '@jest/globals';

import { ApiError } from '../client';

// Mock fetch globally
(globalThis as unknown as { fetch: jest.Mock }).fetch = jest.fn();
const mockFetch = globalThis.fetch as jest.Mock;

// Helper to create a successful JSON response
function okResponse<T>(data: T) {
  return {
    ok: true,
    json: async () => data,
    status: 200,
    headers: { get: () => null },
  };
}

// Helper to create an error response
function errorResponse(status: number, detail: string) {
  return {
    ok: false,
    status,
    statusText: 'Error',
    text: async () => JSON.stringify({ detail }),
    json: async () => ({ detail }),
    headers: { get: () => null },
  };
}

// We must import after fetch is mocked
import { deleteBuyerMemory, getBuyerMemory } from '../buyer-memory';

const FACT = {
  id: 'fact-1',
  kind: 'budget',
  content: 'up to 500,000 PLN',
  listing_id: null,
  confidence: 0.9,
  source: 'chat',
  created_at: '2026-11-01T10:00:00Z',
  expires_at: '2027-11-01T10:00:00Z',
};

beforeEach(() => {
  jest.clearAllMocks();
});

describe('getBuyerMemory', () => {
  it('reads the account endpoint and returns the facts', async () => {
    mockFetch.mockResolvedValueOnce(okResponse({ facts: [FACT], count: 1 }));

    const result = await getBuyerMemory();

    expect(result.count).toBe(1);
    expect(result.facts).toHaveLength(1);
    expect(result.facts[0].content).toBe('up to 500,000 PLN');

    const [url, init] = mockFetch.mock.calls[0] as [string, RequestInit];
    expect(url).toContain('/me/buyer-memory');
    expect(init.method).toBe('GET');
  });

  it('carries the session, so the answer is the caller\'s own memory', async () => {
    mockFetch.mockResolvedValueOnce(okResponse({ facts: [], count: 0 }));

    await getBuyerMemory();

    const [, init] = mockFetch.mock.calls[0] as [string, RequestInit];
    expect(init.credentials).toBe('include');
  });

  it('raises an auth error when the account is not signed in', async () => {
    mockFetch.mockResolvedValueOnce(errorResponse(401, 'Not authenticated'));

    try {
      await getBuyerMemory();
      throw new Error('the call should have failed');
    } catch (err) {
      expect(err).toBeInstanceOf(ApiError);
      expect((err as ApiError).status).toBe(401);
      expect((err as ApiError).category).toBe('auth');
    }
  });

  it('raises the server error when the read fails', async () => {
    mockFetch.mockResolvedValueOnce(errorResponse(500, 'Internal server error'));

    await expect(getBuyerMemory()).rejects.toBeInstanceOf(ApiError);
  });

  it('raises a network error when the request never leaves', async () => {
    mockFetch.mockRejectedValueOnce(new Error('offline'));

    await expect(getBuyerMemory()).rejects.toBeInstanceOf(ApiError);
  });
});

describe('deleteBuyerMemory', () => {
  it('erases the memory and reports how many facts went', async () => {
    mockFetch.mockResolvedValueOnce(okResponse({ deleted: 3 }));

    const result = await deleteBuyerMemory();

    expect(result.deleted).toBe(3);

    const [url, init] = mockFetch.mock.calls[0] as [string, RequestInit];
    expect(url).toContain('/me/buyer-memory');
    expect(init.method).toBe('DELETE');
    expect(init.credentials).toBe('include');
  });

  it('raises the error when the erasure fails', async () => {
    mockFetch.mockResolvedValueOnce(errorResponse(500, 'Internal server error'));

    await expect(deleteBuyerMemory()).rejects.toBeInstanceOf(ApiError);
  });

  it('raises an auth error when the account is not signed in', async () => {
    mockFetch.mockResolvedValueOnce(errorResponse(401, 'Not authenticated'));

    try {
      await deleteBuyerMemory();
      throw new Error('the call should have failed');
    } catch (err) {
      expect(err).toBeInstanceOf(ApiError);
      expect((err as ApiError).category).toBe('auth');
    }
  });
});
