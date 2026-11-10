'use client';

import { useState, useEffect, useCallback } from 'react';
import { useTranslations } from 'next-intl';
import { Loader2, X, Activity, RefreshCw } from 'lucide-react';

import { ConnectorLedger } from '@/components/admin/connector-ledger';
import { Button } from '@/components/ui/button';
import { MonoAnnotation } from '@/components/ui/mono-annotation';
import { SectionHeader } from '@/components/ui/page-header';
import { EmptyState, ErrorState, LoadingState } from '@/components/ui/states';
import {
  listMCPConnectors,
  getMCPConnector,
  healthCheckMCPConnector,
  healthCheckAllMCPConnectors,
  ApiError,
} from '@/lib/api';
import type {
  MCPConnectorInfo,
  MCPConnectorDetailResponse,
  MCPConnectorHealthResponse,
  MCPHealthResponse,
} from '@/lib/types';

interface ErrorStateValue {
  message: string;
  requestId?: string;
}

function extractErrorState(err: unknown, fallbackMessage: string): ErrorStateValue {
  let message = fallbackMessage;
  let requestId: string | undefined = undefined;

  if (err instanceof ApiError) {
    message = err.message;
    requestId = err.request_id;
  } else if (err instanceof Error) {
    message = err.message;
  } else {
    message = String(err);
  }

  return { message, requestId };
}

/**
 * The connectors tab.
 *
 * The connectors are a list, so the tab is a ledger: every row is a
 * connector with its health and its state, and the health check is the one
 * action the tab offers. The detail of a connector opens beside the ledger.
 */
