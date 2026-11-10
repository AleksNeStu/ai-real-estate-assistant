'use client';

import { useTranslations } from 'next-intl';

import { Ledger, LedgerRow } from '@/components/ui/ledger';
import { MonoAnnotation, type MonoTone } from '@/components/ui/mono-annotation';
import { cn } from '@/lib/utils';
import type { DataSource, DataSourceType } from '@/lib/types';

/**
 * The source ledger.
 *
 * The sources are a list, so the list is a ledger: one ink rule opens it and
 * every row is a source - what it is, how many listings it brought, when it
 * last ran, and the three things an administrator can do with it.
 *
 * The portal adapters get their own ledger below it: a portal that is not
 * configured is a different thing from a source, and the two are read
 * separately.
 */

/** The i18n key of a source kind. */
export function sourceKindKey(sourceType: DataSourceType): string {
  switch (sourceType) {
    case 'file_upload':
      return 'fileUpload';
    case 'url':
      return 'url';
    case 'portal_api':
      return 'portalApi';
    case 'json':
      return 'json';
    default:
      return sourceType;
  }
}

/** How long ago the source last ran, and the number the copy needs. */
export function sourceLastSync(
  source: DataSource,
  now: number
): { label: string; tone: MonoTone; minutes?: number; hours?: number; days?: number } {
  if (!source.last_sync_at) return { label: 'never', tone: 'neutral' };
  const then = new Date(source.last_sync_at).getTime();
  if (Number.isNaN(then)) return { label: 'never', tone: 'neutral' };

  const minutes = Math.floor((now - then) / 60000);
  if (minutes < 1) return { label: 'justNow', tone: 'neutral' };
  if (minutes < 60) return { label: 'minutesAgo', tone: 'neutral', minutes };
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return { label: 'hoursAgo', tone: 'neutral', hours };
  return { label: 'daysAgo', tone: 'neutral', days: Math.floor(hours / 24) };
}

export interface SourceLedgerProps {
  sources: DataSource[];
  onSync?: (source: DataSource) => void;
  onEdit?: (source: DataSource) => void;
  onDelete?: (source: DataSource) => void;
  /** The sources a sync is running for right now. */
  syncingIds?: Set<string>;
  /**
   * The reference point for "how long ago", in milliseconds. It is null until
   * the caller has measured the clock, and a row then carries the absolute
   * date instead of a relative one - a relative time computed against an
   * unknown clock is a wrong number, not a missing one.
   */
  now: number | null;
  className?: string;
}

export function SourceLedger({
  sources,
  onSync,
  onEdit,
  onDelete,
  syncingIds,
  now,
  className,
}: SourceLedgerProps) {
  const t = useTranslations('pages.admin.dataSources.ledger');
  const tSources = useTranslations('pages.admin.dataSources');

  if (sources.length === 0) {
    return <p className="text-annot text-muted-foreground">{tSources('noSources')}</p>;
  }

  return (
    <Ledger className={className}>
      <div className="hidden gap-4 pb-2 pt-2.5 text-annot text-muted-foreground md:grid md:grid-cols-[minmax(0,1.4fr)_140px_140px_160px_170px]">
        <span>{t('columns.source')}</span>
        <span>{t('columns.kind')}</span>
        <span>{t('columns.listings')}</span>
        <span>{t('columns.lastSync')}</span>
        <span className="text-right">{t('columns.actions')}</span>
      </div>

      {sources.map((source) => {
        const syncing = syncingIds?.has(source.id) ?? false;
        const lastSync = now === null ? null : sourceLastSync(source, now);
        return (
          <LedgerRow
            key={source.id}
            className="grid-cols-1 gap-x-4 gap-y-1.5 md:grid-cols-[minmax(0,1.4fr)_140px_140px_160px_170px] md:items-center"
          >
            <Cell label={t('columns.source')}>
              <span className="text-app font-medium text-foreground">{source.name}</span>
              {source.last_error ? (
                <MonoAnnotation tone="destructive" className="mt-0.5 block">
                  {source.last_error}
                </MonoAnnotation>
              ) : source.auto_sync_enabled && source.sync_schedule ? (
                <MonoAnnotation className="mt-0.5 block">
                  {tSources('autoSync', { schedule: source.sync_schedule })}
                </MonoAnnotation>
              ) : null}
            </Cell>

            <Cell label={t('columns.kind')}>
              <MonoAnnotation>{tSources(`sourceTypes.${sourceKindKey(source.source_type)}`)}</MonoAnnotation>
              {source.status !== 'active' ? (
                <MonoAnnotation tone="warning" className="mt-0.5 block">
                  {tSources(`status.${source.status}`)}
                </MonoAnnotation>
              ) : null}
            </Cell>

            <Cell label={t('columns.listings')}>
              <MonoAnnotation className="font-medium">
                {source.total_records.toLocaleString()}
              </MonoAnnotation>
            </Cell>

            <Cell label={t('columns.lastSync')}>
              {lastSync === null ? (
                <MonoAnnotation>
                  {source.last_sync_at
                    ? new Date(source.last_sync_at).toLocaleDateString()
                    : t('never')}
                </MonoAnnotation>
              ) : (
                <MonoAnnotation tone={lastSync.tone}>
                  {lastSync.label === 'never'
                    ? t('never')
                    : tSources(lastSync.label, {
                        count: lastSync.minutes ?? lastSync.hours ?? lastSync.days ?? 0,
                      })}
                </MonoAnnotation>
              )}
            </Cell>

            <Cell label={t('columns.actions')} className="md:justify-end">
              <div className="flex items-center justify-end gap-3">
                {onSync ? (
                  <button
                    type="button"
                    onClick={() => onSync(source)}
                    disabled={syncing}
                    className="rounded-sm text-app font-medium text-foreground transition-colors hover:underline disabled:opacity-50"
                  >
                    {syncing ? t('syncing') : t('actions.sync')}
                  </button>
                ) : null}
                {onEdit ? (
                  <button
                    type="button"
                    onClick={() => onEdit(source)}
                    className="rounded-sm text-app text-muted-foreground transition-colors hover:text-foreground hover:underline"
                  >
                    {t('actions.edit')}
                  </button>
                ) : null}
                {onDelete ? (
                  <button
                    type="button"
                    onClick={() => onDelete(source)}
                    className="rounded-sm text-app text-muted-foreground transition-colors hover:text-foreground hover:underline"
                  >
                    {t('actions.delete')}
                  </button>
                ) : null}
              </div>
            </Cell>
          </LedgerRow>
        );
      })}
    </Ledger>
  );
}

