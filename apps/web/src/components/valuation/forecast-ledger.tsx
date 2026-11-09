'use client';

import { useLocale, useTranslations } from 'next-intl';

import { formatPrice, resolveLocale } from '@/lib/format';
import type { ForecastPoint, PriceForecastResponse } from '@/lib/api/tools';

/**
 * The forecast as a row of numbers.
 *
 * The design draws the forecast as columns under one ink rule: today loud,
 * every horizon quieter, and under each value the band the model is
 * uncertain between - the API's own lower and upper bound.
 *
 * Every number here comes from the forecast response. Nothing is derived
 * from the form the reader filled in: the asking price the reader typed is
 * not in the response, so the row does not compare against it.
 */

/** A compact number: 495 000 -> "495 tys." in Polish, "495K" in English. */
function compactNumber(value: number, locale: string): string {
  try {
    return new Intl.NumberFormat(resolveLocale(locale), {
      notation: 'compact',
      maximumFractionDigits: 1,
    }).format(value);
  } catch {
    return String(value);
  }
}

/**
 * The currency as a symbol the band can carry once.
 *
 * The band says "495-519 tys. zł", not the currency twice: the symbol is
 * pulled out of the formatter rather than hard-coded per language.
 */
function currencySymbol(currency: string, locale: string): string {
  try {
    const parts = new Intl.NumberFormat(resolveLocale(locale), {
      style: 'currency',
      currency,
      currencyDisplay: 'narrowSymbol',
    }).formatToParts(1);
    return parts.find((part) => part.type === 'currency')?.value ?? currency;
  } catch {
    return currency;
  }
}

/** The band under a value: the two edges the model is uncertain between. */
export function formatBand(
  point: ForecastPoint,
  currency: string,
  locale: string
): string {
  const symbol = currencySymbol(currency, locale);
  const low = compactNumber(point.lower_bound, locale);
  const high = compactNumber(point.upper_bound, locale);
  return `${low}-${high} ${symbol}`;
}

export interface ForecastLedgerProps {
  result: PriceForecastResponse;
  className?: string;
}

export function ForecastLedger({ result, className }: ForecastLedgerProps) {
  const t = useTranslations('pages.valuation');
  const locale = useLocale();
  const currency = result.currency || 'EUR';

  return (
    <div
      className={[
        'grid grid-cols-2 gap-x-4 border-t border-foreground sm:grid-cols-3 lg:grid-cols-5',
        className,
      ]
        .filter(Boolean)
        .join(' ')}
      data-testid="valuation-forecast-ledger"
    >
      <div className="flex flex-col gap-0.5 border-b border-border py-3 pr-2">
        <span className="text-[12px] leading-4 text-muted-foreground">
          {t('result.today')}
        </span>
        <span className="font-mono text-h3 font-semibold leading-6 text-foreground">
          {formatPrice(result.current_estimate, currency, locale)}
        </span>
      </div>

      {result.forecast.map((point) => (
        <div
          key={point.years_ahead}
          className="flex flex-col gap-0.5 border-b border-border py-3 pr-2"
        >
          <span className="text-[12px] leading-4 text-muted-foreground">
            {t('result.yearsLabel', { years: point.years_ahead })}
          </span>
          <span className="font-mono text-lede font-semibold leading-6 text-foreground">
            {formatPrice(point.estimated_value, currency, locale)}
          </span>
          <span className="font-mono text-[11px] leading-4 text-muted-foreground">
            {formatBand(point, currency, locale)}
          </span>
        </div>
      ))}
    </div>
  );
}
