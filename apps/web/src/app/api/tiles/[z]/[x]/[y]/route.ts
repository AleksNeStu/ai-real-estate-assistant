import { NextRequest } from 'next/server';

/**
 * The map tiles, served from our own origin.
 *
 * WHY THIS ROUTE EXISTS
 *
 * The maps of the application are Leaflet maps over the OpenStreetMap raster
 * tiles. The browser used to fetch them straight from `tile.openstreetmap.org`
 * - and that host answers a share of the requests with 408 (Request Timeout),
 * which leaves the visitor with a grey rectangle: the markers float, the
 * streets never arrive. The demo's own node reaches the same tiles in 80 ms,
 * so the tiles are available - it is the direct browser-to-CDN path that
 * breaks, and it breaks differently from one network to the next.
 *
 * The route takes the hop away from the visitor: the browser asks THIS
 * origin for a tile, the server asks the CDN once and keeps the answer.
 * Three things follow: the visitor's network no longer decides whether the
 * map renders, the public tile servers see one request per tile instead of
 * one per visitor, and the tile is served from the same origin - no
 * third-party connection for a visitor to have to allow.
 *
 * WHAT IT MUST NOT BECOME
 *
 * A tile proxy is not a free CDN. It holds the tiles in the memory of the
 * web container, so the cache is capped and the oldest tiles leave first.
 * The user agent identifies the application, as the OpenStreetMap tile usage
 * policy asks for. When the traffic outgrows a demo, the answer is a
 * commercial tile provider (Mapbox, MapTiler) and a single constant here
 * changes - not a rewrite of the three maps.
 *
 * The attribution the maps carry stays: the tiles are OpenStreetMap's, and
 * the licence asks for the credit.
 */

export const runtime = 'nodejs';

/** The CDN mirrors, tried in turn. */
const TILE_HOSTS = ['a', 'b', 'c'] as const;

/** The tile server this proxy asks. One constant decides the provider. */
const UPSTREAM_TEMPLATE = 'https://{host}.tile.openstreetmap.org/{z}/{x}/{y}.png';

/**
 * The identification the tile usage policy asks for: the application's own
 * name and its public address, so an operator of the tile servers can reach
 * whoever runs this.
 */
const UPSTREAM_USER_AGENT = 'AI-Real-Estate-Assistant/5.6 (+https://realty.kittray.com)';

/** How long the upstream may take before the tile counts as unavailable. */
const UPSTREAM_TIMEOUT_MS = 8000;

/** How many tiles the container keeps in memory. */
const MAX_CACHE_ENTRIES = 1200;

/**
 * A one-pixel transparent PNG. It is what a failed tile answers with, so a
 * tile that cannot be fetched leaves the map legible (the markers, the
 * shapes) instead of showing the browser's broken-image placeholder.
 */
const FALLBACK_TILE = Buffer.from(
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAADiVViLAAAAC0lEQVR4nGNgAAIAAAUAAccf5fkAAAAASUVORBevkxg=',
  'base64'
);

type CachedTile = {
  body: Buffer;
  contentType: string;
};

/** The tiles in memory. The insertion order is the age order. */
const tileCache = new Map<string, CachedTile>();

/** The mirror that served last, so the load is spread over the three. */
let preferredHostIndex = 0;

function cacheKey(z: number, x: number, y: number): string {
  return `${z}/${x}/${y}`;
}

/** Read a tile from the cache and mark it as the most recently used. */
function readCache(key: string): CachedTile | null {
  const hit = tileCache.get(key);
  if (!hit) return null;
  tileCache.delete(key);
  tileCache.set(key, hit);
  return hit;
}

/** Keep a tile, and let the oldest ones go when the cache is full. */
function writeCache(key: string, tile: CachedTile): void {
  tileCache.set(key, tile);
  while (tileCache.size > MAX_CACHE_ENTRIES) {
    const oldest = tileCache.keys().next();
    if (oldest.done) break;
    tileCache.delete(oldest.value);
  }
}

/** A tile coordinate is three integers inside their own ranges. */
function parseTileCoordinate(
  raw: string,
  min: number,
  max: number
): number | null {
  if (!/^\d{1,7}$/.test(raw)) return null;
  const value = Number.parseInt(raw, 10);
  if (!Number.isInteger(value) || value < min || value > max) return null;
  return value;
}

type TileContext = {
  params: Promise<{
    z: string;
    x: string;
    y: string;
  }>;
};

/**
 * The deadline of one upstream request.
 *
 * `AbortSignal.timeout` is the modern way to say it, but it is not in every
 * runtime the route can end up in (a test environment is one of them), so the
 * signal is only attached when the runtime knows how to build one.
 */
function timeoutSignal(): AbortSignal | undefined {
  if (typeof AbortSignal.timeout !== 'function') return undefined;
  return AbortSignal.timeout(UPSTREAM_TIMEOUT_MS);
}

async function fetchTile(z: number, x: number, y: number): Promise<CachedTile | null> {
  for (let attempt = 0; attempt < TILE_HOSTS.length; attempt++) {
    const host = TILE_HOSTS[(preferredHostIndex + attempt) % TILE_HOSTS.length];
    const url = UPSTREAM_TEMPLATE.replace('{host}', host)
      .replace('{z}', String(z))
      .replace('{x}', String(x))
      .replace('{y}', String(y));

    try {
      const response = await fetch(url, {
        headers: {
          'User-Agent': UPSTREAM_USER_AGENT,
          Referer: 'https://realty.kittray.com/',
          Accept: 'image/png,image/*;q=0.8',
        },
        signal: timeoutSignal(),
      });

      if (!response.ok) continue;

      const body = Buffer.from(await response.arrayBuffer());
      preferredHostIndex = (preferredHostIndex + attempt) % TILE_HOSTS.length;
      return { body, contentType: response.headers.get('content-type') || 'image/png' };
    } catch {
      // This mirror did not answer in time - try the next one.
    }
  }
  return null;
}

export async function GET(_request: NextRequest, context: TileContext): Promise<Response> {
  const { z: rawZ, x: rawX, y: rawY } = await context.params;

  const z = parseTileCoordinate(rawZ, 0, 19);
  if (z === null) {
    return new Response('Bad zoom level', { status: 400 });
  }
  const limit = 2 ** z;
  const x = parseTileCoordinate(rawX, 0, limit - 1);
  const y = parseTileCoordinate(rawY, 0, limit - 1);
  if (x === null || y === null) {
    return new Response('Bad tile coordinate', { status: 400 });
  }

  const key = cacheKey(z, x, y);
  const cached = readCache(key);
  if (cached) {
    return new Response(new Uint8Array(cached.body), {
      status: 200,
      headers: {
        'Content-Type': cached.contentType,
        'Cache-Control': 'public, max-age=604800, immutable',
        'X-Tile-Cache': 'HIT',
      },
    });
  }

  const tile = await fetchTile(z, x, y);
  if (!tile) {
    // The upstream is unavailable. Answer with the transparent tile so the
    // map stays legible, and say so in the header - the browser gets a tile
    // it can draw, and the operator can see that the upstream is the problem.
    return new Response(new Uint8Array(FALLBACK_TILE), {
      status: 200,
      headers: {
        'Content-Type': 'image/png',
        'Cache-Control': 'no-store',
        'X-Tile-Cache': 'FALLBACK',
      },
    });
  }

  writeCache(key, tile);
  return new Response(new Uint8Array(tile.body), {
    status: 200,
    headers: {
      'Content-Type': tile.contentType,
      'Cache-Control': 'public, max-age=604800, immutable',
      'X-Tile-Cache': 'MISS',
    },
  });
}
