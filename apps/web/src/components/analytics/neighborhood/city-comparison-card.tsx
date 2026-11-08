'use client';

import React from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';
import type { NeighborhoodQualityResult } from '@/lib/types';
import { useTranslations } from 'next-intl';

interface CityComparisonCardProps {
  result: NeighborhoodQualityResult;
  className?: string;
}

/**
 * CityComparisonCard Component
 *
 * Displays how the neighborhood compares to the city average including:
 * - Percentile rank (0-100)
 * - Better/worse than average factors
 * - Visual comparison chart
 */
export function CityComparisonCard({ result, className = '' }: CityComparisonCardProps) {
  const t = useTranslations('neighborhood');
  const comparison = result.city_comparison;

  if (!comparison) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle>{t('cityComparison.title')}</CardTitle>
          <CardDescription>{t('cityComparison.description')}</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center py-8 text-muted-foreground">
            <p className="text-sm">{t('cityComparison.dataNotAvailable')}</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  const getPercentileColor = (percentile: number): string => {
    if (percentile >= 80) return 'text-success';
    if (percentile >= 60) return 'text-chart-7';
    if (percentile >= 40) return 'text-warning';
    if (percentile >= 20) return 'text-caution';
    return 'text-destructive';
  };

  const getPercentileLabel = (percentile: number): string => {
    if (percentile >= 90) return t('cityComparison.outstanding');
    if (percentile >= 75) return t('cityComparison.excellent');
    if (percentile >= 60) return t('cityComparison.aboveAverage');
    if (percentile >= 40) return t('cityComparison.average');
    if (percentile >= 25) return t('cityComparison.belowAverage');
    return t('cityComparison.poor');
  };

  // Prepare chart data
  const chartData = [
    {
      name: t('cityComparison.thisArea'),
      score: result.overall_score,
      fill: 'hsl(var(--chart-1))',
    },
    {
      name: t('cityComparison.cityAvg'),
      score: comparison.city_average,
      fill: 'hsl(var(--muted-foreground))',
    },
  ];

  // Factor labels mapping
  const factorLabels: Record<string, string> = {
    safety_score: t('components.safety'),
    schools_score: t('components.schools'),
    amenities_score: t('components.amenities'),
    walkability_score: t('components.walkability'),
    green_space_score: t('components.greenSpace'),
    air_quality_score: t('components.airQuality'),
    noise_level_score: t('components.noiseLevel'),
    public_transport_score: t('components.publicTransport'),
  };

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle>{t('cityComparison.title')}</CardTitle>
        <CardDescription>
          How this neighborhood compares to {result.city || 'the city'} average
        </CardDescription>
      </CardHeader>
      <CardContent>
        {/* Percentile Rank */}
        <div className="flex flex-col sm:flex-row items-center gap-6 mb-6">
          {/* Circular percentile indicator */}
          <div className="flex-shrink-0">
            <div className="relative w-32 h-32">
              <svg
                className="w-full h-full transform -rotate-90"
                role="img"
                aria-label={t('cityComparison.percentileLabel', { value: comparison.percentile })}
              >
                <circle
                  cx="64"
                  cy="64"
                  r="56"
                  stroke="currentColor"
                  strokeWidth="12"
                  fill="none"
                  className="text-muted-foreground"
                />
                <circle
                  cx="64"
                  cy="64"
                  r="56"
                  stroke="currentColor"
                  strokeWidth="12"
                  fill="none"
                  strokeDasharray={`${(comparison.percentile / 100) * 351.86} 351.86`}
                  className={getPercentileColor(comparison.percentile)}
                  strokeLinecap="round"
                />
              </svg>
              <div className="absolute inset-0 flex flex-col items-center justify-center">
                <span className={`text-3xl font-bold ${getPercentileColor(comparison.percentile)}`}>
                  {comparison.percentile}
                </span>
                <span className="text-xs text-muted-foreground">{t('cityComparison.percentile')}</span>
              </div>
            </div>
          </div>

          {/* Percentile info */}
          <div className="flex-1 text-center sm:text-left">
            <h4 className="text-lg font-semibold mb-1">
              {getPercentileLabel(comparison.percentile)}
            </h4>
            <p className="text-sm text-muted-foreground mb-2">
              This neighborhood scores higher than{' '}
              <span className="font-semibold">{comparison.percentile}%</span> of areas in{' '}
              {result.city || 'the city'}
            </p>
            <div className="flex items-center gap-2 justify-center sm:justify-start">
              <span className="text-sm text-muted-foreground">{t('cityComparison.cityAverage')}</span>
              <span className="text-lg font-bold text-muted-foreground">
                {comparison.city_average.toFixed(1)}
              </span>
            </div>
          </div>
        </div>

        {/* Comparison Chart */}
        <div className="mb-6">
          <h5 className="text-sm font-medium mb-3">{t('cityComparison.scoreComparison')}</h5>
          <div
            className="h-40"
            role="img"
            aria-label={t('cityComparison.scoreComparisonLabel', {
              area: result.overall_score.toFixed(1),
              average: comparison.city_average.toFixed(1),
            })}
          >
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} layout="vertical" barSize={40}>
                <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                <XAxis type="number" domain={[0, 100]} tick={{ fontSize: 11 }} />
                <YAxis
                  type="category"
                  dataKey="name"
                  tick={{ fontSize: 12 }}
                  width={80}
                  tickLine={false}
                />
                <Tooltip
                  formatter={(value: number) => [value.toFixed(1), t('cityComparison.score')]}
                  contentStyle={{ fontSize: '12px' }}
                />
                <Bar dataKey="score" radius={[4, 4, 4, 4]}>
                  {chartData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.fill} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Better/Worse factors */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Better than average */}
          {comparison.better_than.length > 0 && (
            <div className="rounded-lg border border-success/30 bg-success/10 p-4">
              <div className="flex items-center gap-2 mb-3">
                <TrendingUp className="h-4 w-4 text-success" aria-hidden="true" />
                <h5 className="text-sm font-semibold text-success">{t('cityComparison.betterThanAverage')}</h5>
              </div>
              <ul className="space-y-1">
                {comparison.better_than.map((factor) => {
                  const factorKey = `${factor.toLowerCase().replace(' ', '_')}_score`;
                  const score = result[factorKey as keyof NeighborhoodQualityResult] as number;
                  return (
                    <li key={factor} className="flex items-center justify-between text-xs">
                      <span className="text-success">{factorLabels[factorKey] || factor}</span>
                      <span className="font-semibold text-success">{score?.toFixed(1)}</span>
                    </li>
                  );
                })}
              </ul>
            </div>
          )}

          {/* Worse than average */}
          {comparison.worse_than.length > 0 && (
            <div className="rounded-lg border border-caution/30 bg-caution/10 p-4">
              <div className="flex items-center gap-2 mb-3">
                <TrendingDown className="h-4 w-4 text-caution" aria-hidden="true" />
                <h5 className="text-sm font-semibold text-caution">{t('cityComparison.belowAverage')}</h5>
              </div>
              <ul className="space-y-1">
                {comparison.worse_than.map((factor) => {
                  const factorKey = `${factor.toLowerCase().replace(' ', '_')}_score`;
                  const score = result[factorKey as keyof NeighborhoodQualityResult] as number;
                  return (
                    <li key={factor} className="flex items-center justify-between text-xs">
                      <span className="text-caution">{factorLabels[factorKey] || factor}</span>
                      <span className="font-semibold text-caution">{score?.toFixed(1)}</span>
                    </li>
                  );
                })}
              </ul>
            </div>
          )}

          {/* All equal case */}
          {comparison.better_than.length === 0 && comparison.worse_than.length === 0 && (
            <div className="md:col-span-2 rounded-lg border border-border bg-muted p-4">
              <div className="flex items-center gap-2">
                <Minus className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
                <p className="text-sm text-muted-foreground">
                  This neighborhood scores close to the city average across all factors.
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Overall diff badge */}
        <div className="mt-4 pt-4 border-t flex items-center justify-center">
          <div
            className={`inline-flex items-center gap-2 px-4 py-2 rounded-full ${
              result.overall_score > comparison.city_average
                ? 'bg-success/20 text-success'
                : result.overall_score < comparison.city_average
                  ? 'bg-caution/20 text-caution'
                  : 'bg-muted text-foreground'
            }`}
          >
            {result.overall_score > comparison.city_average ? (
              <TrendingUp className="h-4 w-4" aria-hidden="true" />
            ) : result.overall_score < comparison.city_average ? (
              <TrendingDown className="h-4 w-4" aria-hidden="true" />
            ) : (
              <Minus className="h-4 w-4" aria-hidden="true" />
            )}
            <span className="text-sm font-medium">
              {result.overall_score > comparison.city_average
                ? t('cityComparison.pointsAbove', {
                    count: (result.overall_score - comparison.city_average).toFixed(1),
                  })
                : result.overall_score < comparison.city_average
                  ? t('cityComparison.pointsBelow', {
                      count: (comparison.city_average - result.overall_score).toFixed(1),
                    })
                  : t('cityComparison.equalToAverage')}
            </span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
