'use client';

import { usePathname } from '@/i18n/navigation';

import { SiteFooter } from '@/components/layout/site-footer';

/**
 * The site footer, on every route but the landing.
 *
 * The landing carries its own footer - the one from the prototype, with the
 * three columns and the locale chain - so the site-wide footer would print
 * twice on the public address. One footer per page, never two.
 */
export function AppFooter() {
  const pathname = usePathname() || '/';

  if (pathname === '/') {
    return null;
  }

  return <SiteFooter />;
}
