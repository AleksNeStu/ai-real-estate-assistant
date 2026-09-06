/// <reference lib="webworker" />

// Service Worker for AI Real Estate Assistant PWA
// Provides offline caching, asset pre-caching, and network strategies

const CACHE_NAME = 'realestate-ai-v1';
const STATIC_CACHE = 'static-v1';
const API_CACHE = 'api-v1';
const _OFFLINE_URL = '/offline';

// Static assets to pre-cache on install
const PRECACHE_URLS = [
  '/',
  '/manifest.json',
  '/icon-192x192.svg',
  '/icon-512x512.svg',
  '/icon-maskable.svg',
];

// Cache duration for API responses (5 minutes)
const _API_CACHE_MAX_AGE = 5 * 60 * 1000;
const _API_CACHE_MAX_ENTRIES = 50;

// Install event — pre-cache essential assets (fail soft per-URL so a
// single 404 doesn't break the whole install).
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches
      .open(STATIC_CACHE)
      .then(async (cache) => {
        await Promise.all(
          PRECACHE_URLS.map(async (url) => {
            try {
              const response = await fetch(url, { cache: 'no-cache' });
              if (response.ok) {
                await cache.put(url, response.clone());
              }
            } catch {
              // Network or fetch error for this URL - skip silently so
              // install still completes for the URLs that worked.
            }
          })
        );
      })
      .then(() => {
        return self.skipWaiting();
      })
  );
});

// Activate event — clean up old caches
self.addEventListener('activate', (event) => {
  const allowedCaches = new Set([CACHE_NAME, STATIC_CACHE, API_CACHE]);

  event.waitUntil(
    caches
      .keys()
      .then((cacheNames) => {
        return Promise.all(
          cacheNames.filter((name) => !allowedCaches.has(name)).map((name) => caches.delete(name))
        );
      })
      .then(() => {
        return self.clients.claim();
      })
  );
});

// Fetch event — route requests to appropriate caching strategy
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip non-GET requests
  if (request.method !== 'GET') return;

  // Skip chrome-extension and other non-http(s) requests
  if (!url.protocol.startsWith('http')) return;

  // Route: API requests → Network First
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(networkFirst(request, API_CACHE));
    return;
  }

  // Route: Static assets → Cache First
  if (isStaticAsset(url.pathname)) {
    event.respondWith(cacheFirst(request, STATIC_CACHE));
    return;
  }

  // Route: Navigation requests → Network First with offline fallback
  if (request.mode === 'navigate') {
    event.respondWith(networkFirstWithOfflineFallback(request));
    return;
  }

  // Default: Network First
  event.respondWith(networkFirst(request, CACHE_NAME));
});

/**
 * Cache First strategy — serve from cache, fallback to network
 * Best for static assets that rarely change (fonts, images, JS/CSS bundles)
 */
async function cacheFirst(request, cacheName) {
  const cached = await caches.match(request);
  if (cached) {
    return cached;
  }

  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(cacheName);
      cache.put(request, response.clone());
    }
    return response;
  } catch {
    return new Response('', { status: 408, statusText: 'Request timeout' });
  }
}

/**
 * Network First strategy — try network, fallback to cache
 * Best for API calls where fresh data is preferred
 */
async function networkFirst(request, cacheName) {
  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(cacheName);
      cache.put(request, response.clone());
    }
    return response;
  } catch {
    const cached = await caches.match(request);
    if (cached) {
      return cached;
    }
    return new Response(JSON.stringify({ error: 'Offline' }), {
      status: 503,
      headers: { 'Content-Type': 'application/json' },
    });
  }
}

/**
 * Network First with offline fallback for navigation requests
 */
async function networkFirstWithOfflineFallback(request) {
  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(CACHE_NAME);
      cache.put(request, response.clone());
    }
    return response;
  } catch {
    const cached = await caches.match(request);
    if (cached) {
      return cached;
    }
    // Return cached index page as offline fallback (SPA routing)
    const fallback = await caches.match('/');
    if (fallback) {
      return fallback;
    }
    return new Response('You are offline', {
      status: 503,
      headers: { 'Content-Type': 'text/plain' },
    });
  }
}

/**
 * Check if a request path is a static asset
 */
function isStaticAsset(pathname) {
  return (
    pathname.startsWith('/_next/static/') ||
    pathname.startsWith('/fonts/') ||
    /\.(js|css|woff2?|ttf|eot|svg|png|jpg|jpeg|gif|ico|webp)$/i.test(pathname)
  );
}

// Handle messages from the main thread
self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});
