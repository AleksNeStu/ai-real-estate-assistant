'use client';

import { useEffect, useMemo, useState } from 'react';
import dynamic from 'next/dynamic';
import Link from 'next/link';
import { useLocale, useTranslations } from 'next-intl';
import { Loader2 } from 'lucide-react';

import { getMarketTrends, getMarketIndicators, ApiError } from '@/lib/api';
import { MarketTrends, MarketIndicators, MarketTrendPoint } from '@/lib/types';
import { AreaComparisonComponent } from '@/components/analytics/area-comparison';
import { PageHeader } from '@/components/ui/page-header';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { MonoAnnotation } from '@/components/ui/mono-annotation';
import { ErrorState } from '@/components/ui/states';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { MarketIndicatorsPanel } from '@/components/market-trends/market-indicators';
import { DistrictsLedger } from '@/components/market-trends/districts-ledger';

// Recharts is a 5+ MB bundle; dynamic-import with ssr: false so it only
// ships to the browser after the page has rendered. Both charts live in the
// lazy component below, and the frame around each of them holds the space
// open, so the page does not move when the bundle arrives.
const MarketTrendsChartsLazy = dynamic(
  () => import('@/components/market-trends/MarketTrendsCharts').then((m) => m.MarketTrendsCharts),
  {
    ssr: false,
    loading: () => <div className="h-64 w-full animate-pulse rounded-lg bg-muted" />,
  }
);

const CONTROL_CLASS =
  'h-9 w-full rounded-md border border-input bg-background px-2.5 text-[13px] text-foreground';
const LABEL_CLASS = 'text-[12px] font-medium text-foreground';

export default function MarketTrendsPage() {
  const t = useTranslations('pages.marketTrends');
  // "Apply Filters" and the listing counter are shared copy — they live in
  // the `search` and `cma` namespaces of the catalogue, so they are read from
  // there instead of being written out again here.
  const tSearch = useTranslations('search');
  const locale = useLocale();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [trends, setTrends] = useState<MarketTrends | null>(null);
  const [indicators, setIndicators] = useState<MarketIndicators | null>(null);

  // Filter state
  const [city, setCity] = useState<string>('');
  const [interval, setInterval] = useState<'month' | 'quarter' | 'year'>('month');
  const [monthsBack, setMonthsBack] = useState<number>(12);

  const fetchData = async () => {
    setLoading(true);
    setError(null);

    try {
      const [trendsData, indicatorsData] = await Promise.all([
        getMarketTrends({
          city: city || undefined,
          interval,
          months_back: monthsBack,
        }),
        getMarketIndicators(city || undefined),
      ]);
      setTrends(trendsData);
      setIndicators(indicatorsData);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError(t('errors.load'));
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [interval, monthsBack]);

  const chartData = useMemo(
    () =>
      trends?.data_points.map((point: MarketTrendPoint) => ({
        period: point.period,
        avgPrice: point.average_price,
        medianPrice: point.median_price,
        volume: point.volume,
        currency: point.currency,
      })) || [],
    [trends]
  );

  // The currency the prices of this market are in. It is what the districts
  // are quoted in as well - they come from the same catalogue.
  const currency = useMemo(
    () => chartData.find((point) => point.currency)?.currency,
    [chartData]
  );

  // The price per m² of the last period - the one number of the curve that
  // belongs on the indicators panel.
  const pricePerSqm = useMemo(() => {
    const last = trends?.data_points[trends.data_points.length - 1];
    return last?.avg_price_per_sqm ?? null;
  }, [trends]);

  const scope = t('scope', {
    city: city || t('scopeAllCities'),
    months: monthsBack,
  });
  const chartCaption = t('chartCaption', {
    months: monthsBack,
    interval: t(`filters.${interval === 'month' ? 'monthly' : interval === 'quarter' ? 'quarterly' : 'yearly'}`),
  });

  return (
    <div className="flex min-h-[calc(100vh-56px)] flex-col" aria-live="polite">
      <div className="border-b border-border px-6 pb-5 pt-6">
        <PageHeader
          title={t('title')}
          description={t('description')}
          actions={<MonoAnnotation>{scope}</MonoAnnotation>}
        />

        {/* Filters */}
        <div className="mt-5 grid items-end gap-3 sm:grid-cols-[minmax(0,1fr)_160px_120px_auto]">
          <div className="space-y-1.5">
            <Label htmlFor="city" className={LABEL_CLASS}>
              {t('filters.city')}
            </Label>
            <Input
              id="city"
              className={CONTROL_CLASS}
              placeholder={t('filters.cityPlaceholder')}
              value={city}
              onChange={(e) => setCity(e.target.value)}
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="interval" className={LABEL_CLASS}>
              {t('filters.interval')}
            </Label>
            <Select value={interval} onValueChange={(v) => setInterval(v as typeof interval)}>
              <SelectTrigger id="interval" className={CONTROL_CLASS}>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="month">{t('filters.monthly')}</SelectItem>
                <SelectItem value="quarter">{t('filters.quarterly')}</SelectItem>
                <SelectItem value="year">{t('filters.yearly')}</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="months" className={LABEL_CLASS}>
              {t('filters.monthsBack')}
            </Label>
            <Input
              id="months"
              className={CONTROL_CLASS}
              type="number"
              min={1}
              max={60}
              value={monthsBack}
              onChange={(e) => setMonthsBack(parseInt(e.target.value) || 12)}
            />
          </div>
          <div>
            <Button onClick={fetchData} disabled={loading} className="h-9">
              {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />}
              {tSearch('filters.applyFilters')}
            </Button>
          </div>
        </div>
      </div>

      {error ? (
        <div className="px-6 pt-6">
          <ErrorState title={error} />
        </div>
      ) : null}

      {loading && !trends ? (
        <div className="flex items-center justify-center px-6 py-16" role="status">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" aria-hidden="true" />
        </div>
      ) : (
        <div className="grid flex-1 grid-cols-1 gap-6 p-6 lg:grid-cols-[minmax(0,1fr)_360px]">
          <main className="flex min-w-0 flex-col gap-6">
            {trends && trends.data_points.length > 0 ? (
              <MarketTrendsChartsLazy chartData={chartData} caption={chartCaption} />
            ) : null}

            <AreaComparisonComponent />
          </main>

          <aside className="flex min-w-0 flex-col gap-4">
            {indicators ? (
              <MarketIndicatorsPanel
                indicators={indicators}
                city={city || null}
                pricePerSqm={pricePerSqm}
              />
            ) : null}

            {indicators ? (
              <DistrictsLedger indicators={indicators} currency={currency} />
            ) : null}

            <Link
              href={`/${locale}/cma`}
              className="flex items-center justify-between rounded-lg border border-border px-4 py-3 text-[14px] font-medium text-foreground transition-colors hover:bg-muted"
            >
              {t('aside.cmaCta')}
              <span aria-hidden="true">→</span>
            </Link>
            <Link
              href={`/${locale}/valuation`}
              className="flex items-center justify-between rounded-lg border border-border px-4 py-3 text-[14px] font-medium text-foreground transition-colors hover:bg-muted"
            >
              {t('aside.valuationCta')}
              <span aria-hidden="true">→</span>
            </Link>
          </aside>
        </div>
      )}
    </div>
  );
}