/**
 * The portal ledger.
 *
 * A portal is a place the deployment can fetch from. The row says whether it
 * is configured, whether it wants a key, and how many listings ever came
 * through it - a portal that was never fetched says so.
 */
export interface PortalLedgerProps {
  adapters: Array<{
    name: string;
    display_name: string;
    configured: boolean;
    has_api_key: boolean;
  }>;
  /** The data sources the deployment has, so the fetched count is real. */
  sources: DataSource[];
  className?: string;
}

export function PortalLedger({ adapters, sources, className }: PortalLedgerProps) {
  const t = useTranslations('pages.admin.dataSources.ledger');

  if (adapters.length === 0) {
    return <p className="text-annot text-muted-foreground">{t('portals.none')}</p>;
  }

  return (
    <Ledger className={className}>
      <div className="hidden gap-4 pb-2 pt-2.5 text-annot text-muted-foreground md:grid md:grid-cols-[minmax(0,1.4fr)_160px_140px]">
        <span>{t('portals.columns.portal')}</span>
        <span>{t('portals.columns.state')}</span>
        <span>{t('portals.columns.fetched')}</span>
      </div>

      {adapters.map((adapter) => {
        const fetched = sources
          .filter((source) => source.config?.portal === adapter.name)
          .reduce((sum, source) => sum + (source.total_records ?? 0), 0);
        // Three states, and the middle one matters: a portal that is
        // configured but carries no key cannot fetch anything, and saying
        // "configured" would overstate what the deployment can do.
        const state = !adapter.configured
          ? 'notConfigured'
          : adapter.has_api_key
            ? 'configured'
            : 'needsKey';

        return (
          <LedgerRow
            key={adapter.name}
            className="grid-cols-1 gap-x-4 gap-y-1.5 md:grid-cols-[minmax(0,1.4fr)_160px_140px] md:items-center"
          >
            <Cell label={t('portals.columns.portal')}>
              <span className="text-app font-medium text-foreground">
                {adapter.display_name || adapter.name}
              </span>
              <MonoAnnotation className="mt-0.5 block">{adapter.name}</MonoAnnotation>
            </Cell>

            <Cell label={t('portals.columns.state')}>
              <MonoAnnotation
                tone={state === 'configured' ? 'success' : 'warning'}
                className="font-medium"
              >
                {t(`portals.${state}`)}
              </MonoAnnotation>
            </Cell>

            <Cell label={t('portals.columns.fetched')}>
              <MonoAnnotation>
                {fetched > 0 ? fetched.toLocaleString() : t('portals.never')}
              </MonoAnnotation>
            </Cell>
          </LedgerRow>
        );
      })}
    </Ledger>
  );
}

/**
 * A cell of the ledger.
 *
 * On a wide screen the column header says what the cell is; on a narrow one
 * the header is gone, so the cell carries its own label.
 */
function Cell({
  label,
  children,
  className,
}: {
  label: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={cn('flex min-w-0 flex-col gap-0.5 md:block', className)}>
      <span className="text-annot text-muted-foreground md:hidden">{label}</span>
      {children}
    </div>
  );
}
