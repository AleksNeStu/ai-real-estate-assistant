'use client';

import { useState } from 'react';
import { useLocale, useTranslations } from 'next-intl';
import { Loader2 } from 'lucide-react';

import { compareAreas, ApiError } from '@/lib/api';
import { AreaComparison } from '@/lib/types';
import { formatPrice, resolveLocale } from '@/lib/format';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { MonoAnnotation } from '@/components/ui/mono-annotation';
import { ErrorState } from '@/components/ui/states';

/**
 * Two areas, side by side.
 *
 * The panel is a comparison, so it is drawn as one: the two areas in the
 * header, the metric down the middle, the two numbers on either side. Every
 * number is the one the API returned for that area, in the currency of the
 * listings the area holds.
 */

/** The amenity keys the catalogue names, mapped to their reader-visible label. */
const AMENITY_LABEL_KEYS: Record<string, string> = {
  parking: 'parking',
  garden: 'garden',
  pool: 'pool',
  furnished: 'furnished',
  balcony: 'balcony',
  elevator: 'elevator',
};

const CONTROL_CLASS =
  'h-9 w-full rounded-md border border-input bg-background px-2.5 text-[13px] text-foreground';
const LABEL_CLASS = 'text-[12px] font-medium text-foreground';

export function AreaComparisonComponent() {
  const t = useTranslations('marketTrends');
  const tInv = useTranslations('investment');
  const tCompare = useTranslations('pages.tools.compare');
  const locale = useLocale();

  const [city1, setCity1] = useState('Warsaw');
  const [city2, setCity2] = useState('Krakow');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [comparison, setComparison] = useState<AreaComparison | null>(null);

  const handleCompare = async () => {
    if (!city1.trim() || !city2.trim()) {
      setError(t('areaComparison.bothCitiesRequired'));
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const result = await compareAreas(city1.trim(), city2.trim());
      setComparison(result);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError(t('areaComparison.compareFailed'));
      }
    } finally {
      setLoading(false);
    }
  };

  const money = (value: number | undefined, currency?: string): string => {
    if (value === undefined || value === null) return '—';
    return formatPrice(value, currency ?? 'PLN', resolveLocale(locale));
  };

  const number = (value: number | undefined): string => {
    if (value === undefined || value === null) return '—';
    return value.toLocaleString();
  };

  const rows: Array<{ label: string; left: string; right: string }> = comparison
    ? [
        {
          label: t('areaComparison.avgPrice'),
          left: money(comparison.area1.avg_price, comparison.area1.currency),
          right: money(comparison.area2.avg_price, comparison.area2.currency),
        },
        {
          label: t('areaComparison.medianPrice'),
          left: money(comparison.area1.median_price, comparison.area1.currency),
          right: money(comparison.area2.median_price, comparison.area2.currency),
        },
        {
          label: t('areaComparison.pricePerSqm'),
          left: money(comparison.area1.avg_price_per_sqm, comparison.area1.currency),
          right: money(comparison.area2.avg_price_per_sqm, comparison.area2.currency),
        },
        {
          label: t('areaComparison.listings'),
          left: number(comparison.area1.property_count),
          right: number(comparison.area2.property_count),
        },
        {
          label: t('areaComparison.avgRooms'),
          left: number(comparison.area1.most_common_room_count),
          right: number(comparison.area2.most_common_room_count),
        },
      ]
    : [];

  return (
    <section className="rounded-lg border border-border">
      <header className="flex items-baseline justify-between gap-4 border-b border-border px-4 py-3">
        <h2 className="text-[15px] font-semibold text-foreground">{tInv('areaComparison.title')}</h2>
        <MonoAnnotation>
          {comparison ? comparison.area1.city : t('areaComparison.description')}
        </MonoAnnotation>
      </header>

      <div className="px-4 py-4">
        <div className="grid gap-3 sm:grid-cols-2">
          <div className="space-y-1.5">
            <Label htmlFor="city1" className={LABEL_CLASS}>
              {t('areaComparison.firstCity')}
            </Label>
            <Input
              id="city1"
              className={CONTROL_CLASS}
              placeholder={t('areaComparison.cityPlaceholder')}
              value={city1}
              onChange={(e) => setCity1(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleCompare()}
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="city2" className={LABEL_CLASS}>
              {t('areaComparison.secondCity')}
            </Label>
            <Input
              id="city2"
              className={CONTROL_CLASS}
              placeholder={t('areaComparison.cityPlaceholder')}
              value={city2}
              onChange={(e) => setCity2(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleCompare()}
            />
          </div>
        </div>

        <div className="mt-3 flex items-center gap-3">
          <Button onClick={handleCompare} disabled={loading} size="sm" className="h-9">
            {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />}
            {tCompare('compare')}
          </Button>
          {comparison ? (
            <MonoAnnotation>
              {t('areaComparison.priceDifference')} {comparison.price_difference_percent.toFixed(1)}%
            </MonoAnnotation>
          ) : null}
        </div>

        {error ? (
          <div className="mt-4">
            <ErrorState title={t('areaComparison.compareFailed')} description={error} />
          </div>
        ) : null}

        {loading && !comparison ? (
          <div className="flex items-center justify-center py-10" role="status">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" aria-hidden="true" />
          </div>
        ) : null}

        {comparison ? (
          <>
            <div className="mt-5 grid grid-cols-[minmax(0,1fr)_auto_auto] gap-x-4 border-t border-foreground pt-2 text-[12px] leading-4 text-muted-foreground">
              <span>{t('areaComparison.metric')}</span>
              <span className="text-right">{comparison.area1.city}</span>
              <span className="text-right">{comparison.area2.city}</span>
            </div>
            {rows.map((row) => (
              <div
                key={row.label}
                className="grid grid-cols-[minmax(0,1fr)_auto_auto] items-baseline gap-x-4 border-b border-border py-2"
              >
                <span className="text-[13px] leading-5 text-muted-foreground">{row.label}</span>
                <span className="text-right font-mono text-[13px] leading-5 text-foreground">
                  {row.left}
                </span>
                <span className="text-right font-mono text-[13px] leading-5 text-foreground">
                  {row.right}
                </span>
              </div>
            ))}

            {comparison.area1.amenity_availability &&
            Object.keys(comparison.area1.amenity_availability).length > 0 ? (
              <div className="mt-4">
                <h3 className="text-[12px] font-medium text-muted-foreground">
                  {t('areaComparison.amenityAvailability')}
                </h3>
                <div className="mt-2 grid grid-cols-2 gap-x-4 gap-y-1 sm:grid-cols-3">
                  {Object.entries(comparison.area1.amenity_availability).map(([key, val1]) => {
                    const val2 = comparison.area2.amenity_availability?.[key] ?? 0;
                    const amenityKey = AMENITY_LABEL_KEYS[key];
                    const amenityLabel = amenityKey
                      ? tInv(`areaComparison.amenities.${amenityKey}`)
                      : key.replace(/_/g, ' ');
                    return (
                      <div
                        key={key}
                        className="flex items-baseline justify-between gap-2 border-b border-border py-1"
                      >
                        <span className="truncate text-[13px] text-foreground">{amenityLabel}</span>
                        <span className="font-mono text-[12px] text-muted-foreground">
                          {val1.toFixed(0)}% / {val2.toFixed(0)}%
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>
            ) : null}
          </>
        ) : null}
      </div>
    </section>
  );
}
