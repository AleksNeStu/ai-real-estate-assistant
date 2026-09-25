'use client';

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
  return (
    <>
      <Card>
        <CardHeader>
          <CardTitle>Average and Median Prices</CardTitle>
          <CardDescription>Price trends over the selected period</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="h-80">
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
                  stroke="#1f77b4"
                  strokeWidth={2}
                  name="Average Price"
                />
                <Line
                  type="monotone"
                  dataKey="medianPrice"
                  stroke="#2ca02c"
                  strokeWidth={2}
                  name="Median Price"
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Listing Volume</CardTitle>
          <CardDescription>Number of listings per period</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="period" tick={{ fontSize: 12 }} />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip />
                <Legend />
                <Bar dataKey="volume" fill="#8884d8" name="Listings" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>
    </>
  );
}