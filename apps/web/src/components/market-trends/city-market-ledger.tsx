'use client';

import { useLocale, useTranslations } from 'next-intl';

import { resolveLocale } from '@/lib/format';
import { currencyUnit, type CityMarketSummary } from './city-market-stats';

/**
 * The catalogue as a ledger.
 *
 * The cities are a list, so the list is drawn as a ledger: a rule opens it,
 * every row is a city, and every number is mono. A city the catalogue holds
 * nothing for still gets its row - its numbers read as a dash, which says
 * "not covered" instead of "worth nothing".
 *
 * The row is the control: picking a city picks the row. The selected row
 * carries the ink rule on its left edge and the muted ground, so the
 * selection is visible in the shape of the table and not only in the detail
 * panel below it.
 */

/** A bare number, in the compact form the columns have room for. */
function compact(value: number | null, locale: string): string {
  if (value === null) return '—';
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
 * A number as it is written out.
 *
 * The price per m² is not compact: a rounded "17.5K" is a different number
 * from the one the catalogue holds, and this column has the room for the
 * exact figure.
 */
function plain(value: number | null, locale: string): string {
  if (value === null) return '—';
  try {
    return new Intl.NumberFormat(resolveLocale(locale), {
      maximumFractionDigits: 0,
    }).format(value);
  } catch {
    return String(value);
  }
}

export interface CityMarketLedgerProps {
  cities: CityMarketSummary[];
  /** The city the detail panel is showing. */
  selected: string | null;
  onSelect: (city: string) => void;
  className?: string;
}

export function CityMarketLedger({
  cities,
  selected,
  onSelect,
  className,
}: CityMarketLedgerProps) {
  const t = useTranslations('pages.cityOverview');
  const locale = useLocale();

  // The unit the prices of this catalogue are written in. It is stated once,
  // under the ledger, so the numbers in the columns stay bare.
  const unit = currencyUnit(cities.find((city) => city.currency)?.currency);

  return (
    <div className={className}>
      <div
        className="hidden gap-3 border-b border-foreground px-6 pb-2 text-[12px] leading-4 text-muted-foreground md:grid md:grid-cols-[1.2fr_.6fr_1fr_1fr_1fr_.9fr]"
        aria-hidden="true"
      >
        <span>{t('table.city')}</span>
        <span className="text-right">{t('table.listings')}</span>
        <span className="text-right">{t('table.average')}</span>
        <span className="text-right">{t('table.min')}</span>
        <span className="text-right">{t('table.max')}</span>
        <span className="text-right">
          {unit}/{t('table.perSqmUnit')}
        </span>
      </div>

      <div>
        {cities.map((city) => {
          const isSelected = selected === city.city;
          return (
            <button
              key={city.city}
              type="button"
              onClick={() => onSelect(city.city)}
              aria-pressed={isSelected}
              data-testid="city-row"
              data-city={city.city}
              className={[
                'grid w-full grid-cols-[minmax(0,1fr)_auto] items-baseline gap-x-3 gap-y-1 border-b border-border px-6 py-3 text-left transition-colors hover:bg-muted/60 md:grid-cols-[1.2fr_.6fr_1fr_1fr_1fr_.9fr]',
                isSelected
                  ? 'bg-muted shadow-[inset_2px_0_0_0_hsl(var(--foreground))]'
                  : '',
              ]
                .filter(Boolean)
                .join(' ')}
            >
              <span className="min-w-0">
                <span
                  className={[
                    'block truncate text-[14px] font-medium leading-5',
                    city.listingCount > 0 ? 'text-foreground' : 'text-muted-foreground',
                  ].join(' ')}
                >
                  {city.label}
                </span>
                <span className="block truncate text-[12px] leading-4 text-muted-foreground md:hidden">
                  {city.country}
                </span>
              </span>

              <span className="text-right font-mono text-[13px] leading-5 text-foreground">
                {city.listingCount}
              </span>

              <span className="col-span-2 flex flex-wrap gap-x-4 gap-y-1 md:contents">
                <span className="font-mono text-[13px] leading-5 text-foreground md:text-right">
                  <span className="text-muted-foreground md:hidden">{t('table.average')} </span>
                  {compact(city.avgPrice, locale)}
                </span>
                <span className="font-mono text-[13px] leading-5 text-foreground md:text-right">
                  <span className="text-muted-foreground md:hidden">{t('table.min')} </span>
                  {compact(city.minPrice, locale)}
                </span>
                <span className="font-mono text-[13px] leading-5 text-foreground md:text-right">
                  <span className="text-muted-foreground md:hidden">{t('table.max')} </span>
                  {compact(city.maxPrice, locale)}
                </span>
                <span className="font-mono text-[13px] leading-5 text-foreground md:text-right">
                  <span className="text-muted-foreground md:hidden">{t('table.perSqm')} </span>
                  {plain(city.pricePerSqm, locale)}
                </span>
              </span>
            </button>
          );
        })}
      </div>

      <p className="px-6 py-3 text-[12px] leading-[18px] text-muted-foreground">
        {t('ledger.note', { unit })}
      </p>
    </div>
  );
}