export default function ConnectorsPage() {
  const t = useTranslations('pages.admin.connectors');
  const tLedger = useTranslations('pages.admin.connectors.ledger');
  const tCommon = useTranslations('common');
  const tError = useTranslations('error');

  const [connectors, setConnectors] = useState<MCPConnectorInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [edition, setEdition] = useState<string>('community');

  const [selectedConnector, setSelectedConnector] = useState<MCPConnectorDetailResponse | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);

  const [healthResults, setHealthResults] = useState<Record<string, MCPConnectorHealthResponse>>({});
  const [checkingHealth, setCheckingHealth] = useState<Set<string>>(new Set());
  const [overallHealth, setOverallHealth] = useState<MCPHealthResponse | null>(null);
  const [checkingAllHealth, setCheckingAllHealth] = useState(false);

  const [error, setError] = useState<ErrorStateValue | null>(null);

  const loadConnectors = useCallback(async () => {
    try {
      setLoading(true);
      const response = await listMCPConnectors();
      setConnectors(response.connectors);
      setEdition(response.edition);
    } catch (e) {
      console.error(t('errors.load'), e);
      setError(extractErrorState(e, tError('generic')));
    } finally {
      setLoading(false);
    }
  }, [t, tError]);

  useEffect(() => {
    loadConnectors();
  }, [loadConnectors]);

  const loadConnectorDetail = async (name: string) => {
    try {
      setLoadingDetail(true);
      const detail = await getMCPConnector(name);
      setSelectedConnector(detail);
    } catch (e) {
      setError(extractErrorState(e, tError('generic')));
    } finally {
      setLoadingDetail(false);
    }
  };

  const handleHealthCheck = async (name: string) => {
    setCheckingHealth((prev) => new Set(prev).add(name));

    try {
      const result = await healthCheckMCPConnector(name);
      setHealthResults((prev) => ({ ...prev, [name]: result }));
    } catch (e) {
      setHealthResults((prev) => ({
        ...prev,
        [name]: {
          name,
          status: 'error',
          success: false,
          errors: [e instanceof Error ? e.message : String(e)],
          warnings: [],
          timestamp: new Date().toISOString(),
        },
      }));
    } finally {
      setCheckingHealth((prev) => {
        const next = new Set(prev);
        next.delete(name);
        return next;
      });
    }
  };

  const handleHealthCheckAll = async () => {
    setCheckingAllHealth(true);

    try {
      const result = await healthCheckAllMCPConnectors();
      setOverallHealth(result);
      setHealthResults((prev) => {
        const next = { ...prev };
        for (const [name, value] of Object.entries(result.results ?? {})) {
          const existing = next[name];
          next[name] = {
            name,
            status: value.success ? 'healthy' : 'unhealthy',
            success: value.success,
            errors: value.errors ?? [],
            warnings: [],
            timestamp: result.timestamp,
            response_time_ms: existing?.response_time_ms,
          };
        }
        return next;
      });
    } catch (e) {
      setError(extractErrorState(e, tError('generic')));
    } finally {
      setCheckingAllHealth(false);
    }
  };

  return (
    <>
      <SectionHeader
        title={tLedger('title')}
        description={t('description')}
        actions={
          <>
            <Button
              variant="outline"
              size="sm"
              onClick={loadConnectors}
              disabled={loading}
            >
              <RefreshCw className={`mr-2 size-4 ${loading ? 'animate-spin' : ''}`} aria-hidden="true" />
              {tCommon('refresh')}
            </Button>
            <Button size="sm" onClick={handleHealthCheckAll} disabled={checkingAllHealth}>
              {checkingAllHealth ? (
                <Loader2 className="mr-2 size-4 animate-spin" aria-hidden="true" />
              ) : (
                <Activity className="mr-2 size-4" aria-hidden="true" />
              )}
              {t('healthCheckAll')}
            </Button>
          </>
        }
      />

      <MonoAnnotation>{t('edition', { edition })}</MonoAnnotation>

      {overallHealth ? (
        <div className="flex flex-wrap items-center gap-x-6 gap-y-2 border-b border-border pb-4">
          <MonoAnnotation tone={overallHealth.status === 'healthy' ? 'success' : 'warning'}>
            {tLedger(`health.${overallHealth.status === 'healthy' ? 'healthy' : 'unhealthy'}`)}
          </MonoAnnotation>
          <MonoAnnotation>
            {t('overall.connectorsChecked')} {overallHealth.connectors_checked}
          </MonoAnnotation>
          <MonoAnnotation>{t('overall.edition')} {overallHealth.edition}</MonoAnnotation>
          <MonoAnnotation>
            {t('overall.timestamp')} {new Date(overallHealth.timestamp).toLocaleTimeString()}
          </MonoAnnotation>
        </div>
      ) : null}

      {error ? (
        <ErrorState
          title={tCommon('error')}
          description={
            error.requestId ? `${error.message} · ${t('requestId', { id: error.requestId })}` : error.message
          }
          action={
            <button
              type="button"
              onClick={() => setError(null)}
              className="text-muted-foreground transition-colors hover:text-foreground"
              aria-label={tCommon('close')}
            >
              <X className="size-4" aria-hidden="true" />
            </button>
          }
        />
      ) : null}

      {loading ? (
        <LoadingState rows={4} />
      ) : connectors.length === 0 ? (
        <EmptyState title={t('empty.title')} />
      ) : (
        <ConnectorLedger
          connectors={connectors}
          health={healthResults}
          checking={checkingHealth}
          onCheck={(connector) => handleHealthCheck(connector.name)}
          onOpen={(connector) => loadConnectorDetail(connector.name)}
        />
      )}

      {selectedConnector ? (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
          role="dialog"
          aria-modal="true"
          aria-labelledby="connector-detail-title"
        >
          <div className="max-h-[80vh] w-full max-w-2xl overflow-auto rounded-lg bg-background">
            <div className="sticky top-0 flex items-center justify-between border-b border-border bg-background p-4">
              <h2 id="connector-detail-title" className="m-0 text-app font-semibold text-foreground">
                {selectedConnector.display_name}
              </h2>
              <button
                type="button"
                className="text-muted-foreground transition-colors hover:text-foreground"
                onClick={() => setSelectedConnector(null)}
                aria-label={tCommon('close')}
              >
                <X className="size-4" aria-hidden="true" />
              </button>
            </div>

            {loadingDetail ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="size-6 animate-spin" aria-hidden="true" />
              </div>
            ) : (
              <div className="flex flex-col gap-6 p-4">
                <div className="flex flex-col gap-2">
                  <h3 className="m-0 text-app font-semibold text-foreground">
                    {t('detail.basicInfo')}
                  </h3>
                  <div className="grid grid-cols-2 gap-4 text-app">
                    <DetailRow label={t('detail.name')} value={selectedConnector.name} />
                    <DetailRow label={t('detail.edition')} value={selectedConnector.edition} />
                    <DetailRow label={t('detail.status')} value={selectedConnector.status} />
                    <DetailRow label={t('detail.minEdition')} value={selectedConnector.min_edition} />
                  </div>
                  <p className="m-0 text-app text-muted-foreground">{selectedConnector.description}</p>
                  {selectedConnector.error_message ? (
                    <p className="m-0 text-app text-destructive">
                      {t('detail.error', { message: selectedConnector.error_message })}
                    </p>
                  ) : null}
                </div>

                {selectedConnector.rate_limit ? (
                  <div className="flex flex-col gap-2">
                    <h3 className="m-0 text-app font-semibold text-foreground">{t('detail.rateLimit')}</h3>
                    <div className="grid grid-cols-2 gap-4 text-app">
                      <DetailRow
                        label={t('detail.requestsPerMin')}
                        value={String(selectedConnector.rate_limit.requests_per_minute)}
                      />
                      <DetailRow
                        label={t('detail.burstSize')}
                        value={String(selectedConnector.rate_limit.burst_size)}
                      />
                      <DetailRow
                        label={t('detail.currentRequests')}
                        value={String(selectedConnector.rate_limit.current_requests)}
                      />
                      <DetailRow
                        label={t('detail.remaining')}
                        value={String(selectedConnector.rate_limit.remaining)}
                      />
                    </div>
                  </div>
                ) : null}

                {selectedConnector.instance_status ? (
                  <div className="flex flex-col gap-2">
                    <h3 className="m-0 text-app font-semibold text-foreground">
                      {t('detail.instanceStatus')}
                    </h3>
                    <pre className="m-0 overflow-auto rounded-md bg-muted p-2 font-mono text-[12px]">
                      {JSON.stringify(selectedConnector.instance_status, null, 2)}
                    </pre>
                  </div>
                ) : null}

                {selectedConnector.config ? (
                  <div className="flex flex-col gap-2">
                    <h3 className="m-0 text-app font-semibold text-foreground">
                      {t('detail.configuration')}
                    </h3>
                    <pre className="m-0 overflow-auto rounded-md bg-muted p-2 font-mono text-[12px]">
                      {JSON.stringify(selectedConnector.config, null, 2)}
                    </pre>
                  </div>
                ) : null}

                <div className="flex gap-2 border-t border-border pt-4">
                  <Button
                    onClick={() => handleHealthCheck(selectedConnector.name)}
                    disabled={checkingHealth.has(selectedConnector.name)}
                  >
                    {checkingHealth.has(selectedConnector.name) ? (
                      <Loader2 className="mr-2 size-4 animate-spin" aria-hidden="true" />
                    ) : (
                      <Activity className="mr-2 size-4" aria-hidden="true" />
                    )}
                    {t('healthCheck')}
                  </Button>
                </div>
              </div>
            )}
          </div>
        </div>
      ) : null}
    </>
  );
}

/** One labelled value of the connector's detail. */
function DetailRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-3">
      <span className="text-muted-foreground">{label}</span>
      <MonoAnnotation className="truncate">{value}</MonoAnnotation>
    </div>
  );
}
