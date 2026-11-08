'use client';

import { useState, useEffect, useCallback } from 'react';
import { useTranslations } from 'next-intl';
import {
  Activity,
  AlertCircle,
  CheckCircle2,
  Database,
  Loader2,
  Pause,
  Play,
  RefreshCw,
  X,
  Zap,
  AlertTriangle,
  Clock,
  Gauge,
  ArrowRight,
} from 'lucide-react';
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
import { PageHeader } from '@/components/ui/page-header';
import { EmptyState } from '@/components/ui/states';

interface ErrorState {
  message: string;
  requestId?: string;
}

// Status badge component
function StatusBadge({ status }: { status: string }) {
  const statusConfig: Record<string, { bg: string; text: string; icon: React.ReactNode }> = {
    active: {
      bg: 'bg-success/20 dark:bg-success/30',
      text: 'text-success dark:text-success',
      icon: <CheckCircle2 className="w-3 h-3" />,
    },
    disabled: {
      bg: 'bg-muted dark:bg-muted',
      text: 'text-muted-foreground dark:text-muted-foreground',
      icon: <Pause className="w-3 h-3" />,
    },
    error: {
      bg: 'bg-destructive/20 dark:bg-destructive/30',
      text: 'text-destructive dark:text-destructive',
      icon: <AlertCircle className="w-3 h-3" />,
    },
    not_instantiated: {
      bg: 'bg-warning/20 dark:bg-warning/30',
      text: 'text-warning dark:text-warning',
      icon: <Clock className="w-3 h-3" />,
    },
    unknown: {
      bg: 'bg-muted dark:bg-muted',
      text: 'text-muted-foreground dark:text-muted-foreground',
      icon: <AlertTriangle className="w-3 h-3" />,
    },
  };

  const config = statusConfig[status] || statusConfig.unknown;

  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${config.bg} ${config.text}`}
    >
      {config.icon}
      {status.replace('_', ' ')}
    </span>
  );
}

// Health status badge
function HealthBadge({ status }: { status: string }) {
  const config: Record<string, { bg: string; text: string }> = {
    healthy: { bg: 'bg-success/20 dark:bg-success/30', text: 'text-success dark:text-success' },
    unhealthy: { bg: 'bg-destructive/20 dark:bg-destructive/30', text: 'text-destructive dark:text-destructive' },
    degraded: { bg: 'bg-warning/20 dark:bg-warning/30', text: 'text-warning dark:text-warning' },
    error: { bg: 'bg-destructive/20 dark:bg-destructive/30', text: 'text-destructive dark:text-destructive' },
  };

  const { bg, text } = config[status] || config.error;

  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${bg} ${text}`}>
      {status}
    </span>
  );
}

