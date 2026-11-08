'use client';

import { useTranslations } from 'next-intl';

export function SkipNav() {
  const t = useTranslations('common');

  return (
    <a
      href="#main-content"
      className="sr-only focus:not-sr-only focus:fixed focus:top-4 focus:left-4 focus:z-50 focus:rounded-md focus:bg-primary focus:px-4 focus:py-2 focus:text-primary-foreground focus:outline-none focus:outline-2 focus:outline-ring/50"
    >
      {t('skipToContent')}
    </a>
  );
}
