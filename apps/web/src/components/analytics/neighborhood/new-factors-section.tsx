'use client';

import React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Wind, Volume2, Bus, CheckCircle, AlertTriangle, Info } from 'lucide-react';
import type { NeighborhoodQualityResult } from '@/lib/types';
import { useTranslations } from 'next-intl';

interface NewFactorsSectionProps {
  result: NeighborhoodQualityResult;
  className?: string;
}

interface NewFactorConfig {
  key: 'air_quality_score' | 'noise_level_score' | 'public_transport_score';
  label: string;
  icon: React.ReactNode;
  detailKey: 'air_quality' | 'noise_level' | 'public_transport';
  description: string;
  getRating: (value: number) => { label: string; color: string; bg: string };
  formatValue: (detail: { raw_value: number; unit: string } | undefined) => string;
}

/**
 * NewFactorsSection Component
 *
 * Displays detailed cards for the three new scoring factors:
 * - Air Quality (AQI-based)
 * - Noise Level (decibel-based)
 * - Public Transport (stop count-based)
 *
 * Each card shows:
 * - Score gauge/chart
 * - Raw value with unit
 * - Data source and confidence indicator
 * - Interpretation of what the score means
 */
export function NewFactorsSection({ result, className = '' }: NewFactorsSectionProps) {
  const t = useTranslations('neighborhood');
  const getAirQualityRating = (aqi: number) => {
    if (aqi <= 50) {
      return { label: t('newFactors.ratings.good'), color: 'text-success', bg: 'bg-success/10 border-success/30' };
    }
    if (aqi <= 100) {
      return { label: t('newFactors.ratings.moderate'), color: 'text-warning', bg: 'bg-warning/10 border-warning/30' };
    }
    if (aqi <= 150) {
      return {
        label: t('newFactors.ratings.unhealthySensitive'),
        color: 'text-caution',
        bg: 'bg-caution/10 border-caution/30',
      };
    }
    if (aqi <= 200) {
      return { label: t('newFactors.ratings.unhealthy'), color: 'text-destructive', bg: 'bg-destructive/10 border-destructive/30' };
    }
    return {
      label: t('newFactors.ratings.veryUnhealthy'),
      color: 'text-critical',
      bg: 'bg-critical/10 border-critical/30',
    };
  };

  const getNoiseRating = (dB: number) => {
    if (dB <= 45) {
      return { label: t('newFactors.ratings.quiet'), color: 'text-success', bg: 'bg-success/10 border-success/30' };
    }
    if (dB <= 55) {
      return { label: t('newFactors.ratings.moderate'), color: 'text-warning', bg: 'bg-warning/10 border-warning/30' };
    }
    if (dB <= 65) {
      return { label: t('newFactors.ratings.noisy'), color: 'text-caution', bg: 'bg-caution/10 border-caution/30' };
    }
    return { label: t('newFactors.ratings.veryNoisy'), color: 'text-destructive', bg: 'bg-destructive/10 border-destructive/30' };
  };

  const getTransportRating = (stopCount: number) => {
    if (stopCount >= 10) {
      return { label: t('newFactors.ratings.excellent'), color: 'text-success', bg: 'bg-success/10 border-success/30' };
    }
    if (stopCount >= 5) {
      return { label: t('newFactors.ratings.good'), color: 'text-chart-7', bg: 'bg-chart-7/10 border-chart-7/30' };
    }
    if (stopCount >= 3) {
      return { label: t('newFactors.ratings.fair'), color: 'text-warning', bg: 'bg-warning/10 border-warning/30' };
    }
    return { label: t('newFactors.ratings.limited'), color: 'text-destructive', bg: 'bg-destructive/10 border-destructive/30' };
  };

  const formatAirQuality = (detail: { raw_value: number; unit: string } | undefined) => {
    if (!detail) return 'N/A';
    return `AQI ${detail.raw_value}`;
  };

  const formatNoise = (detail: { raw_value: number; unit: string } | undefined) => {
    if (!detail) return 'N/A';
    return `${detail.raw_value} dB`;
  };

  const formatTransport = (detail: { raw_value: number; unit: string } | undefined) => {
    if (!detail) return 'N/A';
    return t('newFactors.stopsWithin1km', { count: detail.raw_value });
  };

  const factorConfigs: NewFactorConfig[] = [
    {
      key: 'air_quality_score',
      label: t('newFactors.airQuality.label'),
      icon: <Wind className="h-5 w-5" aria-hidden="true" />,
      detailKey: 'air_quality',
      description:
        t('newFactors.airQuality.description'),
      getRating: (_value: number) => {
        void _value;
        const detail = result.factor_details?.air_quality;
        return detail
          ? getAirQualityRating(detail.raw_value)
          : { label: t('newFactors.ratings.unknown'), color: 'text-muted-foreground', bg: 'bg-muted border-border' };
      },
      formatValue: formatAirQuality,
    },
    {
      key: 'noise_level_score',
      label: t('newFactors.noiseLevel.label'),
      icon: <Volume2 className="h-5 w-5" aria-hidden="true" />,
      detailKey: 'noise_level',
      description:
        t('newFactors.noiseLevel.description'),
      getRating: (_value: number) => {
        void _value;
        const detail = result.factor_details?.noise_level;
        return detail
          ? getNoiseRating(detail.raw_value)
          : { label: t('newFactors.ratings.unknown'), color: 'text-muted-foreground', bg: 'bg-muted border-border' };
      },
      formatValue: formatNoise,
    },
    {
      key: 'public_transport_score',
      label: t('newFactors.publicTransport.label'),
      icon: <Bus className="h-5 w-5" aria-hidden="true" />,
      detailKey: 'public_transport',
      description:
        t('newFactors.publicTransport.description'),
      getRating: (_value: number) => {
        void _value;
        const detail = result.factor_details?.public_transport;
        return detail
          ? getTransportRating(detail.raw_value)
          : { label: t('newFactors.ratings.unknown'), color: 'text-muted-foreground', bg: 'bg-muted border-border' };
      },
      formatValue: formatTransport,
    },
  ];

  const getConfidenceIcon = (confidence: number | undefined) => {
    if (confidence === undefined) {
      return <Info className="h-3 w-3 text-muted-foreground" aria-hidden="true" />;
    }
    if (confidence >= 0.8) {
      return <CheckCircle className="h-3 w-3 text-success" aria-hidden="true" />;
    }
    if (confidence >= 0.6) {
      return <Info className="h-3 w-3 text-warning" aria-hidden="true" />;
    }
    return <AlertTriangle className="h-3 w-3 text-destructive" aria-hidden="true" />;
  };

  const getScoreColor = (score: number): string => {
    if (score >= 85) return 'text-success';
    if (score >= 70) return 'text-chart-7';
    if (score >= 55) return 'text-warning';
    if (score >= 40) return 'text-caution';
    return 'text-destructive';
  };

  return (
    <div className={className}>
      <Card>
        <CardHeader>
          <CardTitle>{t('newFactors.title')}</CardTitle>
          <CardDescription>{t('newFactors.description')}</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {factorConfigs.map((config) => {
              const score = result[config.key];
              const detail = result.factor_details?.[config.detailKey];
              const rating = config.getRating(score);
              const confidence = detail?.confidence;

              return (
                <div
                  key={config.key}
                  className={`rounded-lg border-2 p-5 ${rating.bg} transition-all hover:shadow-md`}
                >
                  {/* Header */}
                  <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-2">
                      <div className={`p-2 rounded-lg bg-card ${rating.color} shadow-sm`}>
                        {config.icon}
                      </div>
                      <div>
                        <h4 className="font-semibold text-sm">{config.label}</h4>
                        <span className={`text-xs font-medium ${rating.color}`}>
                          {rating.label}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Score Gauge */}
                  <div className="flex items-center justify-center mb-4">
                    <div className="relative w-24 h-24">
                      {/* Background circle */}
                      <svg
                        className="w-full h-full transform -rotate-90"
                        role="img"
                        aria-label={t('newFactors.scoreLabel', {
                          label: config.label,
                          score: score.toFixed(0),
                        })}
                      >
                        <circle
                          cx="48"
                          cy="48"
                          r="40"
                          stroke="currentColor"
                          strokeWidth="8"
                          fill="none"
                          className="text-muted-foreground"
                        />
                        {/* Score arc */}
                        <circle
                          cx="48"
                          cy="48"
                          r="40"
                          stroke="currentColor"
                          strokeWidth="8"
                          fill="none"
                          strokeDasharray={`${(score / 100) * 251.2} 251.2`}
                          className={getScoreColor(score)}
                          strokeLinecap="round"
                        />
                      </svg>
                      {/* Center score */}
                      <div className="absolute inset-0 flex items-center justify-center">
                        <span className={`text-2xl font-bold ${getScoreColor(score)}`}>
                          {score.toFixed(0)}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Raw value */}
                  <div className="text-center mb-3">
                    <p className="text-lg font-semibold text-foreground">
                      {config.formatValue(detail)}
                    </p>
                  </div>

                  {/* Data source info */}
                  {detail && (
                    <div className="flex items-center justify-between text-xs text-muted-foreground mb-3 pb-3 border-b border-border">
                      <span>{`${t('newFactors.source')} ${detail.data_source}`}</span>
                      <div
                        className="flex items-center gap-1"
                        title={t('newFactors.confidenceLabel', {
                          value: ((confidence ?? 0) * 100).toFixed(0),
                        })}
                      >
                        {getConfidenceIcon(confidence)}
                        <span
                          className={
                            (confidence ?? 0) >= 0.8
                              ? 'text-success'
                              : (confidence ?? 0) >= 0.6
                                ? 'text-warning'
                                : 'text-destructive'
                          }
                        >
                          {((confidence ?? 0) * 100).toFixed(0)}%
                        </span>
                      </div>
                    </div>
                  )}

                  {/* Description */}
                  <p className="text-xs text-muted-foreground leading-relaxed">
                    {config.description}
                  </p>
                </div>
              );
            })}
          </div>

          {/* Data freshness note */}
          {result.data_freshness && (
            <div className="mt-4 pt-4 border-t">
              <p className="text-xs text-muted-foreground">
                <Info className="h-3 w-3 inline mr-1" aria-hidden="true" />
                {t('newFactors.dataFreshness', {
                  airQuality: result.data_freshness.air_quality
                    ? new Date(result.data_freshness.air_quality).toLocaleDateString()
                    : 'N/A',
                  noiseLevel: result.data_freshness.noise_level
                    ? new Date(result.data_freshness.noise_level).toLocaleDateString()
                    : 'N/A',
                  transport: result.data_freshness.public_transport
                    ? new Date(result.data_freshness.public_transport).toLocaleDateString()
                    : 'N/A',
                })}
              </p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
