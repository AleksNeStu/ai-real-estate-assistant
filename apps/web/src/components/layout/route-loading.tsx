'use client';

import { useTranslations } from 'next-intl';

/**
 * The route-level loading state.
 *
 * A spinner says "something is happening"; a skeleton says what is about to
 * arrive. The prototype draws the rows of a ledger and pulses them, so the
 * page that comes out of the loading state has the shape the visitor was
 * already shown. The label comes from the catalogue, so a Polish visitor
 * never reads an English "Loading...".
 */
export function RouteLoading() {
  const t = useTranslations('designStates');

  return (
    <div
      role="status"
      aria-live="polite"
      aria-busy="true"
      className="mx-auto w-full max-w-[1248px] px-6 py-14"
    >
      <span className="sr-only">{t('loading.title')}</span>
      <div className="flex flex-col gap-4" aria-hidden="true">
        {[0, 1, 2, 3, 4].map((row) => (
          <div key={row} className="flex items-center gap-4">
            <div className="h-4 w-4 animate-pulse rounded-[4px] bg-muted" />
            <div
              className="h-4 animate-pulse rounded-[4px] bg-muted"
              style={{ width: `${100 - row * 11}%` }}
            />
          </div>
        ))}
      </div>
    </div>
  );
}

export default RouteLoading;
