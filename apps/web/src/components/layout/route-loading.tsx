'use client';

import { useTranslations } from 'next-intl';

/**
 * The route-level loading state.
 *
 * Every `loading.tsx` in the `[locale]` segment rendered the same hard-coded
 * English "Loading..." — a user on the Polish page saw English while the
 * route was still resolving. The label now comes from the catalogue.
 */
export function RouteLoading() {
  const t = useTranslations('common');

  return (
    <div className="flex items-center justify-center min-h-[60vh]">
      <div className="flex flex-col items-center gap-4">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
        <p className="text-sm text-muted-foreground">{t('loading')}</p>
      </div>
    </div>
  );
}

export default RouteLoading;
