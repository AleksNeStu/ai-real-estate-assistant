'use client';

import { useLocale, useTranslations } from 'next-intl';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  BarChart,
  Bar,
} from 'recharts';

import { formatCompactPrice, formatPrice } from '@/lib/format';

export interface ChartDataPoint {
  period: string;
  avgPrice: number;
  medianPrice: number;
  volume: number;
  /** The currency the prices of this period are in. */
  currency?: string;
}

interface MarketTrendsChartsProps {
  chartData: ChartDataPoint[];
}

/**
 * Charts for /market-trends. Renders two recharts visualizations
 * (line chart of average / median price over time, bar chart of
 * listing volume).
 *
 * Extracted into its own component so the page can dynamic-import it
 * with `ssr: false`, which keeps the recharts bundle (5+ MB) out of
 * the initial page payload.
 */
export function MarketTrendsCharts({ chartData }: MarketTrendsChartsProps) {
  const t = useTranslations('marketTrends.charts');
  const locale = useLocale();

  // The prices are in the currency of the listings they were computed from.
  const currency = chartData.find((point) => point.currency)?.currency;
  const axisPrice = (value: number): string => formatCompactPrice(value, currency, locale);
  const fullPrice = (value: number): string => formatPrice(value, currency, locale);

  return (
    <>
      <Card>
        <CardHeader>
          <CardTitle>{t('pricesTitle')}</CardTitle>
          <CardDescription>{t('pricesDescription')}</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="h-80" role="img" aria-label={t('pricesAria')}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="period" tick={{ fontSize: 12 }} />
                <YAxis
                  tick={{ fontSize: 12 }}
                  tickFormatter={(v) => axisPrice(v)}
                />
                <Tooltip formatter={(value: number) => [fullPrice(value)]} />
                <Legend />
                <Line
                  type="monotone"
                  dataKey="avgPrice"
                  stroke="hsl(var(--chart-1))"
                  strokeWidth={2}
                  name={t('averagePrice')}
                />
                <Line
                  type="monotone"
                  dataKey="medianPrice"
                  stroke="hsl(var(--chart-2))"
                  strokeWidth={2}
                  name={t('medianPrice')}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>{t('volumeTitle')}</CardTitle>
          <CardDescription>{t('volumeDescription')}</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="h-80" role="img" aria-label={t('volumeAria')}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="period" tick={{ fontSize: 12 }} />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip />
                <Legend />
                <Bar dataKey="volume" fill="hsl(var(--chart-4))" name={t('listings')} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>
    </>
  );
}
