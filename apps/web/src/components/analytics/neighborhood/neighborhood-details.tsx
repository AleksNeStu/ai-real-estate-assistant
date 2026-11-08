'use client';

import React, { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { MapPin, Loader2, AlertCircle, Info } from 'lucide-react';
import { NeighborhoodBadge } from '../neighborhood-badge';
import { FactorBreakdown } from './factor-breakdown';
import { NewFactorsSection } from './new-factors-section';
import { CityComparisonCard } from './city-comparison-card';
import { WhatsNearbySection } from './whats-nearby-section';
import type { NeighborhoodQualityResult } from '@/lib/types';
import { useTranslations } from 'next-intl';
import { EmptyState } from '@/components/ui/states';

interface NeighborhoodDetailsProps {
  result: NeighborhoodQualityResult;
  compact?: boolean;
  showMap?: boolean;
  className?: string;
}

interface ErrorState {
  message: string;
  requestId?: string;
}

/**
 * NeighborhoodDetails Component
 *
 * Main container component that brings together all neighborhood quality sub-components.
 * Displays comprehensive neighborhood information including:
 * - Overall score badge
 * - Factor breakdown (all 8 factors)
 * - Extended factors (Air Quality, Noise Level, Public Transport)
 * - City comparison
 * - Nearby points of interest
 *
 * Supports both compact and full view modes with tabbed navigation.
 */
export function NeighborhoodDetails({
  result,
  compact = false,
  showMap = false,
  className = '',
}: NeighborhoodDetailsProps) {
  const t = useTranslations('neighborhood');
  const [activeTab, setActiveTab] = useState('overview');

  if (!result) {
    return (
      <EmptyState icon={AlertCircle} title={t('details.noData')} className={className} />
    );
  }

  // Compact view: simplified single card display
  if (compact) {
    return (
      <Card className={className}>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <MapPin className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
              <CardTitle className="text-lg">{t('details.quality')}</CardTitle>
            </div>
            <NeighborhoodBadge overallScore={result.overall_score} size="sm" />
          </div>
          {(result.city || result.neighborhood) && (
            <CardDescription className="text-xs">
              {[result.neighborhood, result.city].filter(Boolean).join(', ')}
            </CardDescription>
          )}
        </CardHeader>
        <CardContent>
          <FactorBreakdown result={result} compact />
        </CardContent>
      </Card>
    );
  }

  // Full view with tabs and expandable sections
  return (
    <div className={`space-y-6 ${className}`}>
      {/* Header Card */}
      <Card>
        <CardHeader>
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-1">
                <MapPin className="h-5 w-5 text-muted-foreground" aria-hidden="true" />
                <CardTitle>{t('details.assessment')}</CardTitle>
              </div>
              <CardDescription>
                {result.neighborhood && <span className="font-medium">{result.neighborhood}</span>}
                {result.neighborhood && result.city && <span>, </span>}
                {result.city && <span>{result.city}</span>}
                {result.latitude && result.longitude && (
                  <span className="ml-2 text-xs text-muted-foreground">
                    ({result.latitude.toFixed(4)}, {result.longitude.toFixed(4)})
                  </span>
                )}
              </CardDescription>
            </div>
            <NeighborhoodBadge overallScore={result.overall_score} size="lg" showLabel />
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="text-center p-3 rounded-lg bg-muted/30">
              <p className="text-2xl font-bold text-info">{result.safety_score.toFixed(1)}</p>
              <p className="text-xs text-muted-foreground">{t('details.safety')}</p>
            </div>
            <div className="text-center p-3 rounded-lg bg-muted/30">
              <p className="text-2xl font-bold text-chart-4">
                {result.schools_score.toFixed(1)}
              </p>
              <p className="text-xs text-muted-foreground">{t('details.schools')}</p>
            </div>
            <div className="text-center p-3 rounded-lg bg-muted/30">
              <p className="text-2xl font-bold text-success">
                {result.walkability_score.toFixed(1)}
              </p>
              <p className="text-xs text-muted-foreground">{t('details.walkability')}</p>
            </div>
            <div className="text-center p-3 rounded-lg bg-muted/30">
              <p className="text-2xl font-bold text-chart-7">
                {result.green_space_score.toFixed(1)}
              </p>
              <p className="text-xs text-muted-foreground">{t('details.greenSpace')}</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Main Content Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="overview">{t('details.overview')}</TabsTrigger>
          <TabsTrigger value="factors">{t('details.allFactors')}</TabsTrigger>
          <TabsTrigger value="extended">{t('details.extended')}</TabsTrigger>
          <TabsTrigger value="nearby">{t('details.nearby')}</TabsTrigger>
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview" className="mt-4 space-y-6">
          {/* Quick factor summary */}
          <FactorBreakdown result={result} compact={false} />

          {/* City Comparison */}
          <CityComparisonCard result={result} />

          {/* Data sources */}
          {result.data_sources && result.data_sources.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">{t('details.dataSources')}</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex flex-wrap gap-2">
                  {result.data_sources.map((source, index) => (
                    <span
                      key={index}
                      className="inline-flex items-center gap-1 px-2 py-1 text-xs rounded-md bg-muted"
                    >
                      <Info className="h-3 w-3" aria-hidden="true" />
                      {source}
                    </span>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* All Factors Tab */}
        <TabsContent value="factors" className="mt-4 space-y-6">
          <FactorBreakdown result={result} compact={false} />

          {/* Factor details table */}
          {result.factor_details && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">{t('details.detailedFactorInfo')}</CardTitle>
                <CardDescription>{t('details.detailedFactorDescription')}</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b">
                        <th className="text-left py-2 px-3 font-medium">{t('details.factor')}</th>
                        <th className="text-right py-2 px-3 font-medium">{t('details.score')}</th>
                        <th className="text-right py-2 px-3 font-medium">{t('details.rawValue')}</th>
                        <th className="text-center py-2 px-3 font-medium">{t('details.confidence')}</th>
                        <th className="text-left py-2 px-3 font-medium">{t('details.source')}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {Object.entries(result.factor_details).map(([key, detail]) => {
                        if (!detail) return null;
                        const factorLabel =
                          {
                            safety: t('details.safety'),
                            schools: t('details.schools'),
                            amenities: t('details.amenities'),
                            walkability: t('details.walkability'),
                            green_space: t('details.greenSpace'),
                            air_quality: t('details.airQuality'),
                            noise_level: t('details.noiseLevel'),
                            public_transport: t('details.publicTransport'),
                          }[key] || key;

                        const scoreKey = `${key}_score` as keyof NeighborhoodQualityResult;
                        const score = result[scoreKey] as number;

                        return (
                          <tr key={key} className="border-b last:border-0">
                            <td className="py-2 px-3">{factorLabel}</td>
                            <td className="py-2 px-3 text-right font-medium">{score.toFixed(1)}</td>
                            <td className="py-2 px-3 text-right">
                              {detail.raw_value} {detail.unit}
                            </td>
                            <td className="py-2 px-3 text-center">
                              <span
                                className={`inline-block px-2 py-0.5 rounded text-xs ${
                                  detail.confidence >= 0.8
                                    ? 'bg-success/20 text-success'
                                    : detail.confidence >= 0.6
                                      ? 'bg-warning/20 text-warning'
                                      : 'bg-destructive/20 text-destructive'
                                }`}
                              >
                                {(detail.confidence * 100).toFixed(0)}%
                              </span>
                            </td>
                            <td className="py-2 px-3 text-xs text-muted-foreground">
                              {detail.data_source}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* Extended Factors Tab */}
        <TabsContent value="extended" className="mt-4 space-y-6">
          <NewFactorsSection result={result} />
        </TabsContent>

        {/* Nearby Tab */}
        <TabsContent value="nearby" className="mt-4">
          <WhatsNearbySection result={result} showMap={showMap} />
        </TabsContent>
      </Tabs>

      {/* Data freshness footer */}
      {result.data_freshness && (
        <div className="flex items-center gap-2 text-xs text-muted-foreground px-2">
          <Info className="h-3 w-3" aria-hidden="true" />
          <span>
            Data freshness:{' '}
            {Object.entries(result.data_freshness).map(([key, date]) => (
              <span key={key} className="mr-3">
                <span className="font-medium">{key}:</span> {new Date(date).toLocaleDateString()}
              </span>
            ))}
          </span>
        </div>
      )}
    </div>
  );
}

/**
 * Loading state for neighborhood details
 */
export function NeighborhoodDetailsLoading({
  message,
}: {
  message?: string;
}) {
  const t = useTranslations('neighborhood');
  const loadingMessage = message ?? t('details.loading');
  return (
    <Card>
      <CardContent className="flex items-center justify-center py-12">
        <div className="text-center">
          <Loader2
            className="h-8 w-8 animate-spin mx-auto mb-3 text-muted-foreground"
            aria-hidden="true"
          />
          <p className="text-sm text-muted-foreground">{loadingMessage}</p>
        </div>
      </CardContent>
    </Card>
  );
}

/**
 * Error state for neighborhood details
 */
export function NeighborhoodDetailsError({
  error,
  onRetry,
}: {
  error: ErrorState;
  onRetry?: () => void;
}) {
  const t = useTranslations('neighborhood');
  return (
    <Card>
      <CardContent className="flex items-center justify-center py-12">
        <div className="text-center max-w-md">
          <AlertCircle className="h-8 w-8 mx-auto mb-3 text-destructive" aria-hidden="true" />
          <h3 className="text-lg font-semibold mb-2">{t('details.failedToLoad')}</h3>
          <p className="text-sm text-muted-foreground mb-4">{error.message}</p>
          {error.requestId && (
            <p className="text-xs font-mono text-muted-foreground mb-4">
              request_id={error.requestId}
            </p>
          )}
          {onRetry && (
            <Button variant="outline" onClick={onRetry}>
              Try Again
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
