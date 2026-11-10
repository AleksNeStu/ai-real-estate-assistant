'use client';

import { useTranslations } from 'next-intl';

import { Link, usePathname } from '@/i18n/navigation';
import { cn } from '@/lib/utils';

/**
 * The four tabs of the admin screen.
 *
 * The admin is one screen with four views, so the tabs belong to the layout
 * and not to the pages: the visitor sees where they are and what else is
 * there, and the tab they are on is the one that is underlined.
 */

/** The tabs, in the order the prototype puts them in. */
export const ADMIN_TABS = [
  { slug: 'bulk-jobs', labelKey: 'tabs.bulkJobs' },
  { slug: 'connectors', labelKey: 'tabs.connectors' },
  { slug: 'data-sources', labelKey: 'tabs.dataSources' },
  { slug: 'monitoring', labelKey: 'tabs.monitoring' },
] as const;

export function AdminTabs({ className }: { className?: string }) {
  const t = useTranslations('pages.admin.shell');
  const pathname = usePathname() || '';

  return (
    <nav
      aria-label={t('title')}
      className={cn('flex gap-6 overflow-x-auto border-b border-border', className)}
    >
      {ADMIN_TABS.map((tab) => {
        const href = `/admin/${tab.slug}`;
        const active = pathname === href || pathname.startsWith(`${href}/`);
        return (
          <Link
            key={tab.slug}
            href={href}
            aria-current={active ? 'page' : undefined}
            className={cn(
              'shrink-0 border-b-2 pb-2.5 pt-2 text-app font-medium transition-colors',
              active
                ? 'border-foreground text-foreground'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            )}
          >
            {t(tab.labelKey)}
          </Link>
        );
      })}
    </nav>
  );
}
