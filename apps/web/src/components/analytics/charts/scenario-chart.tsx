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
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import type { AppreciationScenario } from '@/lib/types';
import { useTranslations } from 'next-intl';

interface ScenarioChartProps {
  scenarios: AppreciationScenario[];
  initialPrice: number;
  className?: string;
}

export function ScenarioChart({ scenarios, initialPrice, className }: ScenarioChartProps) {
  const t = useTranslations('investment');
  const SCENARIO_LABELS: Record<string, string> = {
    Pessimistic: t('charts.scenario.pessimistic'),
    Realistic: t('charts.scenario.realistic'),
    Optimistic: t('charts.scenario.optimistic'),
  };
  // Get all years from the first scenario
  const years = scenarios.length > 0 ? Object.keys(scenarios[0].projected_values).map(Number) : [];

  const chartData = years.map((year) => {
    const dataPoint: Record<string, number | string> = {
      year: t('charts.scenario.year', { year }),
    };
    scenarios.forEach((scenario) => {
      dataPoint[scenario.name] = scenario.projected_values[year] || initialPrice;
    });
    return dataPoint;
  });

  const scenarioColors: Record<string, string> = {
    Pessimistic: 'hsl(var(--chart-8))',
    Realistic: 'hsl(var(--chart-1))',
    Optimistic: 'hsl(var(--chart-2))',
  };

  const formatCurrency = (value: number) => {
    if (value >= 1000000) {
      return `$${(value / 1000000).toFixed(1)}M`;
    }
    return `$${(value / 1000).toFixed(0)}K`;
  };

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle>{t('charts.scenario.title')}</CardTitle>
        <CardDescription>{t('charts.scenario.description')}</CardDescription>
      </CardHeader>
      <CardContent>
        <div
          className="h-64"
          role="img"
          aria-label={t('charts.scenario.ariaLabel')}
        >
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="year" tick={{ fontSize: 11 }} tickLine={false} />
              <YAxis
                tick={{ fontSize: 11 }}
                tickLine={false}
                tickFormatter={formatCurrency}
                domain={['auto', 'auto']}
              />
              <Tooltip
                formatter={(value: number) => [
                  `$${value.toLocaleString(undefined, { maximumFractionDigits: 0 })}`,
                  t('charts.scenario.value'),
                ]}
              />
              <Legend />
              {scenarios.map((scenario) => (
                <Line
                  key={scenario.name}
                  type="monotone"
                  dataKey={scenario.name}
                  stroke={scenarioColors[scenario.name] || 'hsl(var(--chart-4))'}
                  strokeWidth={2}
                  dot={false}
                  name={`${SCENARIO_LABELS[scenario.name] ?? scenario.name} (${scenario.annual_rate > 0 ? '+' : ''}${scenario.annual_rate}%)`}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Scenario Summary */}
        <div className="grid grid-cols-3 gap-4 mt-4 pt-4 border-t">
          {scenarios.map((scenario) => (
            <div key={scenario.name} className="text-center">
              <p className="text-sm text-muted-foreground">
                {SCENARIO_LABELS[scenario.name] ?? scenario.name}
              </p>
              <p
                className={`text-sm font-medium ${scenario.annual_rate >= 0 ? 'text-success' : 'text-destructive'}`}
              >
                {t('charts.scenario.perYear', {
                  rate: `${scenario.annual_rate > 0 ? '+' : ''}${scenario.annual_rate}`,
                })}
              </p>
              <p className="text-xs text-muted-foreground mt-1">
                {t('charts.scenario.total')}{' '}
                {scenario.total_appreciation_percent > 0 ? '+' : ''}
                {scenario.total_appreciation_percent.toFixed(1)}%
              </p>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
