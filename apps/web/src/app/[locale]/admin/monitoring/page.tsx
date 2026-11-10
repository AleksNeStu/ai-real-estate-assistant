'use client';

import { useState, useEffect, useCallback } from 'react';
import { useTranslations } from 'next-intl';
import { Loader2, RefreshCw, Activity, X } from 'lucide-react';

import {
  AlertsLedger,
  MonitoringStats,
  RequestsPanel,
  ServiceLedger,
  SourceBreakdown,
  buildAlerts,
} from '@/components/admin/monitoring-panels';
import { Button } from '@/components/ui/button';
import { MonoAnnotation } from '@/components/ui/mono-annotation';
import { SectionHeader } from '@/components/ui/page-header';
import { ErrorState, LoadingState } from '@/components/ui/states';
import {
  getHealthStatus,
  getReadinessStatus,
  getMonitoringOverview,
  sendTestAlert,
  type HealthStatus,
  type ReadinessStatus,
  type MonitoringOverview,
} from '@/lib/api/admin';

/**
 * The monitoring tab.
 *
 * The state of a deployment is a handful of numbers, so they are stat tiles;
 * the panel that would hold the request series is a frame with its area held
 * open; the alerts are a list, so they are a ledger.
 *
 * Every number comes from the API. A measurement the API does not carry is
 * not drawn.
 */
export default function MonitoringPage() {
  const t = useTranslations('pages.admin.monitoring');
  const tPanels = useTranslations('pages.admin.monitoring.panels');
  const tCommon = useTranslations('common');

  const [healthStatus, setHealthStatus] = useState<HealthStatus | null>(null);
  const [readinessStatus, setReadinessStatus] = useState<ReadinessStatus | null>(null);
  const [overview, setOverview] = useState<MonitoringOverview | null>(null);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date());

  const [testAlertLoading, setTestAlertLoading] = useState(false);
  const [testAlertResult, setTestAlertResult] = useState<string | null>(null);

  const loadMonitoringData = useCallback(async () => {
    try {
      setError(null);
      const [health, readiness, overviewData] = await Promise.all([
        getHealthStatus(),
        getReadinessStatus(),
        getMonitoringOverview(),
      ]);

      setHealthStatus(health);
      setReadinessStatus(readiness);
      setOverview(overviewData);
      setLastRefresh(new Date());
    } catch (e) {
      console.error(t('errors.load'), e);
      setError(e instanceof Error ? e.message : t('errors.load'));
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [t]);

  useEffect(() => {
    loadMonitoringData();

    const interval = setInterval(() => {
      setRefreshing(true);
      loadMonitoringData();
    }, 30000);

    return () => clearInterval(interval);
  }, [loadMonitoringData]);

  const handleRefresh = () => {
    setRefreshing(true);
    loadMonitoringData();
  };

  const handleTestAlert = async () => {
    setTestAlertLoading(true);
    setTestAlertResult(null);
    try {
      const result = await sendTestAlert();
      setTestAlertResult(result.message);
      setTimeout(() => setTestAlertResult(null), 5000);
    } catch (e) {
      setTestAlertResult(e instanceof Error ? e.message : t('errors.testAlert'));
      setTimeout(() => setTestAlertResult(null), 5000);
    } finally {
      setTestAlertLoading(false);
    }
  };

  const alerts =
    readinessStatus && overview ? buildAlerts(readinessStatus, overview) : [];

  if (loading) {
    return <LoadingState rows={4} />;
  }

  return (
    <>
      <SectionHeader
        title={tPanels('title')}
        description={t('description')}
        actions={
          <>
            <MonoAnnotation>{t('lastRefreshed', { time: lastRefresh.toLocaleTimeString() })}</MonoAnnotation>
            <Button
              variant="outline"
              size="sm"
              onClick={handleRefresh}
              disabled={refreshing}
            >
              {refreshing ? (
                <Loader2 className="mr-2 size-4 animate-spin" aria-hidden="true" />
              ) : (
                <RefreshCw className="mr-2 size-4" aria-hidden="true" />
              )}
              {tCommon('refresh')}
            </Button>
            <Button variant="destructive" size="sm" onClick={handleTestAlert} disabled={testAlertLoading}>
              {testAlertLoading ? (
                <Loader2 className="mr-2 size-4 animate-spin" aria-hidden="true" />
              ) : (
                <Activity className="mr-2 size-4" aria-hidden="true" />
              )}
              {t('testAlert')}
            </Button>
          </>
        }
      />

      {testAlertResult ? (
        <div className="flex items-start gap-3 border-t border-border py-3">
          <Activity className="mt-0.5 size-4 shrink-0 text-muted-foreground" aria-hidden="true" />
          <p className="m-0 text-app text-foreground">{testAlertResult}</p>
          <button
            type="button"
            onClick={() => setTestAlertResult(null)}
            className="ml-auto text-muted-foreground transition-colors hover:text-foreground"
            aria-label={tCommon('close')}
          >
            <X className="size-4" aria-hidden="true" />
          </button>
        </div>
      ) : null}

      {error ? <ErrorState title={t('errorTitle')} description={error} /> : null}

      <MonitoringStats health={healthStatus} readiness={readinessStatus} overview={overview} />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <RequestsPanel />
        <AlertsLedger alerts={alerts} />
      </div>

      <section className="flex flex-col gap-2">
        <h2 className="m-0 text-app font-semibold text-foreground">{tPanels('deploymentTitle')}</h2>
        <ServiceLedger health={healthStatus} readiness={readinessStatus} overview={overview} />
      </section>

      {overview && Object.keys(overview.database.by_source ?? {}).length > 0 ? (
        <section className="flex flex-col gap-2">
          <h2 className="m-0 text-app font-semibold text-foreground">{t('sources.title')}</h2>
          <SourceBreakdown bySource={overview.database.by_source} />
        </section>
      ) : null}
    </>
  );
}
