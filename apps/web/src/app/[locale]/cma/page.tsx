'use client';

import { useTranslations } from 'next-intl';

import { CMAWizard } from '@/components/cma/cma-wizard';
import { PageHeader } from '@/components/ui/page-header';

export default function CMAPage() {
  const t = useTranslations('pages.cma');

  return (
    <div className="container mx-auto max-w-5xl px-4 py-8">
      <PageHeader className="mb-6" title={t('title')} description={t('description')} />
      <CMAWizard />
    </div>
  );
}
