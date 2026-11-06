/**
 * Canonical site URL for the public deployment.
 * Falls back to the public site origin when NEXT_PUBLIC_SITE_URL is not set.
 */
export const SITE_URL: URL = new URL(
  process.env.NEXT_PUBLIC_SITE_URL ?? 'https://realestate.nestlab.tech'
);

/**
 * Build an absolute URL from a path, normalising leading-slash handling.
 * Accepts paths with or without a leading slash.
 */
export function absoluteUrl(path: string): string {
  const normalised = path.startsWith('/') ? path : `/${path}`;
  return `${SITE_URL.origin}${normalised}`;
}
