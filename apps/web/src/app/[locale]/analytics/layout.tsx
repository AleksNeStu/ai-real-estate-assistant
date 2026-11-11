import type { Metadata } from 'next';
import type { ReactNode } from 'react';

import { routeMetadata } from '@/lib/metadata';

/**
 * The metadata of /<locale>/analytics.
 *
 * The page itself is a client component, so it cannot export metadata - this
 * server layout is where the route declares what it is. Without it every
 * public route inherited the layout's title and description, and fourteen
 * routes claimed to be the same page.
 */
export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}): Promise<Metadata> {
  const { locale } = await params;
  return routeMetadata(locale, '/analytics', 'analytics', 'pages');
}

export default function AnalyticsLayout({ children }: { children: ReactNode }) {
  return children;
}
