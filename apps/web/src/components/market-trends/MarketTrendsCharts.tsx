'use client';

import { useLocale, useTranslations } from 'next-intl';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

import { ChartFrame } from '@/components/ui/chart-frame';
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
  /** The mono note on the frame: the period, the scope, the unit. */
  caption?: string;
  /** The height the price curve is drawn in. */
  priceHeight?: number;
  /** The height the volume bars are drawn in. */
  volumeHeight?: number;
}

/**
 * The price curve and the listing volume.
 *
 * Both charts sit in a chart frame: the title above, the note beside it in
 * mono, and the space for the chart held open underneath - so the page does
 * not move when the bundle arrives.
 *
 * The curve is drawn the way the prototype draws it: the median in ink, the
 * average in the muted voice, the grid as hairlines. The charts are the only
 * thing on the page that carries a colour, and they do not carry one.
 */
export function MarketTrendsCharts({
  chartData,
  caption,
  priceHeight = 280,
  volumeHeight = 200,
}: MarketTrendsChartsProps) {
  const t = useTranslations('marketTrends.charts');
  const locale = useLocale();

  // The prices are in the currency of the listings they were computed from.
  const currency = chartData.find((point) => point.currency)?.currency;
  const axisPrice = (value: number): string => formatCompactPrice(value, currency, locale);
  const fullPrice = (value: number): string => formatPrice(value, currency, locale);

  return (
    <>
      <ChartFrame title={t('pricesTitle')} caption={caption} height={priceHeight}>
        <div
          className="w-full"
          style={{ height: priceHeight }}
          role="img"
          aria-label={t('pricesAria')}
        >
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData}>
              <CartesianGrid stroke="hsl(var(--border))" vertical={false} />
              <XAxis
                dataKey="period"
                tick={{ fontSize: 11, fill: 'hsl(var(--muted-foreground))' }}
                axisLine={{ stroke: 'hsl(var(--border))' }}
                tickLine={false}
              />
              <YAxis
                tick={{ fontSize: 11, fill: 'hsl(var(--muted-foreground))' }}
                tickFormatter={(v) => axisPrice(v)}
                axisLine={false}
                tickLine={false}
                width={56}
              />
              <Tooltip
                formatter={(value: number) => [fullPrice(value)]}
                contentStyle={{
                  background: 'hsl(var(--background))',
                  border: '1px solid hsl(var(--border))',
                  borderRadius: 6,
                  fontSize: 12,
                }}
              />
              <Line
                type="monotone"
                dataKey="medianPrice"
                stroke="hsl(var(--foreground))"
                strokeWidth={2}
                dot={false}
                name={t('medianPrice')}
              />
              <Line
                type="monotone"
                dataKey="avgPrice"
                stroke="hsl(var(--muted-foreground))"
                strokeWidth={1.5}
                strokeOpacity={0.7}
                dot={false}
                name={t('averagePrice')}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </ChartFrame>

      <ChartFrame title={t('volumeTitle')} caption={caption} height={volumeHeight}>
        <div
          className="w-full"
          style={{ height: volumeHeight }}
          role="img"
          aria-label={t('volumeAria')}
        >
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData}>
              <CartesianGrid stroke="hsl(var(--border))" vertical={false} />
              <XAxis
                dataKey="period"
                tick={{ fontSize: 11, fill: 'hsl(var(--muted-foreground))' }}
                axisLine={{ stroke: 'hsl(var(--border))' }}
                tickLine={false}
              />
              <YAxis
                tick={{ fontSize: 11, fill: 'hsl(var(--muted-foreground))' }}
                axisLine={false}
                tickLine={false}
                width={40}
              />
              <Tooltip
                contentStyle={{
                  background: 'hsl(var(--background))',
                  border: '1px solid hsl(var(--border))',
                  borderRadius: 6,
                  fontSize: 12,
                }}
              />
              <Bar dataKey="volume" fill="hsl(var(--muted-foreground))" name={t('listings')} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </ChartFrame>
    </>
  );
}
