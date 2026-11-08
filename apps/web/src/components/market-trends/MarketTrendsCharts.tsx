'use client';

import { useTranslations } from 'next-intl';
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

export interface ChartDataPoint {
  period: string;
  avgPrice: number;
  medianPrice: number;
  volume: number;
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
                  tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`}
                />
                <Tooltip formatter={(value: number) => [`$${value.toLocaleString()}`]} />
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
