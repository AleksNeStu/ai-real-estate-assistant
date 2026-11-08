'use client';

import React from 'react';
import { useTranslations } from 'next-intl';
import type { NeighborhoodQualityResult } from '@/lib/types';
import {
  Shield,
  GraduationCap,
  ShoppingBag,
  Footprints,
  Trees,
  Wind,
  Volume2,
  Bus,
} from 'lucide-react';

interface FactorBreakdownProps {
  result: NeighborhoodQualityResult;
  compact?: boolean;
  className?: string;
}

interface FactorConfig {
  key: keyof NeighborhoodQualityResult;
  label: string;
  icon: React.ReactNode;
  weight: string;
  description: string;
  color: string;
  bgColor: string;
}

/**
 * FactorBreakdown Component
 *
 * Displays a grid of all 8 neighborhood quality factors with their scores,
 * weights, and confidence indicators.
 *
 * Shows:
 * - Core factors (60%): Safety, Schools, Amenities, Walkability, Green Space
 * - New factors (40%): Air Quality, Noise Level, Public Transport
 */
export function FactorBreakdown({ result, compact = false, className = '' }: FactorBreakdownProps) {
  const t = useTranslations('neighborhood');
  const factorConfigs: FactorConfig[] = [
    {
      key: 'safety_score',
      label: t('factorBreakdown.factors.safety.label'),
      icon: <Shield className="h-4 w-4" aria-hidden="true" />,
      weight: '15%',
      description: t('factorBreakdown.factors.safety.description'),
      color: 'text-chart-1',
      bgColor: 'bg-chart-1/10',
    },
    {
      key: 'schools_score',
      label: t('factorBreakdown.factors.schools.label'),
      icon: <GraduationCap className="h-4 w-4" aria-hidden="true" />,
      weight: '15%',
      description: t('factorBreakdown.factors.schools.description'),
      color: 'text-chart-4',
      bgColor: 'bg-chart-4/10',
    },
    {
      key: 'amenities_score',
      label: t('factorBreakdown.factors.amenities.label'),
      icon: <ShoppingBag className="h-4 w-4" aria-hidden="true" />,
      weight: '15%',
      description: t('factorBreakdown.factors.amenities.description'),
      color: 'text-chart-6',
      bgColor: 'bg-chart-6/10',
    },
    {
      key: 'walkability_score',
      label: t('factorBreakdown.factors.walkability.label'),
      icon: <Footprints className="h-4 w-4" aria-hidden="true" />,
      weight: '15%',
      description: t('factorBreakdown.factors.walkability.description'),
      color: 'text-chart-2',
      bgColor: 'bg-chart-2/10',
    },
    {
      key: 'green_space_score',
      label: t('factorBreakdown.factors.greenSpace.label'),
      icon: <Trees className="h-4 w-4" aria-hidden="true" />,
      weight: '10%',
      description: t('factorBreakdown.factors.greenSpace.description'),
      color: 'text-chart-7',
      bgColor: 'bg-chart-7/10',
    },
    {
      key: 'air_quality_score',
      label: t('factorBreakdown.factors.airQuality.label'),
      icon: <Wind className="h-4 w-4" aria-hidden="true" />,
      weight: '10%',
      description: t('factorBreakdown.factors.airQuality.description'),
      color: 'text-chart-5',
      bgColor: 'bg-chart-5/10',
    },
    {
      key: 'noise_level_score',
      label: t('factorBreakdown.factors.noiseLevel.label'),
      icon: <Volume2 className="h-4 w-4" aria-hidden="true" />,
      weight: '10%',
      description: t('factorBreakdown.factors.noiseLevel.description'),
      color: 'text-chart-3',
      bgColor: 'bg-chart-3/10',
    },
    {
      key: 'public_transport_score',
      label: t('factorBreakdown.factors.publicTransport.label'),
      icon: <Bus className="h-4 w-4" aria-hidden="true" />,
      weight: '10%',
      description: t('factorBreakdown.factors.publicTransport.description'),
      color: 'text-chart-8',
      bgColor: 'bg-chart-8/10',
    },
  ];

  const getScoreColor = (score: number): string => {
    if (score >= 85) return 'bg-success';
    if (score >= 70) return 'bg-chart-7';
    if (score >= 55) return 'bg-warning';
    if (score >= 40) return 'bg-caution';
    return 'bg-destructive';
  };

  const getConfidenceIndicator = (factorKey: string): { level: string; color: string } => {
    const detail = result.factor_details?.[factorKey as keyof typeof result.factor_details];
    if (!detail) {
      return { level: 'N/A', color: 'text-muted-foreground' };
    }

    if (detail.confidence >= 0.8) {
      return { level: t('factorBreakdown.confidenceHigh'), color: 'text-chart-2' };
    }
    if (detail.confidence >= 0.6) {
      return { level: t('factorBreakdown.confidenceMedium'), color: 'text-warning' };
    }
    return { level: t('factorBreakdown.confidenceLow'), color: 'text-destructive' };
  };

  if (compact) {
    // Compact version: smaller cards in a grid
    return (
      <div className={`grid grid-cols-2 md:grid-cols-4 gap-3 ${className}`}>
        {factorConfigs.map((config) => {
          const score = result[config.key] as number;

          return (
            <div
              key={config.key}
              className={`rounded-lg border p-3 ${config.bgColor} border-${config.color.split('-')[1]}-200`}
            >
              <div className="flex items-center gap-2 mb-2">
                <div className={`${config.color}`}>{config.icon}</div>
                <span className="text-sm font-medium">{config.label}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className={`text-xl font-bold ${config.color}`}>{score.toFixed(1)}</span>
                <span className="text-xs text-muted-foreground">{config.weight}</span>
              </div>
            </div>
          );
        })}
      </div>
    );
  }

  // Full version: detailed cards with more information
  return (
    <div className={`space-y-4 ${className}`}>
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold">{t('factorBreakdown.title')}</h3>
        <div className="text-sm text-muted-foreground">
          Overall: <span className="font-semibold">{result.overall_score.toFixed(1)}/100</span>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {factorConfigs.map((config) => {
          const score = result[config.key] as number;
          const confidence = getConfidenceIndicator(config.key);
          const detail = result.factor_details?.[config.key as keyof typeof result.factor_details];

          return (
            <div
              key={config.key}
              className="rounded-lg border bg-card p-4 shadow-sm hover:shadow-md transition-shadow"
            >
              {/* Header with icon and label */}
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-2">
                  <div className={`p-2 rounded-lg ${config.bgColor} ${config.color}`}>
                    {config.icon}
                  </div>
                  <div>
                    <p className="font-semibold text-sm">{config.label}</p>
                    <p className="text-xs text-muted-foreground">{config.weight}</p>
                  </div>
                </div>
              </div>

              {/* Score display */}
              <div className="mb-3">
                <div className="flex items-end justify-between mb-2">
                  <span className={`text-3xl font-bold ${config.color}`}>{score.toFixed(1)}</span>
                  <span className="text-xs text-muted-foreground">/ 100</span>
                </div>

                {/* Progress bar */}
                <div className="w-full bg-muted rounded-full h-2">
                  <div
                    className={`h-2 rounded-full ${getScoreColor(score)}`}
                    style={{ width: `${Math.min(score, 100)}%` }}
                    role="progressbar"
                    aria-valuenow={score}
                    aria-valuemin={0}
                    aria-valuemax={100}
                  />
                </div>
              </div>

              {/* Description */}
              <p className="text-xs text-muted-foreground mb-2">{config.description}</p>

              {/* Confidence indicator */}
              {detail && (
                <div className="flex items-center justify-between text-xs">
                  <span className="text-muted-foreground">{t('factorBreakdown.dataConfidence')}</span>
                  <span className={confidence.color}>{confidence.level}</span>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Legend */}
      <div className="flex flex-wrap items-center gap-4 text-xs text-muted-foreground pt-2 border-t">
        <span className="font-medium">{t('factorBreakdown.scoreRanges')}</span>
        <span className="flex items-center gap-1">
          <span className="w-3 h-3 rounded-full bg-success" />
          85+ Excellent
        </span>
        <span className="flex items-center gap-1">
          <span className="w-3 h-3 rounded-full bg-chart-7" />
          70-84 Good
        </span>
        <span className="flex items-center gap-1">
          <span className="w-3 h-3 rounded-full bg-warning" />
          55-69 Fair
        </span>
        <span className="flex items-center gap-1">
          <span className="w-3 h-3 rounded-full bg-caution" />
          40-54 Poor
        </span>
        <span className="flex items-center gap-1">
          <span className="w-3 h-3 rounded-full bg-destructive" />
          &lt;40 Very Poor
        </span>
      </div>
    </div>
  );
}
