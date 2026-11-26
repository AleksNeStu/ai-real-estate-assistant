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
      className={cn('flex flex-wrap gap-x-6 border-b border-border', className)}
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
              // The same tab as the other bars of the product: the rule of
              // the active tab sits on the rule of the bar, and the row
              // wraps instead of scrolling - one behaviour at every width.
              '-mb-px shrink-0 whitespace-nowrap border-b-2 py-2.5 text-[14px] font-medium transition-colors',
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
