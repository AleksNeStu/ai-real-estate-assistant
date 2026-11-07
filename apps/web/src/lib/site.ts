/**
 * Canonical site URL for the public deployment.
 *
 * The address arrives as a build argument (Next inlines every NEXT_PUBLIC_*),
 * so it can be missing OR empty - a build without the argument sets the
 * variable to an empty string, and `new URL('')` throws. Both cases fall back
 * to the public site origin.
 */
const CONFIGURED_SITE_URL = process.env.NEXT_PUBLIC_SITE_URL?.trim();

export const SITE_URL: URL = new URL(
  CONFIGURED_SITE_URL || 'https://realty.kittray.com'
);

/**
 * Build an absolute URL from a path, normalising leading-slash handling.
 * Accepts paths with or without a leading slash.
 */
export function absoluteUrl(path: string): string {
  const normalised = path.startsWith('/') ? path : `/${path}`;
  return `${SITE_URL.origin}${normalised}`;
}
