import type { NextConfig } from 'next';
import { dirname, resolve } from 'path';
import { fileURLToPath } from 'url';
import createNextIntlPlugin from 'next-intl/plugin';
import withPWAInit from '@ducanh2912/next-pwa';
import { withSentryConfig } from '@sentry/nextjs';

const configDir = dirname(fileURLToPath(import.meta.url));
const turbopackRoot = resolve(configDir, '..', '..');

const withNextIntl = createNextIntlPlugin('./src/i18n/request.ts');

// PWA configuration - simplified for v10.2.9
const withPWA = withPWAInit({
  dest: 'public',
  disable: process.env.NODE_ENV === 'development',
  register: true,
});

const nextConfig: NextConfig = {
  output: 'standalone',
  turbopack: {
    root: turbopackRoot,
  },
  images: {
    formats: ['image/avif', 'image/webp'],
    deviceSizes: [640, 828, 1080, 1200, 1920],
  },
  experimental: {
    optimizePackageImports: ['recharts', 'lucide-react', 'date-fns'],
  },
  async headers() {
    const isProduction = process.env.NODE_ENV === 'production';

    // Content Security Policy
    // Development: More permissive for hot reload and inline scripts
    // Production: Strict policy allowing only trusted sources
    const cspDirectives = isProduction
      ? {
          'default-src': ["'self'"],
          'script-src': ["'self'", "'unsafe-inline'"],
          'style-src': ["'self'", "'unsafe-inline'"],
          'img-src': ["'self'", 'data:', 'https:', 'blob:'],
          'font-src': ["'self'", 'data:'],
          'connect-src': [
            "'self'",
            ...(process.env.NEXT_PUBLIC_API_URL?.startsWith('http')
              ? [process.env.NEXT_PUBLIC_API_URL]
              : []),
            // The browser talks to the API on the same origin through the Next
            // proxy (`NEXT_PUBLIC_API_URL=/api/v1`), so `'self'` already covers
            // it. The extra origin is the canonical host, for the case where the
            // API URL is configured as an absolute URL.
            'https://ai-real-estate-demo.devs-scaler.workers.dev',
            // Push notification services
            'https://fcm.googleapis.com',
            'https://updates.push.services.mozilla.com',
            'https://*.push.apple.com',
            // Sentry error tracking
            'https://sentry.io',
            'https://*.ingest.sentry.io',
          ],
          'frame-src': ["'none'"],
          'object-src': ["'none'"],
          'base-uri': ["'self'"],
          'form-action': ["'self'"],
          'frame-ancestors': ["'none'"],
          'upgrade-insecure-requests': [],
        }
      : {
          'default-src': ["'self'"],
          'script-src': ["'self'", "'unsafe-eval'", "'unsafe-inline'"],
          'style-src': ["'self'", "'unsafe-inline'"],
          'img-src': ["'self'", 'data:', 'https:', 'blob:', 'http://localhost:*'],
          'font-src': ["'self'", 'data:'],
          'connect-src': [
            "'self'",
            'http://localhost:*',
            'ws://localhost:*',
            'https://localhost:*',
            // Sentry error tracking (development)
            'https://sentry.io',
            'https://*.ingest.sentry.io',
          ],
          'frame-src': ["'none'"],
          'object-src': ["'none'"],
        };

    const cspHeaderValue = Object.entries(cspDirectives)
      .map(([directive, values]) => `${directive} ${values.join(' ')}`)
      .join('; ');

    return [
      {
        source: '/(.*)',
        headers: [
          {
            key: 'X-Content-Type-Options',
            value: 'nosniff',
          },
          {
            key: 'X-Frame-Options',
            value: 'DENY',
          },
          {
            key: 'X-XSS-Protection',
            value: '1; mode=block',
          },
          {
            key: 'Referrer-Policy',
            value: 'strict-origin-when-cross-origin',
          },
          {
            key: 'Permissions-Policy',
            value:
              'geolocation=(), microphone=(), camera=(), payment=(), usb=(), magnetometer=(), gyroscope=()',
          },
          {
            key: 'Content-Security-Policy',
            value: cspHeaderValue,
          },
          // HSTS only in production when using HTTPS
          ...(isProduction
            ? [
                {
                  key: 'Strict-Transport-Security',
                  value: 'max-age=31536000; includeSubDomains; preload',
                },
              ]
            : []),
        ],
      },
    ];
  },
};

// Sentry configuration wrapper - only wrap when auth token is available
const sentryBuildOptions = {
  silent: true,
  org: process.env.SENTRY_ORG,
  project: process.env.SENTRY_PROJECT,
};

export default process.env.SENTRY_AUTH_TOKEN
  ? withSentryConfig(withPWA(withNextIntl(nextConfig)), sentryBuildOptions)
  : withPWA(withNextIntl(nextConfig));
