'use client';

import type { ReactNode } from 'react';
import { useTranslations } from 'next-intl';

import { AdminTabs } from '@/components/admin/admin-tabs';
import { AccountGate } from '@/components/shell/gate';
import { PageHeader } from '@/components/ui/page-header';

/**
 * The shell of the admin screen.
 *
 * The admin is one screen with four views, so the heading and the four tabs
 * live in the layout and the pages carry only their own panel. A visitor
 * who lands on one tab sees where the other three are.
 */
export default function AdminLayout({ children }: { children: ReactNode }) {
  const t = useTranslations('pages.admin.shell');

  return (
    <AccountGate route="admin">
      <div className="flex flex-col px-6 pt-6">
        <PageHeader title={t('title')} description={t('description')} />
        <AdminTabs className="mt-5" />
      </div>
      <main className="flex flex-col gap-4 px-6 pb-16 pt-5">{children}</main>
    </AccountGate>
  );
}
