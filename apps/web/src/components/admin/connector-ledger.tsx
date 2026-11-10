'use client';

import { useTranslations } from 'next-intl';

import { Ledger, LedgerRow } from '@/components/ui/ledger';
import { MonoAnnotation, type MonoTone } from '@/components/ui/mono-annotation';
import { cn } from '@/lib/utils';
import type { MCPConnectorHealthResponse, MCPConnectorInfo } from '@/lib/types';

/**
 * The connector ledger.
 *
 * The connectors are a list, so the list is a ledger: one ink rule opens it
 * and every row is a connector - what it does, how it answers, and whether
 * it is turned on at all.
 *
 * The health of a connector is what the last health check said. Before a
 * check has run the row says so, in zinc - it does not claim a health it
 * has not measured.
 */

/** What the deployment did with the connector. */
export type ConnectorState = 'enabled' | 'disabled' | 'notConfigured' | 'needsKey';

/**
 * The state of a connector, from what the API carries.
 *
 * A connector that is not registered, or that has no instance, is not
 * configured. A connector that wants an API key and is not enabled is
 * waiting for a key. The rest is either on or off.
 */
export function connectorState(connector: MCPConnectorInfo): ConnectorState {
  if (!connector.registered || !connector.has_instance) return 'notConfigured';
  if (connector.requires_api_key && !connector.enabled) return 'needsKey';
  return connector.enabled ? 'enabled' : 'disabled';
}

/** The tone a state carries. */
export function connectorStateTone(state: ConnectorState): MonoTone {
  switch (state) {
    case 'enabled':
      return 'success';
    case 'needsKey':
    case 'notConfigured':
      return 'warning';
    case 'disabled':
      return 'neutral';
    default:
      return 'neutral';
  }
}

/**
 * The health of a connector, from the last health check.
 *
 * Without a check there is no health to report, so the row says that the
 * connector has not been checked yet.
 */
export function connectorHealth(
  connector: MCPConnectorInfo,
  health?: MCPConnectorHealthResponse
): { label: string; tone: MonoTone } {
  if (health) {
    if (health.status === 'healthy') return { label: 'healthy', tone: 'success' };
    if (health.status === 'unhealthy') return { label: 'unhealthy', tone: 'destructive' };
    return { label: 'error', tone: 'destructive' };
  }
  if (connector.status === 'error') return { label: 'error', tone: 'destructive' };
  return { label: 'notChecked', tone: 'neutral' };
}

export interface ConnectorLedgerProps {
  connectors: MCPConnectorInfo[];
  /** The health of the connectors that have been checked. */
  health?: Record<string, MCPConnectorHealthResponse>;
  /** The connectors a health check is running for right now. */
  checking?: Set<string>;
  onCheck?: (connector: MCPConnectorInfo) => void;
  onOpen?: (connector: MCPConnectorInfo) => void;
  className?: string;
}

export function ConnectorLedger({
  connectors,
  health,
  checking,
  onCheck,
  onOpen,
  className,
}: ConnectorLedgerProps) {
  const t = useTranslations('pages.admin.connectors.ledger');

  if (connectors.length === 0) {
    return <p className="text-annot text-muted-foreground">{t('empty')}</p>;
  }

  return (
    <Ledger className={className}>
      <div className="hidden gap-4 pb-2 pt-2.5 text-annot text-muted-foreground md:grid md:grid-cols-[minmax(0,1.2fr)_minmax(0,2fr)_160px_140px_120px]">
        <span>{t('columns.connector')}</span>
        <span>{t('columns.purpose')}</span>
        <span>{t('columns.health')}</span>
        <span>{t('columns.state')}</span>
        <span className="text-right">{t('columns.actions')}</span>
      </div>

      {connectors.map((connector) => {
        const state = connectorState(connector);
        const healthResult = health?.[connector.name];
        const healthLabel = connectorHealth(connector, healthResult);
        const isChecking = checking?.has(connector.name) ?? false;

        return (
          <LedgerRow
            key={connector.name}
            className="grid-cols-1 gap-x-4 gap-y-1.5 md:grid-cols-[minmax(0,1.2fr)_minmax(0,2fr)_160px_140px_120px] md:items-center"
          >
            <Cell label={t('columns.connector')}>
              <button
                type="button"
                onClick={() => onOpen?.(connector)}
                className="truncate text-left text-app font-medium text-foreground transition-colors hover:underline"
              >
                {connector.display_name || connector.name}
              </button>
              <MonoAnnotation className="mt-0.5 block">{connector.name}</MonoAnnotation>
            </Cell>

            <Cell label={t('columns.purpose')}>
              <span className="text-app text-muted-foreground">{connector.description}</span>
              {connector.error_message ? (
                <MonoAnnotation tone="destructive" className="mt-0.5 block">
                  {connector.error_message}
                </MonoAnnotation>
              ) : null}
            </Cell>

            <Cell label={t('columns.health')}>
              <span className="flex items-center gap-2">
                <span
                  className={cn(
                    'h-[7px] w-[7px] shrink-0 rounded-full',
                    healthLabel.tone === 'success' && 'bg-success',
                    healthLabel.tone === 'destructive' && 'bg-destructive',
                    healthLabel.tone === 'warning' && 'bg-warning',
                    healthLabel.tone === 'neutral' && 'bg-muted-foreground'
                  )}
                  aria-hidden="true"
                />
                <MonoAnnotation tone={healthLabel.tone}>{t(`health.${healthLabel.label}`)}</MonoAnnotation>
              </span>
              {healthResult?.response_time_ms !== undefined ? (
                <MonoAnnotation className="mt-0.5 block">
                  {t('responseTime', { value: healthResult.response_time_ms.toFixed(2) })}
                </MonoAnnotation>
              ) : null}
            </Cell>

            <Cell label={t('columns.state')}>
              <MonoAnnotation tone={connectorStateTone(state)} className="font-medium">
                {t(`state.${state}`)}
              </MonoAnnotation>
              {state === 'needsKey' ? (
                <MonoAnnotation tone="warning" className="mt-0.5 block">
                  {t('needsKeyNote')}
                </MonoAnnotation>
              ) : null}
            </Cell>

            <Cell label={t('columns.actions')} className="md:justify-end">
              <div className="flex items-center justify-end">
                {onCheck ? (
                  <button
                    type="button"
                    onClick={() => onCheck(connector)}
                    disabled={isChecking}
                    className="rounded-sm text-app font-medium text-foreground transition-colors hover:underline disabled:opacity-50"
                  >
                    {isChecking ? t('checking') : t('actions.check')}
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
