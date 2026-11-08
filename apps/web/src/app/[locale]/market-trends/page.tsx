'use client';

import { useEffect, useState } from 'react';
import dynamic from 'next/dynamic';
import { useTranslations } from 'next-intl';

// Recharts is a 5+ MB bundle; dynamic-import with ssr: false so it
// only ships to the browser after the page has rendered. Both charts
// (price trends and listing volume) live in the lazy component below.
const MarketTrendsChartsLazy = dynamic(
  () => import('@/components/market-trends/MarketTrendsCharts').then((m) => m.MarketTrendsCharts),
  {
    ssr: false,
    loading: () => <div className="h-80 w-full bg-muted animate-pulse rounded-lg" />,
  }
);
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  TrendingUp,
  TrendingDown,
  Minus,
  Loader2,
  AlertCircle,
  Activity,
  DollarSign,
  Building2,
} from 'lucide-react';
import { getMarketTrends, getMarketIndicators, ApiError } from '@/lib/api';
import { MarketTrends, MarketIndicators, MarketTrendPoint } from '@/lib/types';
import { AreaComparisonComponent } from '@/components/analytics/area-comparison';
import { PageHeader } from '@/components/ui/page-header';

export default function MarketTrendsPage() {
  const t = useTranslations('pages.marketTrends');
  // "Apply Filters" and the listing counter are shared copy — they live in the
  // `search` and `cma` namespaces of the catalogue, so they are read from
  // there instead of being written out again here.
  const tSearch = useTranslations('search');
  const tCma = useTranslations('cma.preview');
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

  const chartData =
    trends?.data_points.map((point: MarketTrendPoint) => ({
      period: point.period,
      avgPrice: point.average_price,
      medianPrice: point.median_price,
      volume: point.volume,
      currency: point.currency,
    })) || [];

  const TrendIcon =
    indicators?.overall_trend === 'rising'
      ? TrendingUp
      : indicators?.overall_trend === 'falling'
        ? TrendingDown
        : Minus;

  const trendColor =
    indicators?.overall_trend === 'rising'
      ? 'text-success'
      : indicators?.overall_trend === 'falling'
        ? 'text-destructive'
        : 'text-muted-foreground';

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="flex flex-col space-y-8">
        {/* Header */}
        <PageHeader title={t('title')} description={t('description')} />

        {/* Filters */}
        <Card>
          <CardHeader>
            <CardTitle>{t('filters.title')}</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="space-y-2">
                <Label htmlFor="city">{t('filters.city')}</Label>
                <Input
                  id="city"
                  placeholder={t('filters.cityPlaceholder')}
                  value={city}
                  onChange={(e) => setCity(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="interval">{t('filters.interval')}</Label>
                <Select value={interval} onValueChange={(v) => setInterval(v as typeof interval)}>
                  <SelectTrigger id="interval">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="month">{t('filters.monthly')}</SelectItem>
                    <SelectItem value="quarter">{t('filters.quarterly')}</SelectItem>
                    <SelectItem value="year">{t('filters.yearly')}</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="months">{t('filters.monthsBack')}</Label>
                <Input
                  id="months"
                  type="number"
                  min={1}
                  max={60}
                  value={monthsBack}
                  onChange={(e) => setMonthsBack(parseInt(e.target.value) || 12)}
                />
              </div>
              <div className="flex items-end">
                <Button onClick={fetchData} disabled={loading}>
                  {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                  {tSearch('filters.applyFilters')}
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Error state */}
        {error && (
          <div className="flex items-center gap-2 p-4 border border-destructive/20 bg-destructive/10 rounded-lg">
            <AlertCircle className="h-5 w-5 text-destructive" />
            <p className="text-destructive">{error}</p>
          </div>
        )}

        {/* Loading state */}
        {loading && !trends && (
          <div className="flex items-center justify-center h-64">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
          </div>
        )}

        {/* Market Indicators */}
        {indicators && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center gap-4">
                  <div className={`p-2 rounded-full ${trendColor} bg-muted`}>
                    <TrendIcon className="h-6 w-6" />
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">{t('stats.overallTrend')}</p>
                    <p className={`text-xl font-semibold capitalize ${trendColor}`}>
                      {indicators.overall_trend}
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center gap-4">
                  <div className="p-2 rounded-full bg-primary/10">
                    <Building2 className="h-6 w-6 text-primary" />
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">{t('stats.totalListings')}</p>
                    <p className="text-xl font-semibold">
                      {indicators.total_listings.toLocaleString()}
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center gap-4">
                  <div className="p-2 rounded-full bg-success/15">
                    <Activity className="h-6 w-6 text-success" />
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">{t('stats.new7d')}</p>
                    <p className="text-xl font-semibold">
                      {indicators.new_listings_7d.toLocaleString()}
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center gap-4">
                  <div className="p-2 rounded-full bg-destructive/15">
                    <DollarSign className="h-6 w-6 text-destructive" />
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">{t('stats.priceDrops7d')}</p>
                    <p className="text-xl font-semibold">
                      {indicators.price_drops_7d.toLocaleString()}
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Price + Volume Charts (dynamic-imported recharts bundle) */}
        {trends && trends.data_points.length > 0 && (
          <MarketTrendsChartsLazy chartData={chartData} />
        )}

        {/* Hottest/Coldest Districts */}
        {indicators &&
          (indicators.hottest_districts.length > 0 || indicators.coldest_districts.length > 0) && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {indicators.hottest_districts.length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle className="text-success">{t('areas.hottest')}</CardTitle>
                    <CardDescription>{t('areas.hottestHint')}</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      {indicators.hottest_districts.map((district, index) => (
                        <div key={index} className="flex items-center justify-between">
                          <div>
                            <p className="font-medium">{district.name}</p>
                            <p className="text-sm text-muted-foreground">
                              {tCma('listings', { count: district.count })}
                            </p>
                          </div>
                          <p className="font-semibold">${district.avg_price.toLocaleString()}</p>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}

              {indicators.coldest_districts.length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle className="text-info">{t('areas.affordable')}</CardTitle>
                    <CardDescription>{t('areas.affordableHint')}</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      {indicators.coldest_districts.map((district, index) => (
                        <div key={index} className="flex items-center justify-between">
                          <div>
                            <p className="font-medium">{district.name}</p>
                            <p className="text-sm text-muted-foreground">
                              {tCma('listings', { count: district.count })}
                            </p>
                          </div>
                          <p className="font-semibold">${district.avg_price.toLocaleString()}</p>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}
            </div>
          )}

        {/* Area Comparison Section - Task #84 */}
        <AreaComparisonComponent />
      </div>
    </div>
  );
}
