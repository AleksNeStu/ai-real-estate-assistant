'use client';

import { useLocale, useTranslations } from 'next-intl';

import { MonoAnnotation } from '@/components/ui/mono-annotation';
import { formatPrice } from '@/lib/format';
import type { MarketIndicators } from '@/lib/types';

/**
 * The districts that moved.
 *
 * Two lists side by side - the dearest and the cheapest - and each one is a
 * ledger: the district on the left, how much it asks on the right, and how
 * many listings stand behind that number underneath.
 */

interface District {
  name: string;
  avg_price: number;
  count: number;
}

export interface DistrictsLedgerProps {
  indicators: MarketIndicators;
  /**
   * The currency the listings of this market are priced in.
   *
   * The indicators API does not carry one, so the price is written as a bare
   * number when it is unknown: a dollar sign in front of a Polish listing
   * would be a guess.
   */
  currency?: string;
  className?: string;
}

export function DistrictsLedger({ indicators, currency, className }: DistrictsLedgerProps) {
  const t = useTranslations('pages.marketTrends');
  const tCma = useTranslations('cma.preview');
  const locale = useLocale();

  const hottest = indicators.hottest_districts ?? [];
  const coldest = indicators.coldest_districts ?? [];

  if (hottest.length === 0 && coldest.length === 0) return null;

  const renderList = (
    title: string,
    hint: string,
    districts: District[],
    tone: 'success' | 'neutral'
  ) => (
    <section className="rounded-lg border border-border">
      <header className="border-b border-border px-4 py-3">
        <h2
          className={[
            'text-[15px] font-semibold',
            tone === 'success' ? 'text-success' : 'text-foreground',
          ].join(' ')}
        >
          {title}
        </h2>
        <p className="mt-0.5 text-[12px] leading-4 text-muted-foreground">{hint}</p>
      </header>
      <div>
        {districts.map((district, index) => (
          <div
            key={`${district.name}-${index}`}
            className="flex items-baseline justify-between gap-4 border-b border-border px-4 py-[10px]"
          >
            <span className="min-w-0 truncate text-[14px] leading-5 text-foreground">
              {district.name}
            </span>
            <span className="flex shrink-0 items-baseline gap-3">
              <MonoAnnotation>{tCma('listings', { count: district.count })}</MonoAnnotation>
              <span className="font-mono text-[14px] font-semibold text-foreground">
                {currency
                  ? formatPrice(district.avg_price, currency, locale)
                  : district.avg_price.toLocaleString()}
              </span>
            </span>
          </div>
        ))}
      </div>
    </section>
  );

  return (
    <div className={['grid gap-4 sm:grid-cols-2', className].filter(Boolean).join(' ')}>
      {hottest.length > 0
        ? renderList(t('areas.hottest'), t('areas.hottestHint'), hottest, 'success')
        : null}
      {coldest.length > 0
        ? renderList(t('areas.affordable'), t('areas.affordableHint'), coldest, 'neutral')
        : null}
    </div>
  );
}
