'use client';

import { useTranslations } from 'next-intl';

import { MonoAnnotation } from '@/components/ui/mono-annotation';
import type { MarketIndicators } from '@/lib/types';

/**
 * The indicators of one market.
 *
 * The indicators are a list of numbers, so they are drawn as a ledger: a
 * label on the left, the number in mono on the right, a hairline between
 * the rows. The panel names the market it is about - the city, or every
 * city when the view is not narrowed to one.
 *
 * Every number is the one the API returned. The panel adds no estimate and
 * no comparison of its own.
 */

export interface MarketIndicatorsPanelProps {
  indicators: MarketIndicators;
  /** The city the view is narrowed to, or null when it covers every city. */
  city: string | null;
  /** The price per m² of the last period of the trends, when there is one. */
  pricePerSqm?: number | null;
  className?: string;
}

export function MarketIndicatorsPanel({
  indicators,
  city,
  pricePerSqm,
  className,
}: MarketIndicatorsPanelProps) {
  const t = useTranslations('pages.marketTrends');

  const change = indicators.avg_price_change_1y;
  const trend = indicators.overall_trend;
  const trendTone =
    trend === 'rising' ? 'success' : trend === 'falling' ? 'destructive' : 'neutral';
  const changeTone =
    change === undefined ? 'neutral' : change > 0 ? 'success' : change < 0 ? 'destructive' : 'neutral';

  const rows: Array<{ label: string; value: string; tone?: 'success' | 'destructive' }> = [
    {
      label: t('stats.overallTrend'),
      value: t(`trend.${trend}`),
      ...(trendTone === 'neutral' ? {} : { tone: trendTone }),
    },
    {
      label: t('stats.change12m'),
      value: change === undefined ? '—' : `${change > 0 ? '+' : ''}${change.toFixed(1)}%`,
      ...(changeTone === 'neutral' ? {} : { tone: changeTone }),
    },
    {
      label: t('stats.totalListings'),
      value: indicators.total_listings.toLocaleString(),
    },
    {
      label: t('stats.new7d'),
      value: indicators.new_listings_7d.toLocaleString(),
    },
    {
      label: t('stats.priceDrops7d'),
      value: indicators.price_drops_7d.toLocaleString(),
    },
    {
      label: t('stats.pricePerSqm'),
      value:
        pricePerSqm === null || pricePerSqm === undefined
          ? '—'
          : Math.round(pricePerSqm).toLocaleString(),
    },
  ];

  return (
    <section
      className={['rounded-lg border border-border', className].filter(Boolean).join(' ')}
    >
      <header className="border-b border-border px-4 py-3">
        <h2 className="text-[15px] font-semibold text-foreground">
          {t('panels.indicatorsTitle', { city: city ?? t('stats.allCities') })}
        </h2>
      </header>

      <div>
        {rows.map((row) => (
          <div
            key={row.label}
            data-testid="indicator-row"
            className="flex items-baseline justify-between gap-4 border-b border-border px-4 py-[10px]"
          >
            <span className="text-[13px] leading-5 text-muted-foreground">{row.label}</span>
            <MonoAnnotation
              className={[
                'text-[15px] font-semibold',
                row.tone === 'success' ? 'text-success' : row.tone === 'destructive' ? 'text-destructive' : '',
              ]
                .filter(Boolean)
                .join(' ')}
            >
              {row.value}
            </MonoAnnotation>
          </div>
        ))}
      </div>

      <p className="px-4 py-3 text-[12px] leading-[18px] text-muted-foreground">
        {t('panels.indicatorsNote')}
      </p>
    </section>
  );
}
