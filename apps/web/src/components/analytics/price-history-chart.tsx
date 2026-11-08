'use client';

import { useEffect, useState, useMemo } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Loader2, AlertCircle, TrendingUp, TrendingDown, Minus, AlertTriangle } from 'lucide-react';
import { getPriceHistory, getAnomalies, ApiError } from '@/lib/api';
import { PriceHistory, PriceSnapshot, MarketAnomaly } from '@/lib/types';
import { AnomalyBadge } from './anomaly-badge';
import { useTranslations } from 'next-intl';

interface PriceHistoryChartProps {
  propertyId: string;
  className?: string;
  showAnomalies?: boolean;
}

export function PriceHistoryChart({
  propertyId,
  className,
  showAnomalies = true,
}: PriceHistoryChartProps) {
  const t = useTranslations('marketTrends');
  const tInv = useTranslations('investment');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<PriceHistory | null>(null);
  const [anomalies, setAnomalies] = useState<MarketAnomaly[]>([]);

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      setError(null);

      try {
        const [history, anomalyResponse] = await Promise.all([
          getPriceHistory(propertyId, 100),
          showAnomalies
            ? getAnomalies({ scope_type: 'property', scope_id: propertyId, limit: 50 })
            : Promise.resolve({ anomalies: [] }),
        ]);
        setData(history);
        setAnomalies(anomalyResponse.anomalies);
      } catch (err) {
        if (err instanceof ApiError) {
          setError(err.message);
        } else if (err instanceof Error) {
          setError(err.message);
        } else {
          setError(t('priceHistory.loadFailed'));
        }
      } finally {
        setLoading(false);
      }
    };

    if (propertyId) {
      fetchData();
    }
  }, [propertyId, showAnomalies, t]);

  // Create a lookup for anomalies by date
  const anomaliesByDate = useMemo(() => {
    const lookup: Record<string, MarketAnomaly[]> = {};
    for (const anomaly of anomalies) {
      const date = new Date(anomaly.detected_at).toLocaleDateString();
      if (!lookup[date]) {
        lookup[date] = [];
      }
      lookup[date].push(anomaly);
    }
    return lookup;
  }, [anomalies]);

  const chartData =
    data?.snapshots
      .slice()
      .reverse()
      .map((snapshot: PriceSnapshot) => {
        const date = new Date(snapshot.recorded_at).toLocaleDateString();
        const snapshotAnomalies = anomaliesByDate[date] || [];
        return {
          date,
          price: snapshot.price,
          pricePerSqm: snapshot.price_per_sqm,
          hasAnomaly: snapshotAnomalies.length > 0,
          anomalies: snapshotAnomalies,
        };
      }) || [];

  const TrendIcon =
    data?.trend === 'increasing' ? TrendingUp : data?.trend === 'decreasing' ? TrendingDown : Minus;

  const trendColor =
    data?.trend === 'increasing'
      ? 'text-success'
      : data?.trend === 'decreasing'
        ? 'text-destructive'
        : 'text-muted-foreground';

  if (loading) {
    return (
      <Card className={className}>
        <CardContent className="flex items-center justify-center h-64">
          <Loader2 className="h-8 w-8 animate-spin text-primary" aria-hidden="true" />
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className={className}>
        <CardContent className="flex flex-col items-center justify-center h-64 text-center">
          <AlertCircle className="h-8 w-8 text-destructive mb-2" aria-hidden="true" />
          <p className="text-destructive">{error}</p>
        </CardContent>
      </Card>
    );
  }

  if (!data || data.snapshots.length === 0) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle>{t('priceHistory.title')}</CardTitle>
          <CardDescription>{t('priceHistory.noData')}</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  const trendKey =
    data?.trend === 'increasing'
      ? 'increasing'
      : data?.trend === 'decreasing'
        ? 'decreasing'
        : 'stable';

  return (
    <Card className={className}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>{t('priceHistory.title')}</CardTitle>
            <CardDescription>
              {tInv('priceHistoryChart.snapshotsRecorded', { count: data.total })}
            </CardDescription>
          </div>
          <div className={`flex items-center gap-2 ${trendColor}`}>
            <TrendIcon className="h-5 w-5" aria-hidden="true" />
            <span className="font-medium capitalize">{t(`priceHistory.trend.${trendKey}`)}</span>
            {data.price_change_percent !== null && data.price_change_percent !== undefined && (
              <span className="text-sm">
                ({data.price_change_percent > 0 ? '+' : ''}
                {data.price_change_percent.toFixed(1)}%)
              </span>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {/* Anomaly Alert Banner */}
        {showAnomalies && anomalies.length > 0 && (
          <div className="mb-4 p-3 rounded-md bg-caution/10 dark:bg-caution/20 border border-caution/30 dark:border-caution">
            <div className="flex items-center gap-2 text-caution dark:text-caution">
              <AlertTriangle className="h-4 w-4" aria-hidden="true" />
              <span className="text-sm font-medium">
                {tInv('priceHistoryChart.anomaliesDetected', { count: anomalies.length })}
              </span>
            </div>
          </div>
        )}

        <div
          className="h-64"
          role="img"
          aria-label={t('priceHistory.chartLabel', {
            count: data.total,
            trend: t(`priceHistory.trend.${trendKey}`),
          })}
        >
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" tick={{ fontSize: 12 }} tickLine={false} />
              <YAxis
                tick={{ fontSize: 12 }}
                tickLine={false}
                tickFormatter={(value) => `$${(value / 1000).toFixed(0)}k`}
              />
              <Tooltip
                content={({ active, payload }) => {
                  if (active && payload && payload.length > 0) {
                    const data = payload[0].payload;
                    const hasAnomaly = data?.hasAnomaly;
                    const anomalies = data?.anomalies || [];
                    return (
                      <div className="bg-card p-2 rounded shadow-lg border border-border">
                        <p className="font-medium text-sm">{data.date}</p>
                        <p className="text-sm">
                          {tInv('priceHistoryChart.priceLabel', {
                            price: `$${data.price?.toLocaleString()}`,
                          })}
                        </p>
                        {data.pricePerSqm && (
                          <p className="text-xs text-muted">
                            {tInv('priceHistoryChart.pricePerSqmLabel', {
                              price: `$${data.pricePerSqm?.toLocaleString()}`,
                            })}
                          </p>
                        )}
                        {hasAnomaly && anomalies.length > 0 && (
                          <div className="mt-2 pt-2 border-t border-border">
                            <p className="text-xs font-medium text-caution dark:text-caution">
                              {t('priceHistory.anomalyCount', { count: anomalies.length })}
                            </p>
                            {anomalies.slice(0, 2).map((a: MarketAnomaly, i: number) => (
                              <div key={i} className="mt-1">
                                <AnomalyBadge
                                  severity={a.severity}
                                  type={a.anomaly_type}
                                  size="sm"
                                />
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    );
                  }
                  return null;
                }}
              />
              <Legend />
              <Line
                type="monotone"
                dataKey="price"
                stroke="hsl(var(--chart-1))"
                strokeWidth={2}
                dot={(props: { cx?: number; cy?: number; payload?: { hasAnomaly?: boolean } }) => {
                  const { cx = 0, cy = 0, payload } = props;
                  if (payload?.hasAnomaly) {
                    return (
                      <svg x={cx - 6} y={cy - 6} width={12} height={12} viewBox="0 0 12 12">
                        <circle cx={6} cy={6} r={5} fill="hsl(var(--chart-3))" stroke="hsl(var(--background))" strokeWidth={2} />
                      </svg>
                    );
                  }
                  // Return a small transparent dot for normal points
                  return (
                    <svg x={cx - 2} y={cy - 2} width={4} height={4} viewBox="0 0 4 4">
                      <circle cx={2} cy={2} r={2} fill="transparent" />
                    </svg>
                  );
                }}
                name={t('priceHistory.price')}
              />
              {chartData[0]?.pricePerSqm && (
                <Line
                  type="monotone"
                  dataKey="pricePerSqm"
                  stroke="hsl(var(--chart-2))"
                  strokeWidth={2}
                  dot={false}
                  name={t('priceHistory.pricePerSqm')}
                />
              )}
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Summary stats */}
        <div className="grid grid-cols-3 gap-4 mt-4 pt-4 border-t">
          <div>
            <p className="text-sm text-muted-foreground">{t('priceHistory.currentPrice')}</p>
            <p className="text-lg font-semibold">
              {data.current_price ? `$${data.current_price.toLocaleString()}` : 'N/A'}
            </p>
          </div>
          <div>
            <p className="text-sm text-muted-foreground">{t('priceHistory.firstRecorded')}</p>
            <p className="text-lg">
              {data.first_recorded ? new Date(data.first_recorded).toLocaleDateString() : 'N/A'}
            </p>
          </div>
          <div>
            <p className="text-sm text-muted-foreground">{t('priceHistory.priceChange')}</p>
            <p className={`text-lg font-semibold ${trendColor}`}>
              {data.price_change_percent !== null && data.price_change_percent !== undefined
                ? `${data.price_change_percent > 0 ? '+' : ''}${data.price_change_percent.toFixed(1)}%`
                : 'N/A'}
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