export default function ConnectorsPage() {
  const t = useTranslations('pages.admin.connectors');
  // Connectors list state
  const [connectors, setConnectors] = useState<MCPConnectorInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [edition, setEdition] = useState<string>('community');

  // Selected connector detail
  const [selectedConnector, setSelectedConnector] = useState<MCPConnectorDetailResponse | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);

  // Health check state
  const [healthResults, setHealthResults] = useState<Record<string, MCPConnectorHealthResponse>>({});
  const [checkingHealth, setCheckingHealth] = useState<Set<string>>(new Set());
  const [overallHealth, setOverallHealth] = useState<MCPHealthResponse | null>(null);
  const [checkingAllHealth, setCheckingAllHealth] = useState(false);

  // UI state
  const [error, setError] = useState<ErrorState | null>(null);

  // Load connectors
  const loadConnectors = useCallback(async () => {
    try {
      setLoading(true);
      const response = await listMCPConnectors();
      setConnectors(response.connectors);
      setEdition(response.edition);
    } catch (e) {
      console.error('Failed to load connectors:', e);
      setError(extractErrorState(e));
    } finally {
      setLoading(false);
    }
  }, []);

  // Load connectors on mount
  useEffect(() => {
    loadConnectors();
  }, [loadConnectors]);

  const extractErrorState = (err: unknown): ErrorState => {
    let message = 'Unknown error';
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
  };

  // Load connector detail
  const loadConnectorDetail = async (name: string) => {
    try {
      setLoadingDetail(true);
      const detail = await getMCPConnector(name);
      setSelectedConnector(detail);
    } catch (e) {
      setError(extractErrorState(e));
    } finally {
      setLoadingDetail(false);
    }
  };

  // Health check single connector
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

  // Health check all connectors
  const handleHealthCheckAll = async () => {
    setCheckingAllHealth(true);

    try {
      const result = await healthCheckAllMCPConnectors();
      setOverallHealth(result);
    } catch (e) {
      setError(extractErrorState(e));
    } finally {
      setCheckingAllHealth(false);
    }
  };

  return (
    <div className="container mx-auto px-4 py-8">
      {/* Header */}
      <PageHeader
        className="mb-8"
        title={t('title')}
        description={t('description')}
        actions={
          <div className="flex gap-2">
            <button
              type="button"
              className="px-4 py-2 bg-secondary text-secondary-foreground rounded hover:bg-secondary/80 flex items-center gap-2 focus-visible:outline-none focus-visible:outline-2 focus-visible:outline-ring/50"
              onClick={loadConnectors}
              disabled={loading}
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
              Refresh
            </button>
            <button
              type="button"
              className="px-4 py-2 bg-primary text-primary-foreground rounded hover:bg-primary/90 flex items-center gap-2 focus-visible:outline-none focus-visible:outline-2 focus-visible:outline-ring/50"
              onClick={handleHealthCheckAll}
              disabled={checkingAllHealth}
            >
              {checkingAllHealth ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Activity className="w-4 h-4" />
              )}
              Health Check All
            </button>
          </div>
        }
      >
        <span className="text-xs text-muted-foreground">Edition: {edition}</span>
      </PageHeader>

      {/* Overall Health Status */}
      {overallHealth && (
        <div className="mb-6 p-4 border rounded-lg">
          <div className="flex items-center justify-between mb-2">
            <h3 className="font-semibold">Overall Health Status</h3>
            <HealthBadge status={overallHealth.status} />
          </div>
          <div className="grid grid-cols-3 gap-4 text-sm">
            <div>
              <span className="text-muted-foreground">Connectors Checked:</span>{' '}
              {overallHealth.connectors_checked}
            </div>
            <div>
              <span className="text-muted-foreground">Edition:</span> {overallHealth.edition}
            </div>
            <div>
              <span className="text-muted-foreground">Timestamp:</span>{' '}
              {new Date(overallHealth.timestamp).toLocaleTimeString()}
            </div>
          </div>
        </div>
      )}

      {/* Error Display */}
      {error && (
        <div className="flex items-start gap-3 p-4 bg-destructive/10 text-destructive rounded mb-4">
          <AlertCircle className="w-5 h-5 shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="font-medium">Error</p>
            <p className="text-sm">{error.message}</p>
            {error.requestId && <p className="text-xs mt-1">Request ID: {error.requestId}</p>}
          </div>
          <button
            type="button"
            onClick={() => setError(null)}
            className="text-destructive/50 hover:text-destructive"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Connectors Grid */}
      {loading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 animate-spin mr-2" />
          Loading connectors...
        </div>
      ) : connectors.length === 0 ? (
        <EmptyState icon={Database} title="No connectors registered" />
      ) : (
        <div className="grid gap-4">
          {connectors.map((connector) => (
            <div
              key={connector.name}
              className="border rounded-lg p-4 hover:border-primary/50 transition-colors cursor-pointer"
              onClick={() => loadConnectorDetail(connector.name)}
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <h3 className="font-semibold">{connector.display_name}</h3>
                    <StatusBadge status={connector.status} />
                    {connector.accessible_in_ce && (
                      <span className="text-xs bg-info/20 dark:bg-info/30 text-info dark:text-info px-2 py-0.5 rounded">
                        CE
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-muted-foreground mb-2">{connector.description}</p>
                  <div className="flex flex-wrap gap-4 text-xs text-muted-foreground">
                    <span className="flex items-center gap-1">
                      <Database className="w-3 h-3" />
                      {connector.registered ? 'Registered' : 'Not Registered'}
                    </span>
                    <span className="flex items-center gap-1">
                      <Play className="w-3 h-3" />
                      {connector.has_instance ? 'Instantiated' : 'No Instance'}
                    </span>
                    {connector.requires_api_key && (
                      <span className="flex items-center gap-1">
                        <Zap className="w-3 h-3" />
                        API Key Required
                      </span>
                    )}
                    {connector.supports_streaming && (
                      <span className="flex items-center gap-1">
                        <Activity className="w-3 h-3" />
                        Streaming
                      </span>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {healthResults[connector.name] && (
                    <HealthBadge status={healthResults[connector.name].status} />
                  )}
                  <button
                    type="button"
                    className="p-2 hover:bg-secondary rounded focus-visible:outline-none focus-visible:outline-2 focus-visible:outline-ring/50"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleHealthCheck(connector.name);
                    }}
                    disabled={checkingHealth.has(connector.name)}
                  >
                    {checkingHealth.has(connector.name) ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <Activity className="w-4 h-4" />
                    )}
                  </button>
                  <ArrowRight className="w-4 h-4 text-muted-foreground" />
                </div>
              </div>

              {/* Health Check Results */}
              {healthResults[connector.name] && (
                <div className="mt-4 pt-4 border-t text-sm">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <span className="text-muted-foreground">Response Time:</span>{' '}
                      {healthResults[connector.name].response_time_ms?.toFixed(2) || 'N/A'}ms
                    </div>
                    <div>
                      <span className="text-muted-foreground">Success:</span>{' '}
                      {healthResults[connector.name].success ? 'Yes' : 'No'}
                    </div>
                  </div>
                  {healthResults[connector.name].errors.length > 0 && (
                    <div className="mt-2">
                      <span className="text-destructive font-medium">Errors:</span>
                      <ul className="list-disc list-inside text-xs mt-1">
                        {healthResults[connector.name].errors.map((err, i) => (
                          <li key={i}>{err}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Connector Detail Modal */}
      {selectedConnector && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-background rounded-lg max-w-2xl w-full max-h-[80vh] overflow-auto">
            <div className="sticky top-0 bg-background border-b p-4 flex items-center justify-between">
              <h2 className="text-xl font-bold">{selectedConnector.display_name}</h2>
              <button
                type="button"
                className="p-2 hover:bg-secondary rounded focus-visible:outline-none focus-visible:outline-2 focus-visible:outline-ring/50"
                onClick={() => setSelectedConnector(null)}
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {loadingDetail ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="w-8 h-8 animate-spin" />
              </div>
            ) : (
              <div className="p-4 space-y-6">
                {/* Basic Info */}
                <div>
                  <h3 className="font-semibold mb-2">Basic Information</h3>
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <span className="text-muted-foreground">Name:</span> {selectedConnector.name}
                    </div>
                    <div>
                      <span className="text-muted-foreground">Edition:</span> {selectedConnector.edition}
                    </div>
                    <div>
                      <span className="text-muted-foreground">Status:</span>{' '}
                      <StatusBadge status={selectedConnector.status} />
                    </div>
                    <div>
                      <span className="text-muted-foreground">Min Edition:</span>{' '}
                      {selectedConnector.min_edition}
                    </div>
                  </div>
                  <p className="text-sm text-muted-foreground mt-2">
                    {selectedConnector.description}
                  </p>
                  {selectedConnector.error_message && (
                    <div className="mt-2 p-2 bg-destructive/20 dark:bg-destructive/30 text-destructive dark:text-destructive rounded text-sm">
                      Error: {selectedConnector.error_message}
                    </div>
                  )}
                </div>

                {/* Capabilities */}
                <div>
                  <h3 className="font-semibold mb-2">Capabilities</h3>
                  <div className="flex flex-wrap gap-2">
                    {selectedConnector.requires_api_key && (
                      <span className="px-2 py-1 bg-warning/20 dark:bg-warning/30 text-warning dark:text-warning rounded text-xs">
                        API Key Required
                      </span>
                    )}
                    {selectedConnector.supports_streaming && (
                      <span className="px-2 py-1 bg-info/20 dark:bg-info/30 text-info dark:text-info rounded text-xs">
                        Streaming
                      </span>
                    )}
                    {selectedConnector.accessible_in_ce && (
                      <span className="px-2 py-1 bg-success/20 dark:bg-success/30 text-success dark:text-success rounded text-xs">
                        CE Accessible
                      </span>
                    )}
                    {selectedConnector.enabled ? (
                      <span className="px-2 py-1 bg-success/20 dark:bg-success/30 text-success dark:text-success rounded text-xs">
                        Enabled
                      </span>
                    ) : (
                      <span className="px-2 py-1 bg-muted dark:bg-muted text-muted-foreground dark:text-muted-foreground rounded text-xs">
                        Disabled
                      </span>
                    )}
                  </div>
                </div>

                {/* Rate Limit */}
                {selectedConnector.rate_limit && (
                  <div>
                    <h3 className="font-semibold mb-2 flex items-center gap-2">
                      <Gauge className="w-4 h-4" />
                      Rate Limit
                    </h3>
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <span className="text-muted-foreground">Requests/min:</span>{' '}
                        {selectedConnector.rate_limit.requests_per_minute}
                      </div>
                      <div>
                        <span className="text-muted-foreground">Burst Size:</span>{' '}
                        {selectedConnector.rate_limit.burst_size}
                      </div>
                      <div>
                        <span className="text-muted-foreground">Current Requests:</span>{' '}
                        {selectedConnector.rate_limit.current_requests}
                      </div>
                      <div>
                        <span className="text-muted-foreground">Remaining:</span>{' '}
                        {selectedConnector.rate_limit.remaining}
                      </div>
                    </div>
                  </div>
                )}

                {/* Instance Status */}
                {selectedConnector.instance_status && (
                  <div>
                    <h3 className="font-semibold mb-2">Instance Status</h3>
                    <pre className="text-xs bg-muted p-2 rounded overflow-auto">
                      {JSON.stringify(selectedConnector.instance_status, null, 2)}
                    </pre>
                  </div>
                )}

                {/* Config (sanitized) */}
                {selectedConnector.config && (
                  <div>
                    <h3 className="font-semibold mb-2">Configuration</h3>
                    <pre className="text-xs bg-muted p-2 rounded overflow-auto">
                      {JSON.stringify(selectedConnector.config, null, 2)}
                    </pre>
                  </div>
                )}

                {/* Health Check Actions */}
                <div className="flex gap-2 pt-4 border-t">
                  <button
                    type="button"
                    className="px-4 py-2 bg-primary text-primary-foreground rounded hover:bg-primary/90 flex items-center gap-2 focus-visible:outline-none focus-visible:outline-2 focus-visible:outline-ring/50"
                    onClick={() => handleHealthCheck(selectedConnector.name)}
                    disabled={checkingHealth.has(selectedConnector.name)}
                  >
                    {checkingHealth.has(selectedConnector.name) ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <Activity className="w-4 h-4" />
                    )}
                    Health Check
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
