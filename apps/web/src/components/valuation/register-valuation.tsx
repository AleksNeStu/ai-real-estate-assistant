'use client';

import { useLocale, useTranslations } from 'next-intl';

import { formatPrice } from '@/lib/format';
import type { ValuationResponse } from '@/lib/api/tools';

/**
 * The valuation as the register states it.
 *
 * The number is loud and everything that made it is quiet: how many sales it
 * rests on, the period they cover, the area they came from. A reader who
 * wants to know whether to believe the number can read all three without
 * leaving the page, and the sales themselves are listed underneath — the
 * deed, the date and the price per square metre, so the comparison can be
 * checked rather than believed.
 */
export interface RegisterValuationProps {
  result: ValuationResponse;
  className?: string;
}

export function RegisterValuation({ result, className }: RegisterValuationProps) {
  const t = useTranslations('pages.valuation');
  const locale = useLocale();
  const currency = result.currency || 'PLN';

  const facts = [
    { label: t('register.comparisonArea'), value: result.comparison_area || '—' },
    {
      label: t('register.sample'),
      value:
        result.sample_size != null
          ? t('register.sampleCount', { count: result.sample_size })
          : '—',
    },
    {
      label: t('register.period'),
      value:
        result.period_start && result.period_end
          ? `${result.period_start} → ${result.period_end}`
          : '—',
    },
    { label: t('register.confidence'), value: result.confidence || '—' },
  ];

  return (
    <div className={['flex flex-col gap-6', className].filter(Boolean).join(' ')} data-testid="register-valuation">
      <div className="grid grid-cols-1 gap-x-4 border-t border-foreground sm:grid-cols-2 lg:grid-cols-4">
        <div className="flex flex-col gap-0.5 border-b border-border py-3 pr-2">
          <span className="text-[12px] leading-4 text-muted-foreground">
            {t('register.estimate')}
          </span>
          <span className="font-mono text-h3 font-semibold leading-6 text-foreground">
            {formatPrice(result.estimated_value, currency, locale)}
          </span>
          {result.low != null && result.high != null ? (
            <span className="font-mono text-[11px] leading-4 text-muted-foreground">
              {formatPrice(result.low, currency, locale)} –{' '}
              {formatPrice(result.high, currency, locale)}
            </span>
          ) : null}
        </div>

        {result.price_per_sqm_median != null ? (
          <div className="flex flex-col gap-0.5 border-b border-border py-3 pr-2">
            <span className="text-[12px] leading-4 text-muted-foreground">
              {t('register.medianPerSqm')}
            </span>
            <span className="font-mono text-lede font-semibold leading-6 text-foreground">
              {formatPrice(result.price_per_sqm_median, currency, locale)}/m²
            </span>
          </div>
        ) : null}

        {facts.map((fact) => (
          <div key={fact.label} className="flex flex-col gap-0.5 border-b border-border py-3 pr-2">
            <span className="text-[12px] leading-4 text-muted-foreground">{fact.label}</span>
            <span className="text-[14px] leading-6 text-foreground">{fact.value}</span>
          </div>
        ))}
      </div>

      {result.notes.length ? (
        <ul className="flex flex-col gap-1">
          {result.notes.map((note, index) => (
            <li key={`${note}-${index}`} className="text-[12px] leading-5 text-muted-foreground">
              {note}
            </li>
          ))}
        </ul>
      ) : null}

      {result.comparables.length ? (
        <section className="flex flex-col gap-2">
          <h2 className="text-[14px] font-semibold text-foreground">{t('register.sales')}</h2>
          <ul className="border-t border-foreground">
            {result.comparables.map((comparable, index) => (
              <li
                key={`${comparable.deed_reference ?? 'sale'}-${index}`}
                className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 border-b border-border py-2.5"
              >
                <span className="text-[14px] leading-5 text-foreground">
                  {comparable.address}
                </span>
                <span className="font-mono text-[12px] leading-5 text-muted-foreground">
                  {comparable.area_sqm.toFixed(1)} m² ·{' '}
                  {formatPrice(comparable.price, currency, locale)} (
                  {formatPrice(comparable.price_per_sqm, currency, locale)}/m²) ·{' '}
                  {comparable.transaction_date}
                  {comparable.deed_reference ? ` · ${comparable.deed_reference}` : ''}
                </span>
              </li>
            ))}
          </ul>
        </section>
      ) : null}
    </div>
  );
}
