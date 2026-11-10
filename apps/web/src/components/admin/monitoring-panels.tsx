'use client';

import { useTranslations } from 'next-intl';

import { ChartFrame } from '@/components/ui/chart-frame';
import { Ledger, LedgerRow } from '@/components/ui/ledger';
import { MonoAnnotation, type MonoTone } from '@/components/ui/mono-annotation';
import { StatTile } from '@/components/ui/stat-tile';
import { cn } from '@/lib/utils';
import type {
  HealthStatus,
  MonitoringOverview,
  ReadinessStatus,
} from '@/lib/api/admin';

/**
 * The monitoring panels.
 *
 * The numbers of a deployment are stats, so they are stat tiles; the panel
 * that would hold a graph is a chart frame with its area held open; the
 * alerts are a list, so they are a ledger.
 *
 * Every number here comes from the API. A measurement the API does not
 * carry is not drawn - the panel says it has nothing to draw instead.
 */

/**
 * The alerts a deployment raises.
 *
 * The thresholds are the ones the deployment itself uses: a database that
 * answers too slowly, a cache that is colder than it should be, a service
 * that is not ready to answer at all.
 */
export interface MonitoringAlert {
  id: string;
  tone: MonoTone;
  /** The i18n key of the message. */
  messageKey: string;
  /** The i18n key of the threshold it broke. */
  thresholdKey: string;
  /** The values the message is interpolated with. */
  values: Record<string, string | number>;
}

/**
 * The alerts, computed from what the API carried.
 *
 * The function is pure so that it can be tested without a deployment: the
 * thresholds are the numbers, and the copy is looked up by the caller.
 */
export function buildAlerts(
  readiness: ReadinessStatus,
  overview: MonitoringOverview
): MonitoringAlert[] {
  const alerts: MonitoringAlert[] = [];

  if (readiness.database_latency_ms && readiness.database_latency_ms > 3000) {
    alerts.push({
      id: 'db-latency',
      tone: 'destructive',
      messageKey: 'alerts.dbLatency',
      thresholdKey: 'alerts.dbLatencyThreshold',
      values: { value: readiness.database_latency_ms },
    });
  }

  if (overview.cache?.hit_rate !== undefined && overview.cache.hit_rate < 20) {
    alerts.push({
      id: 'cache-hit-rate',
      tone: 'warning',
      messageKey: 'alerts.cacheHitRate',
      thresholdKey: 'alerts.cacheHitRateThreshold',
      values: { rate: overview.cache.hit_rate },
    });
  }

  if (readiness.overall === 'not_ready') {
    alerts.push({
      id: 'not-ready',
      tone: 'destructive',
      messageKey: 'alerts.notReady',
      thresholdKey: 'alerts.notReadyThreshold',
      values: {},
    });
  }

  if (readiness.database.includes('unhealthy')) {
    alerts.push({
      id: 'db-unhealthy',
      tone: 'destructive',
      messageKey: 'alerts.dbUnhealthy',
      thresholdKey: 'alerts.dbUnhealthyThreshold',
      values: {},
    });
  }

  if (readiness.llm.includes('unhealthy')) {
    alerts.push({
      id: 'llm-unhealthy',
      tone: 'destructive',
      messageKey: 'alerts.llmUnhealthy',
      thresholdKey: 'alerts.llmUnhealthyThreshold',
      values: {},
    });
  }

  if (readiness.redis.includes('unhealthy')) {
    alerts.push({
      id: 'redis-unhealthy',
      tone: 'warning',
      messageKey: 'alerts.redisUnhealthy',
      thresholdKey: 'alerts.redisUnhealthyThreshold',
      values: {},
    });
  }

  return alerts;
}

/** The five numbers of a deployment. */
export interface MonitoringStatsProps {
  health: HealthStatus | null;
  readiness: ReadinessStatus | null;
  overview: MonitoringOverview | null;
  className?: string;
}

