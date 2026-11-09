'use client';

import { useTranslations } from 'next-intl';

import { PageHeader } from '@/components/ui/page-header';
import { MonoAnnotation } from '@/components/ui/mono-annotation';
import { AnalyticsConsole } from '@/components/analytics/analytics-console';

/**
 * The tools of the assistant.
 *
 * Five calculators, one screen: the prototype puts them behind a row of
 * tabs, and the console draws that row. Each tool is the one the assistant
 * calls in the chat - the route does not rebuild them, it puts them in one
 * place and lets the visitor pick.
 */
export default function AnalyticsPage() {
  const t = useTranslations('pages.analytics');

  return (
    <div className="flex min-h-[calc(100vh-56px)] flex-col">
      <div className="border-b border-border px-6 pb-5 pt-6">
        <PageHeader
          title={t('title')}
          description={t('description')}
          actions={<MonoAnnotation>{t('note')}</MonoAnnotation>}
        />
      </div>

      <div className="flex-1 px-6 py-6">
        <AnalyticsConsole />
      </div>
    </div>
  );
}
