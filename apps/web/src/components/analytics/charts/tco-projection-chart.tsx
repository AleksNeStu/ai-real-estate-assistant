'use client';

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
import type { TooltipProps } from 'recharts';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import type { TCOProjection } from '@/lib/types';
import { useTranslations } from 'next-intl';

interface TCOProjectionChartProps {
  projections: TCOProjection[];
  className?: string;
  highlightYears?: number[];
}

function formatCurrency(value: number) {
  if (value >= 1000000) {
    return `$${(value / 1000000).toFixed(1)}M`;
  }
  return `$${(value / 1000).toFixed(0)}K`;
}

export function TCOProjectionChart({
  projections,
  className,
  highlightYears = [5, 10, 20],
}: TCOProjectionChartProps) {
  const t = useTranslations('mortgage');
  const chartData = projections.map((proj) => ({
    year: proj.year,
    cumulative_cost: proj.cumulative_cost,
    cumulative_equity: proj.cumulative_equity,
    property_value: proj.property_value_estimate,
    loan_balance: proj.loan_balance,
    annual_cost: proj.annual_cost,
  }));

  // Find projection points for highlighted years
  const highlightPoints = projections.filter((p) => highlightYears.includes(p.year));

  const renderTooltip = ({ active, payload, label }: TooltipProps<number, string>) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-background border rounded-lg p-3 shadow-lg">
          <p className="font-medium mb-2">{t('charts.projection.year', { year: label })}</p>
          {payload.map((entry, index) => (
            <p key={index} className="text-sm" style={{ color: entry.color }}>
              {entry.name}: {entry.value !== undefined ? formatCurrency(entry.value) : 'N/A'}
            </p>
          ))}
        </div>
      );
    }
    return null;
  };

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle>{t('charts.projection.title')}</CardTitle>
        <CardDescription>{t('charts.projection.description')}</CardDescription>
      </CardHeader>
      <CardContent>
        <div
          className="h-72"
          role="img"
          aria-label={t('charts.projection.ariaLabel')}
        >
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
              <XAxis
                dataKey="year"
                tick={{ fontSize: 11 }}
                tickLine={false}
                label={{ value: t('charts.projection.years'), position: 'bottom', fontSize: 12 }}
              />
              <YAxis
                tick={{ fontSize: 11 }}
                tickLine={false}
                tickFormatter={formatCurrency}
                domain={['auto', 'auto']}
              />
              <Tooltip content={renderTooltip} />
              <Legend />
              <Line
                type="monotone"
                dataKey="cumulative_cost"
                stroke="hsl(var(--chart-8))"
                strokeWidth={2}
                dot={false}
                name={t('charts.projection.totalCost')}
              />
              <Line
                type="monotone"
                dataKey="cumulative_equity"
                stroke="hsl(var(--chart-2))"
                strokeWidth={2}
                dot={false}
                name={t('charts.projection.equityBuilt')}
              />
              <Line
                type="monotone"
                dataKey="property_value"
                stroke="hsl(var(--chart-1))"
                strokeWidth={2}
                dot={false}
                name={t('charts.projection.propertyValue')}
              />
              <Line
                type="monotone"
                dataKey="loan_balance"
                stroke="hsl(var(--chart-3))"
                strokeWidth={2}
                dot={false}
                name={t('charts.projection.loanBalance')}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Key Milestones */}
        <div className="grid grid-cols-3 gap-4 mt-4 pt-4 border-t">
          {highlightPoints.map((point) => (
            <div key={point.year} className="text-center p-2 bg-muted/50 rounded">
              <p className="text-sm font-medium">
                {t('charts.projection.year', { year: point.year })}
              </p>
              <div className="mt-1 space-y-1">
                <p className="text-xs text-muted-foreground">
                  {`${t('charts.projection.cost')} ${formatCurrency(point.cumulative_cost)}`}
                </p>
                <p className="text-xs text-muted-foreground">
                  {`${t('charts.projection.equity')} ${formatCurrency(point.cumulative_equity)}`}
                </p>
                <p className="text-xs text-muted-foreground">
                  {`${t('charts.projection.value')} ${formatCurrency(point.property_value_estimate)}`}
                </p>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
