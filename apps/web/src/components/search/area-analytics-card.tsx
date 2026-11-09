'use client';

import { useLocale, useTranslations } from 'next-intl';
import Link from 'next/link';

import { MonoAnnotation } from '@/components/ui/mono-annotation';
import { StatTile } from '@/components/ui/stat-tile';
import { resolveLocale } from '@/lib/format';
import type { SearchResultItem } from '@/lib/types';

/**
 * The area analytics card, over the map.
 *
 * The card states what the area in view is worth. Every number in it is
 * computed from the listings the search returned - the median price per m²
 * of the area, how many of them there are, and the median price. Nothing is
 * carried over from a model of the market: what is not in the catalogue is
 * not on the card.
 */

/** The median of a list of numbers. An even count takes the middle pair. */
function median(values: number[]): number | null {
  if (values.length === 0) return null;
  const sorted = [...values].sort((a, b) => a - b);
  const middle = Math.floor(sorted.length / 2);
  if (sorted.length % 2 === 1) return sorted[middle];
  return (sorted[middle - 1] + sorted[middle]) / 2;
}

export interface AreaAnalyticsCardProps {
  results: SearchResultItem[];
  className?: string;
}

export function AreaAnalyticsCard({ results, className }: AreaAnalyticsCardProps) {
  const t = useTranslations('search');
  const locale = useLocale();

  // The area is the one most of the results stand in. The listings are
  // grouped by the finest place the catalogue names.
  const groups = new Map<string, SearchResultItem[]>();
  for (const item of results) {
    const property = item.property;
    const name = property.district || property.neighborhood || property.city;
    if (!name) continue;
    const group = groups.get(name);
    if (group) group.push(item);
    else groups.set(name, [item]);
  }

  let areaName: string | null = null;
  let areaListings: SearchResultItem[] = [];
  for (const [name, group] of groups) {
    if (group.length > areaListings.length) {
      areaName = name;
      areaListings = group;
    }
  }

  const currency = areaListings[0]?.property.currency || 'USD';
  const perSqmValues = areaListings
    .map((item) => item.property)
    .filter((property) => property.price && property.area_sqm)
    .map((property) => (property.price as number) / (property.area_sqm as number));
  const yearValues = areaListings
    .map((item) => item.property.year_built)
    .filter((year): year is number => typeof year === 'number' && year > 0);

  const medianPerSqm = median(perSqmValues);
  const medianYearBuilt = median(yearValues);

  return (
    <div
      className={[
        'absolute left-4 top-4 z-[1000] w-[300px] rounded-lg border border-border bg-background p-4 shadow-[0_1px_2px_rgb(9_9_11/0.06)]',
        className,
      ]
        .filter(Boolean)
        .join(' ')}
    >
      <div className="flex items-baseline justify-between gap-3">
        <span className="truncate text-[15px] font-semibold text-foreground">
          {areaName ?? t('area.empty')}
        </span>
        <MonoAnnotation className="shrink-0">{t('area.label')}</MonoAnnotation>
      </div>

      {areaName ? (
        <>
          <div className="mt-3 grid grid-cols-3 gap-3">
            <StatTile
              value={
                medianPerSqm !== null
                  ? Math.round(medianPerSqm).toLocaleString(resolveLocale(locale))
                  : '—'
              }
              label={t('area.medianPerSqm')}
              hint={medianPerSqm !== null ? `${currency}/m²` : undefined}
            />
            <StatTile value={areaListings.length} label={t('area.listings')} />
            <StatTile
              value={medianYearBuilt !== null ? Math.round(medianYearBuilt) : '—'}
              label={t('area.medianYearBuilt')}
            />
          </div>

          <div className="mt-3 flex items-center justify-between gap-3 border-t border-border pt-2.5">
            <span className="text-[12px] text-muted-foreground">{t('area.note')}</span>
            <Link
              href={`/${locale}/city-overview`}
              className="shrink-0 text-[12px] text-foreground hover:underline"
            >
              {t('area.cityOverview')}
            </Link>
          </div>
        </>
      ) : null}
    </div>
  );
}