export function MonitoringStats({ health, readiness, overview, className }: MonitoringStatsProps) {
  const t = useTranslations('pages.admin.monitoring.panels');
  const tStatus = useTranslations('pages.admin.monitoring.status');

  const healthTone: MonoTone =
    health?.status === 'healthy' ? 'success' : health?.status === 'degraded' ? 'warning' : 'destructive';
  const readinessTone: MonoTone = readiness?.overall === 'ready' ? 'success' : 'destructive';

  return (
    <div
      className={cn(
        'grid grid-cols-2 gap-x-6 gap-y-5 border-b border-border pb-5 md:grid-cols-3 xl:grid-cols-5',
        className
      )}
    >
      <StatTile
        value={
          <span
            className={cn(
              healthTone === 'success' && 'text-success',
              healthTone === 'warning' && 'text-warning',
              healthTone === 'destructive' && 'text-destructive'
            )}
          >
            {health ? tStatus(health.status) : '—'}
          </span>
        }
        label={t('health')}
        hint={health?.service}
      />

      <StatTile
        value={
          <span className={readinessTone === 'success' ? 'text-success' : 'text-destructive'}>
            {readiness ? tStatus(readiness.overall) : '—'}
          </span>
        }
        label={t('readiness')}
        hint={readiness?.database}
      />

      <StatTile
        value={
          readiness?.database_latency_ms !== undefined
            ? `${readiness.database_latency_ms} ms`
            : '—'
        }
        label={t('latency')}
        hint={t('latencyHint')}
      />

      <StatTile
        value={
          overview?.cache?.hit_rate !== undefined ? `${overview.cache.hit_rate.toFixed(1)}%` : '—'
        }
        label={t('cacheHitRate')}
        hint={
          overview?.cache?.hits !== undefined
            ? t('hitsMisses', {
                hits: (overview.cache.hits ?? 0).toLocaleString(),
                misses: (overview.cache.misses ?? 0).toLocaleString(),
              })
            : t('noCacheData')
        }
      />

      <StatTile
        value={overview ? overview.knowledge_store.documents.toLocaleString() : '—'}
        label={t('vectorIndex')}
        hint={
          overview
            ? t('chunks', { count: overview.knowledge_store.chunks.toLocaleString() })
            : undefined
        }
      />
    </div>
  );
}

/**
 * The panel that would hold the request series.
 *
 * The deployment does not expose a request series, so the frame holds its
 * area open and says so - an empty frame with a caption is honest, a drawn
 * line that nobody measured is not.
 */
export function RequestsPanel({ className }: { className?: string }) {
  const t = useTranslations('pages.admin.monitoring.panels');

  return (
    <ChartFrame
      title={t('requestsTitle')}
      caption={t('requestsCaption')}
      height={140}
      className={className}
    >
      <div className="flex h-full min-h-[140px] items-center justify-center">
        <p className="max-w-[360px] text-center text-annot text-muted-foreground">
          {t('requestsEmpty')}
        </p>
      </div>
    </ChartFrame>
  );
}

/** The alerts of a deployment: a list, so a ledger. */
export interface AlertsLedgerProps {
  alerts: MonitoringAlert[];
  className?: string;
}

export function AlertsLedger({ alerts, className }: AlertsLedgerProps) {
  const t = useTranslations('pages.admin.monitoring.panels');
  const tAlerts = useTranslations('pages.admin.monitoring');

  return (
    <section
      className={cn('flex flex-col overflow-hidden rounded-lg border border-border', className)}
    >
      <header className="border-b border-border px-4 py-2.5">
        <span className="text-app font-semibold text-foreground">{t('alertsTitle')}</span>
      </header>

      {alerts.length === 0 ? (
        <p className="px-4 py-4 text-annot text-muted-foreground">{t('alertsEmpty')}</p>
      ) : (
        <Ledger className="border-t-0">
          {alerts.map((alert) => (
            <LedgerRow
              key={alert.id}
              className="grid-cols-[10px_minmax(0,1fr)] gap-x-3 gap-y-1 border-b border-border px-4 py-3 last:border-b-0 md:items-center"
            >
              <span
                className={cn(
                  'mt-1 h-2 w-2 shrink-0 rounded-full md:mt-0',
                  alert.tone === 'destructive' && 'bg-destructive',
                  alert.tone === 'warning' && 'bg-warning',
                  alert.tone === 'success' && 'bg-success',
                  alert.tone === 'neutral' && 'bg-muted-foreground'
                )}
                aria-hidden="true"
              />
              <div className="min-w-0">
                <p className="text-app text-foreground">
                  {tAlerts(alert.messageKey, alert.values as never)}
                </p>
                <MonoAnnotation className="mt-0.5 block">
                  {tAlerts('alerts.threshold', { threshold: tAlerts(alert.thresholdKey) })}
                </MonoAnnotation>
              </div>
            </LedgerRow>
          ))}
        </Ledger>
      )}
    </section>
  );
}

