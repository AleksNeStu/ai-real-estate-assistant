import createMiddleware from 'next-intl/middleware';
import { NextResponse, type NextRequest } from 'next/server';
import { routing } from './i18n/routing';

const { locales: routingLocales, defaultLocale } = routing;

/**
 * Next.js Proxy for i18n routing and authentication protection.
 *
 * (Renamed from `middleware` to `proxy` per Next.js 16 — the `middleware`
 *  file convention is deprecated in v16.0.0.)
 *
 * This proxy:
 * 1. Handles locale detection and redirection
 * 2. Protects routes that require authentication
 *
 * Public routes (accessible without authentication):
 * - /{locale}/auth/* - Authentication pages
 * - /api/v1/auth/* - Auth API endpoints
 * - /_next/* - Next.js internals
 * - /static/* - Static files
 * - /favicon.ico - Favicon
 *
 * Protected routes (require authentication):
 * - All other routes under /{locale}/*
 */

// Create the next-intl middleware
const intlMiddleware = createMiddleware(routing);

export async function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Handle API routes separately (no i18n)
  if (pathname.startsWith('/api/')) {
    return NextResponse.next();
  }

  // Handle static files and Next.js internals
  if (
    pathname.startsWith('/_next/') ||
    pathname.startsWith('/static/') ||
    pathname === '/favicon.ico'
  ) {
    return NextResponse.next();
  }

  // First, handle i18n routing
  const intlResponse = intlMiddleware(request);

  // Extract locale from pathname or use default
  const pathSegments = pathname.split('/').filter(Boolean);
  const localeFromPath = pathSegments[0];
  const hasLocalePrefix = routingLocales.includes(
    localeFromPath as (typeof routingLocales)[number]
  );
  const currentLocale = hasLocalePrefix ? localeFromPath : defaultLocale;

  // Get the path without locale prefix for route checking
  const pathWithoutLocale = hasLocalePrefix ? '/' + pathSegments.slice(1).join('/') : pathname;

  // Check if this is a public route (auth pages + demo-accessible pages)
  const isAuthRoute = pathWithoutLocale.startsWith('/auth/') || pathWithoutLocale === '/auth';

  // Routes accessible without authentication (demo mode)
  const demoRoutes = [
    '/',
    '/search',
    '/city-overview',
    '/knowledge',
    '/analytics',
    '/market-trends',
    '/cma',
    '/tools',
    '/chat',
    '/agents',
  ];
  const isDemoRoute =
    pathWithoutLocale === '/' ||
    demoRoutes.some(
      (r) => r !== '/' && (pathWithoutLocale === r || pathWithoutLocale.startsWith(r + '/'))
    );

  if (isAuthRoute || isDemoRoute) {
    return intlResponse;
  }

  // If the intl middleware returned a redirect (for locale handling), return it
  if (intlResponse.status === 307 || intlResponse.status === 308) {
    // But still check auth for the redirect destination
    const location = intlResponse.headers.get('location');
    if (location) {
      const redirectUrl = new URL(location);
      const redirectPath = redirectUrl.pathname;

      // Extract locale from redirect path
      const redirectSegments = redirectPath.split('/').filter(Boolean);
      const redirectLocale = redirectSegments[0];
      const redirectPathWithoutLocale = routingLocales.includes(
        redirectLocale as (typeof routingLocales)[number]
      )
        ? '/' + redirectSegments.slice(1).join('/')
        : redirectPath;

      // Check if redirecting to auth route
      if (redirectPathWithoutLocale.startsWith('/auth/') || redirectPathWithoutLocale === '/auth') {
        return intlResponse;
      }
    }
    // For non-auth redirects, continue with auth check
  }

  // Allow CI Lighthouse audits to bypass auth
  if (process.env.LHCI_AUTH_BYPASS === 'true') {
    return intlResponse;
  }

  // Demo mode: allow all routes without authentication
  if (process.env.NEXT_PUBLIC_DEMO_MODE === 'true') {
    return intlResponse;
  }

  // Check for access_token cookie (set by backend auth)
  const accessToken = request.cookies.get('access_token')?.value;

  if (!accessToken) {
    // No access token found, redirect to login with locale
    const loginUrl = new URL(`/${currentLocale}/auth/login`, request.url);
    loginUrl.searchParams.set('redirect', pathname);
    return NextResponse.redirect(loginUrl);
  }

  // Token exists, return the intl response (or continue)
  return intlResponse;
}

/**
 * Configure which routes the proxy should run on.
 *
 * Matches all request paths except:
 * - api routes (handled by backend)
 * - _next/static (static files)
 * - _next/image (image optimization files)
 * - favicon.ico (favicon file)
 * - static files
 */
export const config = {
  matcher: [
    /*
     * Match all request paths except:
     * - api routes that don't need proxy (handled by backend)
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     * - static files
     */
    '/((?!api/|_next/static|_next/image|favicon.ico|static|.*\\..*).*)',
  ],
};
