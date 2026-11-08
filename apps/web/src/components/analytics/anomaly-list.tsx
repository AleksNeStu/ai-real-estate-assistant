'use client';

import * as React from 'react';
import { useState, useEffect } from 'react';
import { formatDistanceToNow } from 'date-fns';
import { AlertTriangle, Eye, CheckCircle, Clock, Search } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { AnomalyBadge, AnomalyTypeBadge, getSeverityIcon } from './anomaly-badge';
import type { MarketAnomaly, AnomalyFilterParams, AnomalySeverity, AnomalyType } from '@/lib/types';
import { getAnomalies, dismissAnomaly } from '@/lib/api';
import { cn } from '@/lib/utils';
import { useTranslations } from 'next-intl';
import { EmptyState } from '@/components/ui/states';

// Extended filter params with state
interface AnomalyFilters extends AnomalyFilterParams {
  search: string;
}

const severityOptions: AnomalySeverity[] = ['critical', 'high', 'medium', 'low'];

const typeOptions: AnomalyType[] = [
  'price_spike',
  'price_drop',
  'volume_spike',
  'volume_drop',
  'unusual_pattern',
];

/**
 * Maps the API severity / type values to the catalogue keys that carry their
 * reader-visible label.
 */
const SEVERITY_LABEL_KEYS: Record<string, string> = {
  critical: 'critical',
  high: 'high',
  medium: 'medium',
  low: 'low',
};

const TYPE_LABEL_KEYS: Record<string, string> = {
  price_spike: 'priceSpike',
  price_drop: 'priceDrop',
  volume_spike: 'volumeSpike',
  volume_drop: 'volumeDrop',
  unusual_pattern: 'unusualPattern',
};

