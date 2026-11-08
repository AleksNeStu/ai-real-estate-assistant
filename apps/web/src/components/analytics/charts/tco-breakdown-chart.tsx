'use client';

import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import type { TooltipProps } from 'recharts';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import type { TCOResult } from '@/lib/types';
import { useTranslations } from 'next-intl';

interface TCOBreakdownChartProps {
  tcoResult: TCOResult;
  className?: string;
  title?: string;
  description?: string;
}

const COLORS = [
  'hsl(var(--chart-1))', // blue - mortgage
  'hsl(var(--chart-2))', // green - property tax
  'hsl(var(--chart-3))', // amber - insurance
  'hsl(var(--chart-4))', // violet - HOA
  'hsl(var(--chart-5))', // cyan - utilities
  'hsl(var(--chart-6))', // pink - internet
  'hsl(var(--chart-7))', // lime - parking
  'hsl(var(--chart-8))', // red - maintenance
];

function formatCurrency(value: number) {
  return `$${value.toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
}

export function TCOBreakdownChart({
  tcoResult,
  className,
  title,
  description,
}: TCOBreakdownChartProps) {
  const t = useTranslations('mortgage');
  const chartTitle = title ?? t('charts.breakdown.title');
  const chartDescription = description ?? t('charts.breakdown.description');
  const CATEGORY_LABELS: Record<string, string> = {
    mortgage: t('charts.breakdown.categories.mortgage'),
    property_tax: t('charts.breakdown.categories.propertyTax'),
    insurance: t('charts.breakdown.categories.insurance'),
    hoa: t('charts.breakdown.categories.hoa'),
    utilities: t('charts.breakdown.categories.utilities'),
    internet: t('charts.breakdown.categories.internet'),
    parking: t('charts.breakdown.categories.parking'),
    maintenance: t('charts.breakdown.categories.maintenance'),
  };
  // Build chart data from TCO result
  const chartData = [
    { name: CATEGORY_LABELS.mortgage, value: tcoResult.monthly_mortgage, key: 'mortgage' },
    {
      name: CATEGORY_LABELS.property_tax,
      value: tcoResult.monthly_property_tax,
      key: 'property_tax',
    },
    { name: CATEGORY_LABELS.insurance, value: tcoResult.monthly_insurance, key: 'insurance' },
    { name: CATEGORY_LABELS.hoa, value: tcoResult.monthly_hoa, key: 'hoa' },
    { name: CATEGORY_LABELS.utilities, value: tcoResult.monthly_utilities, key: 'utilities' },
    { name: CATEGORY_LABELS.internet, value: tcoResult.monthly_internet, key: 'internet' },
    { name: CATEGORY_LABELS.parking, value: tcoResult.monthly_parking, key: 'parking' },
    { name: CATEGORY_LABELS.maintenance, value: tcoResult.monthly_maintenance, key: 'maintenance' },
  ].filter((item) => item.value > 0); // Only show non-zero categories

  const renderLabel = ({ name, percent }: { name: string; percent: number }) => {
    if (percent < 0.05) return null;
    return `${name} (${(percent * 100).toFixed(0)}%)`;
  };

  const renderTooltip = ({ active, payload }: TooltipProps<number, string>) => {
    if (active && payload && payload.length) {
      const data = payload[0];
      if (!data || data.value === undefined) return null;
      const percent = (data.value / tcoResult.monthly_tco) * 100;
      return (
        <div className="bg-background border rounded-lg p-3 shadow-lg">
          <p className="font-medium">{data.name}</p>
          <p className="text-sm text-muted-foreground">
            {t('charts.breakdown.perMonth', { value: formatCurrency(data.value) })}
          </p>
          <p className="text-xs text-muted-foreground">
            {t('charts.breakdown.percentOfTotal', { percent: percent.toFixed(1) })}
          </p>
        </div>
      );
    }
    return null;
  };

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle>{chartTitle}</CardTitle>
        <CardDescription>{chartDescription}</CardDescription>
      </CardHeader>
      <CardContent>
        <div
          className="h-64"
          role="img"
          aria-label={t('charts.breakdown.ariaLabel', {
            categories: chartData.map((d) => `${d.name} ${formatCurrency(d.value)}`).join(', '),
          })}
        >
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={chartData}
                cx="50%"
                cy="50%"
                labelLine={true}
                label={renderLabel}
                outerRadius={90}
                dataKey="value"
              >
                {chartData.map((entry, index) => (
                  <Cell key={`cell-${entry.key}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip content={renderTooltip} />
              <Legend formatter={(value: string) => <span className="text-sm">{value}</span>} />
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* Cost Category Summary */}
        <div className="grid grid-cols-3 gap-4 mt-4 pt-4 border-t">
          <div className="text-center">
            <p className="text-xs text-muted-foreground">{t('charts.breakdown.fixedCosts')}</p>
            <p className="text-sm font-semibold">
              {formatCurrency(
                tcoResult.monthly_mortgage +
                  tcoResult.monthly_property_tax +
                  tcoResult.monthly_insurance +
                  tcoResult.monthly_hoa
              )}
            </p>
          </div>
          <div className="text-center">
            <p className="text-xs text-muted-foreground">{t('charts.breakdown.variableCosts')}</p>
            <p className="text-sm font-semibold">
              {formatCurrency(tcoResult.monthly_utilities + tcoResult.monthly_maintenance)}
            </p>
          </div>
          <div className="text-center">
            <p className="text-xs text-muted-foreground">{t('charts.breakdown.discretionary')}</p>
            <p className="text-sm font-semibold">
              {formatCurrency(tcoResult.monthly_internet + tcoResult.monthly_parking)}
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
