import { MetadataRoute } from 'next';
import { routing } from '@/i18n/routing';
import { absoluteUrl } from '@/lib/site';

// Public, indexable routes. Private areas (favorites, saved-searches,
// settings, auth, admin) are excluded — robots.txt disallows them.
const PUBLIC_PATHS = [
  '', // homepage
  '/search',
  '/chat',
  '/market-trends',
  '/city-overview',
  '/agents',
  '/tools',
  '/knowledge',
  '/valuation',
  '/showcase',
  '/cma',
  '/documents',
  '/analytics',
  '/agent-analytics',
  '/leads',
  '/usage',
];

export default function sitemap(): MetadataRoute.Sitemap {
  const entries: MetadataRoute.Sitemap = [];

  for (const locale of routing.locales) {
    for (const path of PUBLIC_PATHS) {
      entries.push({
        url: absoluteUrl(`/${locale}${path}`),
        changeFrequency: path === '' ? 'daily' : 'weekly',
        priority: path === '' ? 1.0 : path === '/search' ? 0.9 : 0.7,
      });
    }
  }

  return entries;
}
