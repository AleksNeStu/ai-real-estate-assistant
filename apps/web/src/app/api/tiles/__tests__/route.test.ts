import { describe, it, expect, beforeEach, afterEach, jest } from '@jest/globals';

import { GET } from '../[z]/[x]/[y]/route';

/**
 * The tile proxy.
 *
 * The map on the live site was grey because the browser asked the tile CDN
 * directly and the answer never came. The proxy is the fix, so the test
 * holds the three things it promises: a tile arrives as a PNG, a coordinate
 * outside its zoom level is refused, and an upstream that does not answer
 * leaves the map with a transparent tile instead of an error.
 */

type TileContext = {
  params: Promise<{ z: string; x: string; y: string }>;
};

function context(z: string, x: string, y: string): TileContext {
  return { params: Promise.resolve({ z, x, y }) };
}

/** A tile as the upstream answers it. */
function upstreamTile(bytes: number[] = [137, 80, 78, 71]) {
  return {
    ok: true,
    status: 200,
    headers: { get: (name: string) => (name.toLowerCase() === 'content-type' ? 'image/png' : null) },
    arrayBuffer: async () => new Uint8Array(bytes).buffer,
  };
}

describe('the tile proxy', () => {
  beforeEach(() => {
    jest.resetAllMocks();
    (global.fetch as unknown as jest.Mock) = jest.fn();
  });

  afterEach(() => {
    (global.fetch as unknown as jest.Mock) = jest.fn(() =>
      Promise.resolve(new Response(JSON.stringify({ message: 'success' }), { status: 200 }))
    );
  });

  it('answers a tile with the image the upstream sent', async () => {
    (global.fetch as unknown as jest.Mock).mockResolvedValueOnce(upstreamTile());

    const response = await GET({} as never, context('12', '2278', '1406'));

    expect(response.status).toBe(200);
    expect(response.headers.get('Content-Type')).toBe('image/png');
    expect(response.headers.get('X-Tile-Cache')).toBe('MISS');
  });

  it('refuses a coordinate that the zoom level does not have', async () => {
    const response = await GET({} as never, context('2', '9', '9'));

    expect(response.status).toBe(400);
    expect(global.fetch).not.toHaveBeenCalled();
  });

  it('refuses a zoom level the map never asks for', async () => {
    const response = await GET({} as never, context('42', '0', '0'));

    expect(response.status).toBe(400);
  });

  it('answers with a transparent tile when no mirror answers', async () => {
    (global.fetch as unknown as jest.Mock).mockRejectedValue(new Error('no route to host'));

    const response = await GET({} as never, context('9', '100', '200'));

    expect(response.status).toBe(200);
    expect(response.headers.get('Content-Type')).toBe('image/png');
    expect(response.headers.get('X-Tile-Cache')).toBe('FALLBACK');
  });

  it('serves the second request for a tile from the cache', async () => {
    (global.fetch as unknown as jest.Mock).mockResolvedValueOnce(upstreamTile());

    await GET({} as never, context('7', '70', '80'));
    const cached = await GET({} as never, context('7', '70', '80'));

    expect(cached.headers.get('X-Tile-Cache')).toBe('HIT');
    // One upstream request for two asks.
    expect(global.fetch).toHaveBeenCalledTimes(1);
  });
});