/**
 * The details of the deployment.
 *
 * The tiles say how the deployment is; this says what it is - the service,
 * the version, the commit, the uptime, and what each dependency answers.
 */
export interface ServiceLedgerProps {
  health: HealthStatus | null;
  readiness: ReadinessStatus | null;
  overview: MonitoringOverview | null;
  className?: string;
}

export function ServiceLedger({ health, readiness, overview, className }: ServiceLedgerProps) {
  const t = useTranslations('pages.admin.monitoring.panels');

  const rows: Array<{ label: string; value: string }> = [];

  if (health) {
    rows.push({ label: t('service'), value: health.service });
    if (health.version) rows.push({ label: t('version'), value: health.version });
    if (health.git?.commit) rows.push({ label: t('commit'), value: health.git.commit.slice(0, 7) });
    if (health.uptime_seconds !== undefined) {
      rows.push({ label: t('uptime'), value: formatUptime(health.uptime_seconds) });
    }
  }
  if (readiness) {
    rows.push({ label: t('database'), value: readiness.database });
    rows.push({ label: t('redis'), value: readiness.redis });
    rows.push({ label: t('llm'), value: readiness.llm });
  }
  if (overview) {
    rows.push({ label: t('environment'), value: overview.environment });
    rows.push({
      label: t('provider'),
      value: `${overview.llm.default_provider} / ${overview.llm.default_model}`,
    });
  }

  if (rows.length === 0) return null;

  return (
    <Ledger className={className}>
      {rows.map((row) => (
        <LedgerRow
          key={row.label}
          className="grid-cols-[180px_minmax(0,1fr)] gap-x-4 gap-y-1 py-2.5 md:items-center"
        >
          <span className="text-annot text-muted-foreground">{row.label}</span>
          <MonoAnnotation className="truncate">{row.value}</MonoAnnotation>
        </LedgerRow>
      ))}
    </Ledger>
  );
}

/** The properties the catalogue holds, and where they came from. */
export interface SourceBreakdownProps {
  bySource: Record<string, number>;
  className?: string;
}

export function SourceBreakdown({ bySource, className }: SourceBreakdownProps) {
  const t = useTranslations('pages.admin.monitoring.panels');
  const entries = Object.entries(bySource ?? {});

  if (entries.length === 0) return null;

  return (
    <Ledger className={className}>
      <div className="hidden gap-4 pb-2 pt-2.5 text-annot text-muted-foreground md:grid md:grid-cols-[minmax(0,1fr)_160px]">
        <span>{t('sourceColumns.source')}</span>
        <span className="text-right">{t('sourceColumns.listings')}</span>
      </div>
      {entries.map(([source, count]) => (
        <LedgerRow
          key={source}
          className="grid-cols-[minmax(0,1fr)_160px] gap-x-4 gap-y-1 py-2.5 md:items-center"
        >
          <span className="truncate text-app text-foreground">{source}</span>
          <MonoAnnotation className="text-right">{count.toLocaleString()}</MonoAnnotation>
        </LedgerRow>
      ))}
    </Ledger>
  );
}

/** An uptime in hours and minutes. */
export function formatUptime(seconds: number): string {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  return `${hours}h ${minutes}m`;
}
