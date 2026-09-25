'use client';

import { useEffect, useState } from 'react';
import dynamic from 'next/dynamic';

// Recharts is a 5+ MB bundle; dynamic-import with ssr: false so it
// only ships to the browser after the page has rendered. Both charts
// (price trends and listing volume) live in the lazy component below.
const MarketTrendsChartsLazy = dynamic(
  () =>
    import('@/components/market-trends/MarketTrendsCharts').then(
      (m) => m.MarketTrendsCharts
    ),
  {
    ssr: false,
    loading: () => (
      <div className="h-80 w-full bg-muted animate-pulse rounded-lg" />
    ),
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

export default function MarketTrendsPage() {
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
        setError('Failed to load market data');
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
    })) || [];

  const TrendIcon =
    indicators?.overall_trend === 'rising'
      ? TrendingUp
      : indicators?.overall_trend === 'falling'
        ? TrendingDown
        : Minus;

  const trendColor =
    indicators?.overall_trend === 'rising'
      ? 'text-green-600'
      : indicators?.overall_trend === 'falling'
        ? 'text-red-600'
        : 'text-gray-600';

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="flex flex-col space-y-8">
        {/* Header */}
        <div className="flex flex-col space-y-4">
          <h1 className="text-3xl font-bold tracking-tight">Market Trends</h1>
          <p className="text-muted-foreground">
            Analyze price trends and market indicators across different areas.
          </p>
        </div>

        {/* Filters */}
        <Card>
          <CardHeader>
            <CardTitle>Filters</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="space-y-2">
                <Label htmlFor="city">City</Label>
                <Input
                  id="city"
                  placeholder="Enter city name"
                  value={city}
                  onChange={(e) => setCity(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="interval">Interval</Label>
                <Select value={interval} onValueChange={(v) => setInterval(v as typeof interval)}>
                  <SelectTrigger id="interval">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="month">Monthly</SelectItem>
                    <SelectItem value="quarter">Quarterly</SelectItem>
                    <SelectItem value="year">Yearly</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="months">Months Back</Label>
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
                  Apply Filters
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
                    <p className="text-sm text-muted-foreground">Overall Trend</p>
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
                    <p className="text-sm text-muted-foreground">Total Listings</p>
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
                  <div className="p-2 rounded-full bg-green-100">
                    <Activity className="h-6 w-6 text-green-600" />
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">New (7 days)</p>
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
                  <div className="p-2 rounded-full bg-red-100">
                    <DollarSign className="h-6 w-6 text-red-600" />
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Price Drops (7d)</p>
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
                    <CardTitle className="text-green-600">Hottest Areas</CardTitle>
                    <CardDescription>Highest average prices</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      {indicators.hottest_districts.map((district, index) => (
                        <div key={index} className="flex items-center justify-between">
                          <div>
                            <p className="font-medium">{district.name}</p>
                            <p className="text-sm text-muted-foreground">
                              {district.count} listings
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
                    <CardTitle className="text-blue-600">Most Affordable</CardTitle>
                    <CardDescription>Lowest average prices</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      {indicators.coldest_districts.map((district, index) => (
                        <div key={index} className="flex items-center justify-between">
                          <div>
                            <p className="font-medium">{district.name}</p>
                            <p className="text-sm text-muted-foreground">
                              {district.count} listings
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