export function AnomalyList() {
  const t = useTranslations('marketTrends');
  const tAnalytics = useTranslations('analytics');
  const [anomalies, setAnomalies] = useState<MarketAnomaly[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<AnomalyFilters>({
    limit: 20,
    offset: 0,
    severity: undefined,
    anomaly_type: undefined,
    scope_type: undefined,
    scope_id: undefined,
    search: '',
  });

  useEffect(() => {
    const loadAnomalies = async () => {
      try {
        setLoading(true);
        setError(null);
        const response = await getAnomalies(filters);
        setAnomalies(response.anomalies);
      } catch (err) {
        setError(err instanceof Error ? err.message : t('anomalies.loadFailed'));
      } finally {
        setLoading(false);
      }
    };
    loadAnomalies();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters.severity, filters.anomaly_type, filters.scope_type, filters.scope_id]);

  const handleDismiss = async (anomalyId: string) => {
    try {
      await dismissAnomaly(anomalyId);
      setAnomalies((prev) => prev.filter((a) => a.id !== anomalyId));
    } catch (err) {
      console.error('Failed to dismiss anomaly:', err);
    }
  };

  const handleFilterChange = (key: keyof AnomalyFilters, value: string | undefined) => {
    setFilters((prev) => ({
      ...prev,
      [key]: value,
      offset: 0, // Reset to first page when filter changes
    }));
  };

  const filteredAnomalies = anomalies.filter((a) => {
    if (filters.search) {
      const searchLower = filters.search.toLowerCase();
      return (
        a.anomaly_type.toLowerCase().includes(searchLower) ||
        a.scope_id.toLowerCase().includes(searchLower) ||
        JSON.stringify(a.context).toLowerCase().includes(searchLower)
      );
    }
    return true;
  });

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    return formatDistanceToNow(date, { addSuffix: true });
  };

  const getScopeLabel = (scopeType: string, scopeId: string) => {
    switch (scopeType) {
      case 'property':
        return tAnalytics('anomalyList.scope.property', { id: scopeId });
      case 'city':
        return tAnalytics('anomalyList.scope.city', { id: scopeId });
      case 'district':
        return tAnalytics('anomalyList.scope.district', { id: scopeId });
      case 'market':
        return tAnalytics('anomalyList.scope.market', { id: scopeId });
      case 'region':
        return tAnalytics('anomalyList.scope.region', { id: scopeId });
      default:
        return scopeId;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header with filters */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-2">
          <h2 className="text-2xl font-bold tracking-tight">{t('anomalies.title')}</h2>
          <Badge variant="secondary">
            {tAnalytics('anomalyList.totalCount', { count: anomalies.length })}
          </Badge>
        </div>

        <div className="flex gap-2">
          {/* Search */}
          <div className="relative">
            <input
              type="text"
              placeholder={t('anomalies.searchPlaceholder')}
              value={filters.search}
              onChange={(e) => handleFilterChange('search', e.target.value)}
              className="pl-10 pr-4 text-sm text-muted"
              aria-label={t('anomalies.searchLabel')}
            />
            <Search className="absolute left-3 top-3 h-4 w-4 text-muted" aria-hidden="true" />
          </div>

          {/* Severity Filter */}
          <select
            value={filters.severity || ''}
            onChange={(e) =>
              handleFilterChange(
                'severity',
                (e.target.value || undefined) as AnomalySeverity | undefined
              )
            }
            className="rounded-md border bg-background px-3 py-2 text-sm"
            aria-label={t('anomalies.filterSeverity')}
          >
            <option value="">{t('anomalies.allSeverities')}</option>
            {severityOptions.map((s) => (
              <option key={s} value={s}>
                {t(`anomalies.severities.${SEVERITY_LABEL_KEYS[s] ?? s}`)}
              </option>
            ))}
          </select>

          {/* Type Filter */}
          <select
            value={filters.anomaly_type || ''}
            onChange={(e) =>
              handleFilterChange(
                'anomaly_type',
                (e.target.value || undefined) as AnomalyType | undefined
              )
            }
            className="rounded-md border bg-background px-3 py-2 text-sm"
            aria-label={t('anomalies.filterType')}
          >
            <option value="">{t('anomalies.allTypes')}</option>
            {typeOptions.map((type) => (
              <option key={type} value={type}>
                {t(`anomalies.types.${TYPE_LABEL_KEYS[type] ?? type}`)}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Loading State */}
      {loading && (
        <div className="flex justify-center py-8" role="status" aria-live="polite">
          <div className="animate-pulse flex flex-col items-center gap-2">
            <div className="h-4 w-4 bg-muted rounded-full"></div>
            <p className="text-sm text-muted">{t('anomalies.loading')}</p>
          </div>
        </div>
      )}

      {/* Error State */}
      {error && (
        <div className="rounded-md border border-destructive/50 bg-destructive/10 p-4" role="alert">
          <div className="flex items-center gap-2 text-destructive">
            <AlertTriangle className="h-4 w-4" aria-hidden="true" />
            <p className="text-sm">{error}</p>
          </div>
        </div>
      )}

      {/* Empty State */}
      {!loading && !error && filteredAnomalies.length === 0 && (
        <EmptyState
          icon={CheckCircle}
          title={t('anomalies.noneDetected')}
          description={t('anomalies.emptyHint')}
        />
      )}

      {/* Anomaly Cards */}
      {!loading && !error && filteredAnomalies.length > 0 && (
        <div className="grid gap-4 md:grid-cols-1 lg:grid-cols-2">
          {filteredAnomalies.map((anomaly) => (
            <Card key={anomaly.id} className="overflow-hidden transition-all hover:shadow-md">
              <div className="p-4 space-y-3">
                {/* Header */}
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-2">
                    {React.createElement(getSeverityIcon(anomaly.severity), {
                      className: 'h-4 w-4',
                    })}
                    <AnomalyBadge severity={anomaly.severity} />
                  </div>
                  <div className="flex items-center gap-2 text-xs text-muted">
                    <Clock className="h-3 w-3" aria-hidden="true" />
                    <span>{formatTimestamp(anomaly.detected_at)}</span>
                  </div>
                </div>

                {/* Type and Scope */}
                <div className="flex items-center gap-2 mt-2">
                  <AnomalyTypeBadge type={anomaly.anomaly_type} />
                  <span className="text-sm text-muted">
                    {getScopeLabel(anomaly.scope_type, anomaly.scope_id)}
                  </span>
                </div>

                {/* Metric Details */}
                <div className="mt-3 space-y-2">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted">{t('anomalies.metric')}</span>
                    <span className="font-medium">{anomaly.metric_name}</span>
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted">{t('anomalies.expected')}</span>
                    <span className="font-medium">
                      {typeof anomaly.expected_value === 'number'
                        ? anomaly.expected_value.toLocaleString()
                        : anomaly.expected_value}
                    </span>
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted">{t('anomalies.actual')}</span>
                    <span
                      className={cn(
                        'font-medium',
                        anomaly.actual_value > anomaly.expected_value
                          ? 'text-destructive'
                          : 'text-success'
                      )}
                    >
                      {typeof anomaly.actual_value === 'number'
                        ? anomaly.actual_value.toLocaleString()
                        : anomaly.actual_value}
                    </span>
                  </div>
                </div>

                {/* Deviation */}
                <div className="flex items-center justify-between rounded-md bg-muted/50 p-2">
                  <span className="text-sm font-medium">{t('anomalies.deviation')}</span>
                  <span
                    className={cn(
                      'font-bold',
                      anomaly.deviation_percent > 0
                        ? anomaly.deviation_percent > 50
                          ? 'text-destructive'
                          : anomaly.deviation_percent > 20
                            ? 'text-caution'
                            : 'text-warning'
                        : 'text-success'
                    )}
                  >
                    {anomaly.deviation_percent > 0 ? '+' : '-'}
                    {Math.abs(anomaly.deviation_percent).toFixed(1)}%
                  </span>
                </div>

                {/* Z-Score (if available) */}
                {anomaly.z_score !== undefined && anomaly.z_score !== null && (
                  <div className="mt-2 flex items-center justify-between text-xs">
                    <span className="text-muted">{t('anomalies.zScore')}</span>
                    <span
                      className={cn(
                        'font-medium',
                        Math.abs(anomaly.z_score) > 3 ? 'text-destructive' : ''
                      )}
                    >
                      {anomaly.z_score.toFixed(2)}
                    </span>
                  </div>
                )}

                {/* Actions */}
                {!anomaly.dismissed_at && (
                  <div className="mt-3 flex justify-end">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleDismiss(anomaly.id)}
                      className="text-xs"
                    >
                      <Eye className="h-3 w-3 mr-1" aria-hidden="true" />
                      {tAnalytics('anomalyList.markReviewed')}
                    </Button>
                  </div>
                )}

                {/* Dismissed Badge */}
                {anomaly.dismissed_at && (
                  <div className="mt-2">
                    <Badge variant="secondary" className="text-xs">
                      {anomaly.dismissed_by
                        ? tAnalytics('anomalyList.dismissedBy', { name: anomaly.dismissed_by })
                        : tAnalytics('anomalyList.dismissedBySystem')}
                    </Badge>
                  </div>
                )}
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
