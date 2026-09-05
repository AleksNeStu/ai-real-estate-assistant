/**
 * Canonical site URL for the public Render deployment.
 * Falls back to the Render subdomain when NEXT_PUBLIC_SITE_URL is not set.
 */
export const SITE_URL: URL = new URL(
  process.env.NEXT_PUBLIC_SITE_URL ?? 'https://realestate-web-dz1y.onrender.com'
);

/**
 * Build an absolute URL from a path, normalising leading-slash handling.
 * Accepts paths with or without a leading slash.
 */
export function absoluteUrl(path: string): string {
  const normalised = path.startsWith('/') ? path : `/${path}`;
  return `${SITE_URL.origin}${normalised}`;
}
