'use client';

import { useLocale, useTranslations } from 'next-intl';
import Link from 'next/link';

import { Button } from '@/components/ui/button';
import { MonoAnnotation } from '@/components/ui/mono-annotation';
import { resolveLocale } from '@/lib/format';
import { currencyUnit, type CityMarketSummary } from './city-market-stats';

/**
 * The city in detail.
 *
 * The panel says what one city is worth: how many listings the catalogue
 * holds for it, where its prices sit between the cheapest and the dearest,
 * and where its average falls on that line. The bar is drawn on one scale
 * for the whole catalogue, so two cities can be read against each other.
 *
 * A city the catalogue holds nothing for says so, and points at the place
 * where the missing half is configured - a data provider with a key.
 */

function number(value: number, locale: string): string {
  try {
    return new Intl.NumberFormat(resolveLocale(locale), {
      maximumFractionDigits: 0,
    }).format(value);
  } catch {
    return String(value);
  }
}

export interface CityMarketDetailProps {
  /** The city the panel is about. */
  city: CityMarketSummary | null;
  /** The price the whole catalogue tops out at - the scale of the bar. */
  scale: number;
  className?: string;
}

export function CityMarketDetail({ city, scale, className }: CityMarketDetailProps) {
  const t = useTranslations('pages.cityOverview');
  const locale = useLocale();

  if (!city) return null;

  const unit = currencyUnit(city.currency);
  const hasListings = city.listingCount > 0 && city.minPrice !== null && city.maxPrice !== null;

  const minLeft = hasListings ? ((city.minPrice as number) / scale) * 100 : 0;
  const barWidth = hasListings
    ? (((city.maxPrice as number) - (city.minPrice as number)) / scale) * 100
    : 0;
  const avgLeft = hasListings && city.avgPrice !== null ? (city.avgPrice / scale) * 100 : 0;

  return (
    <div className={['mx-6 mb-6 rounded-lg border border-border p-4', className].filter(Boolean).join(' ')}>
      <div className="flex items-baseline justify-between gap-3">
        <span className="text-[18px] font-semibold leading-6 text-foreground">{city.label}</span>
        <MonoAnnotation>
          {t('detail.listings', { count: city.listingCount })}
        </MonoAnnotation>
      </div>

      {hasListings ? (
        <>
          <div className="mt-3 flex flex-col gap-1.5">
            <span className="text-[12px] leading-4 text-muted-foreground">
              {t('detail.priceRange', { unit })}
            </span>
            <div className="relative h-7" data-testid="price-range">
              <div className="absolute left-0 right-0 top-[13px] h-0.5 bg-border" />
              <div
                className="absolute top-[10px] h-2 rounded-sm bg-foreground"
                style={{ left: `${minLeft}%`, width: `${barWidth}%` }}
              />
              <div
                className="absolute top-[4px] h-5 w-0.5 bg-action"
                style={{ left: `${avgLeft}%` }}
                aria-hidden="true"
              />
            </div>
            <div className="flex items-baseline justify-between gap-3 font-mono text-[12px] leading-4">
              <span className="text-foreground">{number(city.minPrice as number, locale)}</span>
              <span className="text-action">
                {t('detail.average', { value: number(city.avgPrice as number, locale) })}
              </span>
              <span className="text-foreground">{number(city.maxPrice as number, locale)}</span>
            </div>
          </div>

          <div className="mt-4 flex flex-wrap items-center gap-2">
            <Button asChild size="sm" className="h-9">
              <Link href={`/${locale}/search?q=${encodeURIComponent(`properties in ${city.city}`)}`}>
                {t('detail.searchCta', { city: city.label })}
              </Link>
            </Button>
            <Button asChild size="sm" variant="outline" className="h-9">
              <Link href={`/${locale}/market-trends`}>{t('detail.trendsCta')}</Link>
            </Button>
          </div>
        </>
      ) : (
        <>
          <p className="mt-3 text-[14px] leading-5 text-muted-foreground">
            {t('detail.empty', { city: city.label })}
          </p>
          <Link
            href={`/${locale}/admin#data-sources`}
            className="mt-2 inline-block text-[14px] font-medium text-foreground hover:underline"
          >
            {t('detail.dataSourcesCta')}
          </Link>
        </>
      )}
    </div>
  );
}
