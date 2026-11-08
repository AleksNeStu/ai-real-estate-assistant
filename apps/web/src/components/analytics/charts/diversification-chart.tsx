'use client';

import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import type { PortfolioDiversification } from '@/lib/types';
import { useTranslations } from 'next-intl';

interface DiversificationChartProps {
  diversification: PortfolioDiversification;
  className?: string;
}

const COLORS = [
  'hsl(var(--chart-1))',
  'hsl(var(--chart-2))',
  'hsl(var(--chart-3))',
  'hsl(var(--chart-8))',
  'hsl(var(--chart-4))',
  'hsl(var(--chart-6))',
  'hsl(var(--chart-5))',
  'hsl(var(--chart-7))',
];

export function DiversificationChart({ diversification, className }: DiversificationChartProps) {
  const t = useTranslations('investment');
  // Convert distributions to chart data
  const cityData = Object.entries(diversification.city_distribution).map(
    ([name, value], index) => ({
      name,
      value,
      fill: COLORS[index % COLORS.length],
    })
  );

  const typeData = Object.entries(diversification.type_distribution).map(
    ([name, value], index) => ({
      name,
      value,
      fill: COLORS[index % COLORS.length],
    })
  );

  const renderLabel = ({ name, percent }: { name: string; percent: number }) => {
    if (percent < 0.05) return null;
    return `${name} (${(percent * 100).toFixed(0)}%)`;
  };

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle>{t('charts.diversification.title')}</CardTitle>
        <CardDescription>{t('charts.diversification.description')}</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="grid md:grid-cols-2 gap-6">
          {/* Geographic Distribution */}
          <div>
            <h4 className="text-sm font-medium mb-2 text-center">{t('charts.diversification.byCity')}</h4>
            <div
              className="h-48"
              role="img"
              aria-label={t('charts.diversification.geographicAria')}
            >
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={cityData}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={renderLabel}
                    outerRadius={70}
                    dataKey="value"
                  >
                    {cityData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.fill} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(value: number) => [`$${value.toLocaleString()}`, t('charts.diversification.value')]} />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="text-center mt-2">
              <p className="text-sm text-muted-foreground">{t('charts.diversification.geographicScore')}</p>
              <p className="text-lg font-semibold">{diversification.geographic_score}/100</p>
            </div>
          </div>

          {/* Property Type Distribution */}
          <div>
            <h4 className="text-sm font-medium mb-2 text-center">{t('charts.diversification.byPropertyType')}</h4>
            <div
              className="h-48"
              role="img"
              aria-label={t('charts.diversification.typeAria')}
            >
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={typeData}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={renderLabel}
                    outerRadius={70}
                    dataKey="value"
                  >
                    {typeData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.fill} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(value: number) => [`$${value.toLocaleString()}`, t('charts.diversification.value')]} />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="text-center mt-2">
              <p className="text-sm text-muted-foreground">{t('charts.diversification.typeScore')}</p>
              <p className="text-lg font-semibold">{diversification.property_type_score}/100</p>
            </div>
          </div>
        </div>

        {/* Risk Summary */}
        <div className="grid grid-cols-2 gap-4 mt-4 pt-4 border-t">
          <div className="text-center">
            <p className="text-sm text-muted-foreground">{t('charts.diversification.concentrationRisk')}</p>
            <p
              className={`text-lg font-semibold ${
                diversification.concentration_risk > 70
                  ? 'text-destructive'
                  : diversification.concentration_risk > 40
                    ? 'text-warning'
                    : 'text-success'
              }`}
            >
              {diversification.concentration_risk.toFixed(0)}%
            </p>
          </div>
          <div className="text-center">
            <p className="text-sm text-muted-foreground">{t('charts.diversification.largestHolding')}</p>
            <p className="text-lg font-semibold">
              {diversification.largest_holding_percent.toFixed(1)}%
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
