'use client';

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import type { YearlyCashFlow } from '@/lib/types';
import { useTranslations } from 'next-intl';

interface CashFlowChartProps {
  data: YearlyCashFlow[];
  title?: string;
  description?: string;
  className?: string;
}

export function CashFlowChart({
  data,
  title,
  description,
  className,
}: CashFlowChartProps) {
  const t = useTranslations('investment');
  const chartTitle = title ?? t('charts.cashFlow.title');
  const chartDescription = description ?? t('charts.cashFlow.description');
  const chartData = data.map((item) => ({
    year: t('charts.cashFlow.year', { year: item.year }),
    cashFlow: item.cash_flow,
    cumulativeCashFlow: item.cumulative_cash_flow,
    equity: item.equity,
    propertyValue: item.property_value,
  }));

  const formatCurrency = (value: number) => {
    if (value >= 1000000) {
      return `$${(value / 1000000).toFixed(1)}M`;
    }
    return `$${(value / 1000).toFixed(0)}K`;
  };

  const totalCashFlow = data.length > 0 ? data[data.length - 1].cumulative_cash_flow : 0;
  const finalEquity = data.length > 0 ? data[data.length - 1].equity : 0;

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle>{chartTitle}</CardTitle>
        <CardDescription>{chartDescription}</CardDescription>
      </CardHeader>
      <CardContent>
        <div
          className="h-72"
          role="img"
          aria-label={t('charts.cashFlow.ariaLabel')}
        >
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="year" tick={{ fontSize: 11 }} tickLine={false} />
              <YAxis tick={{ fontSize: 11 }} tickLine={false} tickFormatter={formatCurrency} />
              <Tooltip
                formatter={(value: number, name: string) => [
                  `$${value.toLocaleString(undefined, { maximumFractionDigits: 0 })}`,
                  name === 'cashFlow'
                    ? t('charts.cashFlow.annualCashFlow')
                    : name === 'cumulativeCashFlow'
                      ? t('charts.cashFlow.cumulativeCashFlow')
                      : name === 'equity'
                        ? t('charts.cashFlow.equity')
                        : t('charts.cashFlow.propertyValue'),
                ]}
              />
              <Legend />
              <Area
                type="monotone"
                dataKey="cumulativeCashFlow"
                stackId="1"
                stroke="hsl(var(--chart-2))"
                fill="hsl(var(--chart-2))"
                fillOpacity={0.3}
                name={t('charts.cashFlow.cumulativeCashFlow')}
              />
              <Area
                type="monotone"
                dataKey="equity"
                stackId="2"
                stroke="hsl(var(--chart-1))"
                fill="hsl(var(--chart-1))"
                fillOpacity={0.3}
                name={t('charts.cashFlow.equity')}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Summary */}
        <div className="grid grid-cols-2 gap-4 mt-4 pt-4 border-t">
          <div>
            <p className="text-sm text-muted-foreground">{t('charts.cashFlow.totalCashFlow')}</p>
            <p
              className={`text-lg font-semibold ${totalCashFlow >= 0 ? 'text-success' : 'text-destructive'}`}
            >
              ${totalCashFlow.toLocaleString(undefined, { maximumFractionDigits: 0 })}
            </p>
          </div>
          <div>
            <p className="text-sm text-muted-foreground">{t('charts.cashFlow.finalEquity')}</p>
            <p className="text-lg font-semibold text-info">
              ${finalEquity.toLocaleString(undefined, { maximumFractionDigits: 0 })}
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
