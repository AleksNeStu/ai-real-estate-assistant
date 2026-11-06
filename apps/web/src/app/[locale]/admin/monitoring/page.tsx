'use client';

import { useState, useEffect } from 'react';
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  Database,
  HardDrive,
  Loader2,
  RefreshCw,
  Server,
  Zap,
  X,
} from 'lucide-react';
import {
  getHealthStatus,
  getReadinessStatus,
  getMonitoringOverview,
  sendTestAlert,
  type HealthStatus,
  type ReadinessStatus,
  type MonitoringOverview,
} from '@/lib/api/admin';

interface ChartDataPoint {
  timestamp: string;
  value: number;
}

interface Alert {
  type: 'error' | 'warning' | 'info';
  message: string;
  threshold: string;
}

export default function MonitoringPage() {
  // Data state
  const [healthStatus, setHealthStatus] = useState<HealthStatus | null>(null);
  const [readinessStatus, setReadinessStatus] = useState<ReadinessStatus | null>(null);
  const [overview, setOverview] = useState<MonitoringOverview | null>(null);

  // UI state
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [refreshing, setRefreshing] = useState(false);
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date());

  // Test alert state
  const [testAlertLoading, setTestAlertLoading] = useState(false);
  const [testAlertResult, setTestAlertResult] = useState<string | null>(null);

  // Simulated time-series data for charts (in production, this would come from metrics endpoint)
  const [requestRateData, setRequestRateData] = useState<ChartDataPoint[]>([]);
  const [errorRateData, setErrorRateData] = useState<ChartDataPoint[]>([]);
  const [responseTimeData, setResponseTimeData] = useState<ChartDataPoint[]>([]);

  // Load all monitoring data
  const loadMonitoringData = async () => {
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

      // Check for alerts based on thresholds
      checkAlerts(readiness, overviewData);
    } catch (e) {
      console.error('Failed to load monitoring data:', e);
      setError(e instanceof Error ? e.message : 'Failed to load monitoring data');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  // Check for alerts based on thresholds
  const checkAlerts = (readiness: ReadinessStatus, overview: MonitoringOverview) => {
    const newAlerts: Alert[] = [];

    // Check database latency
    if (readiness.database_latency_ms && readiness.database_latency_ms > 3000) {
      newAlerts.push({
        type: 'error',
        message: `High database latency: ${readiness.database_latency_ms}ms`,
        threshold: 'P95 latency >3s',
      });
    }

    // Check cache hit rate
    if (overview.cache?.hit_rate !== undefined && overview.cache.hit_rate < 20) {
      newAlerts.push({
        type: 'warning',
        message: `Low cache hit rate: ${overview.cache.hit_rate}%`,
        threshold: 'Hit rate <20%',
      });
    }

    // Check overall readiness
    if (readiness.overall === 'not_ready') {
      newAlerts.push({
        type: 'error',
        message: 'Service is not ready to handle requests',
        threshold: 'Overall readiness',
      });
    }

    // Check database health
    if (readiness.database.includes('unhealthy')) {
      newAlerts.push({
        type: 'error',
        message: 'Database connection is unhealthy',
        threshold: 'Database health',
      });
    }

    // Check LLM health
    if (readiness.llm.includes('unhealthy')) {
      newAlerts.push({
        type: 'error',
        message: 'LLM provider is unhealthy',
        threshold: 'LLM health',
      });
    }

    // Check Redis health
    if (readiness.redis.includes('unhealthy')) {
      newAlerts.push({
        type: 'warning',
        message: 'Redis cache is unhealthy',
        threshold: 'Redis health',
      });
    }

    setAlerts(newAlerts);
  };

  // Initial load and auto-refresh
  useEffect(() => {
    loadMonitoringData();

    // Auto-refresh every 30 seconds
    const interval = setInterval(() => {
      setRefreshing(true);
      loadMonitoringData();
    }, 30000);

    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Generate simulated chart data (for demo purposes)
  useEffect(() => {
    const now = Date.now();
    const generateData = (baseValue: number, variance: number) => {
      // nosemgrep: weak-random.random — mock dashboard data, not security-sensitive
      return Array.from({ length: 20 }, (_, i) => ({
        timestamp: new Date(now - (19 - i) * 60000).toISOString(),
        value: Math.round(baseValue + (Math.random() - 0.5) * variance), // nosemgrep: weak-random.random
      }));
    };

    setRequestRateData(generateData(50, 20));
    setErrorRateData(generateData(2, 3));
    setResponseTimeData(generateData(200, 100));
  }, []);

  // Handle manual refresh
  const handleRefresh = () => {
    setRefreshing(true);
    loadMonitoringData();
  };

  // Handle test alert
  const handleTestAlert = async () => {
    setTestAlertLoading(true);
    setTestAlertResult(null);
    try {
      const result = await sendTestAlert();
      setTestAlertResult(result.message);
      setTimeout(() => setTestAlertResult(null), 5000);
    } catch (e) {
      setTestAlertResult(e instanceof Error ? e.message : 'Failed to send test alert');
      setTimeout(() => setTestAlertResult(null), 5000);
    } finally {
      setTestAlertLoading(false);
    }
  };

  // Status badge component
  const StatusBadge = ({
    status,
  }: {
    status: 'healthy' | 'unhealthy' | 'ready' | 'not_ready' | 'degraded';
  }) => {
    const colors = {
      healthy: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-100',
      unhealthy: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-100',
      ready: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-100',
      not_ready: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-100',
      degraded: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-100',
    };

    const icons = {
      healthy: <CheckCircle2 className="w-3 h-3 inline mr-1" />,
      unhealthy: <AlertTriangle className="w-3 h-3 inline mr-1" />,
      ready: <CheckCircle2 className="w-3 h-3 inline mr-1" />,
      not_ready: <AlertTriangle className="w-3 h-3 inline mr-1" />,
      degraded: <AlertTriangle className="w-3 h-3 inline mr-1" />,
    };

    return (
      <span
        className={`inline-flex items-center px-2 py-1 rounded text-xs font-medium ${colors[status]}`}
      >
        {icons[status]}
        {status.replace('_', ' ')}
      </span>
    );
  };

  if (loading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="flex items-center justify-center py-20">
          <Loader2 className="w-8 h-8 animate-spin mr-3" />
          Loading monitoring data...
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div className="flex flex-col space-y-2">
          <h1 className="text-3xl font-bold tracking-tight">Production Monitoring</h1>
          <p className="text-muted-foreground">
            Real-time system health, metrics, and operational insights
          </p>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-sm text-muted-foreground">
            Last refreshed: {lastRefresh.toLocaleTimeString()}
          </span>
          <button
            type="button"
            className="px-4 py-2 bg-secondary text-secondary-foreground rounded hover:bg-secondary/80 disabled:opacity-50 flex items-center gap-2"
            onClick={handleRefresh}
            disabled={refreshing}
          >
            {refreshing ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Refreshing...
              </>
            ) : (
              <>
                <RefreshCw className="w-4 h-4" />
                Refresh
              </>
            )}
          </button>
          <button
            type="button"
            className="px-4 py-2 bg-destructive text-destructive-foreground rounded hover:bg-destructive/90 disabled:opacity-50 flex items-center gap-2"
            onClick={handleTestAlert}
            disabled={testAlertLoading}
          >
            {testAlertLoading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Sending...
              </>
            ) : (
              <>
                <Activity className="w-4 h-4" />
                Test Alert
              </>
            )}
          </button>
        </div>
      </div>

      {/* Test Alert Result */}
      {testAlertResult && (
        <div className="flex items-start gap-3 p-4 bg-blue-50 text-blue-900 dark:bg-blue-950 dark:text-blue-100 rounded mb-6">
          <CheckCircle2 className="w-5 h-5 shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="text-sm">{testAlertResult}</p>
          </div>
          <button
            type="button"
            onClick={() => setTestAlertResult(null)}
            className="text-blue-900/50 hover:text-blue-900 dark:text-blue-100/50 dark:hover:text-blue-100"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Alerts */}
      {alerts.length > 0 && (
        <div className="space-y-2 mb-6">
          {alerts.map((alert, index) => (
            <div
              key={index}
              className={`flex items-start gap-3 p-4 rounded ${
                alert.type === 'error'
                  ? 'bg-destructive/10 text-destructive'
                  : 'bg-yellow-50 text-yellow-900 dark:bg-yellow-950 dark:text-yellow-100'
              }`}
            >
              <AlertTriangle className="w-5 h-5 shrink-0 mt-0.5" />
              <div className="flex-1">
                <p className="font-medium">{alert.message}</p>
                <p className="text-xs mt-1">Threshold: {alert.threshold}</p>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Error Display */}
      {error && (
        <div className="flex items-start gap-3 p-4 bg-destructive/10 text-destructive rounded mb-6">
          <AlertTriangle className="w-5 h-5 shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="font-medium">Error Loading Data</p>
            <p className="text-sm">{error}</p>
          </div>
        </div>
      )}

      {/* Health & Readiness Status */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
        {/* Health Status */}
        <div className="border rounded-lg p-6">
          <div className="flex items-center gap-2 mb-4">
            <Activity className="w-5 h-5" />
            <h2 className="text-xl font-semibold">Health Status</h2>
            {healthStatus && <StatusBadge status={healthStatus.status} />}
          </div>
          {healthStatus && (
            <dl className="space-y-2 text-sm">
              <div className="flex justify-between">
                <dt className="text-muted-foreground">Service:</dt>
                <dd className="font-medium">{healthStatus.service}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-muted-foreground">Timestamp:</dt>
                <dd className="font-medium">{new Date(healthStatus.timestamp).toLocaleString()}</dd>
              </div>
              {healthStatus.uptime_seconds && (
                <div className="flex justify-between">
                  <dt className="text-muted-foreground">Uptime:</dt>
                  <dd className="font-medium">
                    {Math.floor(healthStatus.uptime_seconds / 3600)}h{' '}
                    {Math.floor((healthStatus.uptime_seconds % 3600) / 60)}m
                  </dd>
                </div>
              )}
              {healthStatus.version && (
                <div className="flex justify-between">
                  <dt className="text-muted-foreground">Version:</dt>
                  <dd className="font-medium">{healthStatus.version}</dd>
                </div>
              )}
              {healthStatus.git && (
                <div className="flex justify-between">
                  <dt className="text-muted-foreground">Git Commit:</dt>
                  <dd className="font-medium font-mono text-xs">
                    {healthStatus.git.commit.slice(0, 7)}
                  </dd>
                </div>
              )}
            </dl>
          )}
        </div>

        {/* Readiness Status */}
        <div className="border rounded-lg p-6">
          <div className="flex items-center gap-2 mb-4">
            <Server className="w-5 h-5" />
            <h2 className="text-xl font-semibold">Readiness Status</h2>
            {readinessStatus && <StatusBadge status={readinessStatus.overall} />}
          </div>
          {readinessStatus && (
            <dl className="space-y-2 text-sm">
              <div className="flex justify-between items-center">
                <dt className="text-muted-foreground">Database:</dt>
                <dd>
                  {readinessStatus.database.includes('healthy') ? (
                    <CheckCircle2 className="w-4 h-4 inline text-green-600" />
                  ) : (
                    <AlertTriangle className="w-4 h-4 inline text-red-600" />
                  )}
                  <span className="ml-2">{readinessStatus.database}</span>
                </dd>
              </div>
              {readinessStatus.database_latency_ms && (
                <div className="flex justify-between">
                  <dt className="text-muted-foreground">DB Latency:</dt>
                  <dd className="font-medium">{readinessStatus.database_latency_ms}ms</dd>
                </div>
              )}
              <div className="flex justify-between items-center">
                <dt className="text-muted-foreground">Redis:</dt>
                <dd>
                  {readinessStatus.redis === 'healthy' ? (
                    <CheckCircle2 className="w-4 h-4 inline text-green-600" />
                  ) : readinessStatus.redis === 'disabled' ? (
                    <span className="text-muted-foreground">Disabled</span>
                  ) : (
                    <AlertTriangle className="w-4 h-4 inline text-red-600" />
                  )}
                  <span className="ml-2">{readinessStatus.redis}</span>
                </dd>
              </div>
              <div className="flex justify-between items-center">
                <dt className="text-muted-foreground">LLM Provider:</dt>
                <dd>
                  {readinessStatus.llm.includes('healthy') ? (
                    <CheckCircle2 className="w-4 h-4 inline text-green-600" />
                  ) : (
                    <AlertTriangle className="w-4 h-4 inline text-red-600" />
                  )}
                  <span className="ml-2">{readinessStatus.llm}</span>
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-muted-foreground">Last Check:</dt>
                <dd className="font-medium">
                  {new Date(readinessStatus.timestamp).toLocaleString()}
                </dd>
              </div>
            </dl>
          )}
        </div>
      </div>

      {/* Metrics Overview */}
      {overview && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          {/* Total Properties */}
          <div className="border rounded-lg p-4">
            <div className="flex items-center gap-2 mb-2">
              <Database className="w-4 h-4 text-muted-foreground" />
              <h3 className="text-sm font-medium text-muted-foreground">Total Properties</h3>
            </div>
            <p className="text-2xl font-bold">
              {overview.database.total_properties.toLocaleString()}
            </p>
            <p className="text-xs text-muted-foreground mt-1">
              {overview.database.recent_properties_24h} in last 24h
            </p>
          </div>

          {/* Knowledge Store */}
          <div className="border rounded-lg p-4">
            <div className="flex items-center gap-2 mb-2">
              <HardDrive className="w-4 h-4 text-muted-foreground" />
              <h3 className="text-sm font-medium text-muted-foreground">Knowledge Store</h3>
            </div>
            <p className="text-2xl font-bold">
              {overview.knowledge_store.documents.toLocaleString()}
            </p>
            <p className="text-xs text-muted-foreground mt-1">
              {overview.knowledge_store.chunks.toLocaleString()} chunks
            </p>
          </div>

          {/* Cache Hit Rate */}
          <div className="border rounded-lg p-4">
            <div className="flex items-center gap-2 mb-2">
              <Zap className="w-4 h-4 text-muted-foreground" />
              <h3 className="text-sm font-medium text-muted-foreground">Cache Hit Rate</h3>
            </div>
            {overview.cache.hit_rate !== undefined ? (
              <>
                <p className="text-2xl font-bold">{overview.cache.hit_rate.toFixed(1)}%</p>
                <p className="text-xs text-muted-foreground mt-1">
                  {overview.cache.hits?.toLocaleString()} hits,{' '}
                  {overview.cache.misses?.toLocaleString()} misses
                </p>
              </>
            ) : (
              <p className="text-sm text-muted-foreground">No cache data</p>
            )}
          </div>

          {/* Environment */}
          <div className="border rounded-lg p-4">
            <div className="flex items-center gap-2 mb-2">
              <Server className="w-4 h-4 text-muted-foreground" />
              <h3 className="text-sm font-medium text-muted-foreground">Environment</h3>
            </div>
            <p className="text-2xl font-bold capitalize">{overview.environment}</p>
            <p className="text-xs text-muted-foreground mt-1">
              {overview.llm.default_provider} / {overview.llm.default_model}
            </p>
          </div>
        </div>
      )}

      {/* Data Sources Breakdown */}
      {overview &&
        overview.database.by_source &&
        Object.keys(overview.database.by_source).length > 0 && (
          <div className="border rounded-lg p-6 mb-6">
            <h2 className="text-xl font-semibold mb-4">Properties by Data Source</h2>
            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
              {Object.entries(overview.database.by_source).map(([source, count]) => (
                <div key={source} className="text-center p-3 bg-secondary rounded">
                  <p className="text-lg font-bold">{count.toLocaleString()}</p>
                  <p className="text-xs text-muted-foreground mt-1 truncate">{source}</p>
                </div>
              ))}
            </div>
          </div>
        )}

      {/* Charts Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Request Rate Chart */}
        <div className="border rounded-lg p-6">
          <h3 className="text-lg font-semibold mb-4">Request Rate (req/min)</h3>
          <div className="h-48 flex items-end justify-between gap-1">
            {requestRateData.map((point, i) => (
              <div
                key={i}
                className="flex-1 bg-primary rounded-t transition-all hover:bg-primary/80"
                style={{ height: `${Math.min(point.value, 100)}%` }}
                title={`${new Date(point.timestamp).toLocaleTimeString()}: ${point.value}`}
              />
            ))}
          </div>
          <div className="flex justify-between text-xs text-muted-foreground mt-2">
            <span>{new Date(requestRateData[0]?.timestamp).toLocaleTimeString()}</span>
            <span>
              {new Date(
                requestRateData[requestRateData.length - 1]?.timestamp
              ).toLocaleTimeString()}
            </span>
          </div>
        </div>

        {/* Error Rate Chart */}
        <div className="border rounded-lg p-6">
          <h3 className="text-lg font-semibold mb-4">Error Rate (%)</h3>
          <div className="h-48 flex items-end justify-between gap-1">
            {errorRateData.map((point, i) => (
              <div
                key={i}
                className={`flex-1 rounded-t transition-all hover:opacity-80 ${
                  point.value > 5
                    ? 'bg-destructive'
                    : point.value > 2
                      ? 'bg-yellow-500'
                      : 'bg-green-500'
                }`}
                style={{ height: `${Math.min(point.value * 10, 100)}%` }}
                title={`${new Date(point.timestamp).toLocaleTimeString()}: ${point.value}%`}
              />
            ))}
          </div>
          <div className="flex justify-between text-xs text-muted-foreground mt-2">
            <span>{new Date(errorRateData[0]?.timestamp).toLocaleTimeString()}</span>
            <span>
              {new Date(errorRateData[errorRateData.length - 1]?.timestamp).toLocaleTimeString()}
            </span>
          </div>
        </div>

        {/* Response Time Chart */}
        <div className="border rounded-lg p-6">
          <h3 className="text-lg font-semibold mb-4">Response Time (ms)</h3>
          <div className="h-48 flex items-end justify-between gap-1">
            {responseTimeData.map((point, i) => (
              <div
                key={i}
                className={`flex-1 rounded-t transition-all hover:opacity-80 ${
                  point.value > 3000
                    ? 'bg-destructive'
                    : point.value > 1000
                      ? 'bg-yellow-500'
                      : 'bg-blue-500'
                }`}
                style={{ height: `${Math.min(point.value / 10, 100)}%` }}
                title={`${new Date(point.timestamp).toLocaleTimeString()}: ${point.value}ms`}
              />
            ))}
          </div>
          <div className="flex justify-between text-xs text-muted-foreground mt-2">
            <span>{new Date(responseTimeData[0]?.timestamp).toLocaleTimeString()}</span>
            <span>
              {new Date(
                responseTimeData[responseTimeData.length - 1]?.timestamp
              ).toLocaleTimeString()}
            </span>
          </div>
        </div>
      </div>

      {/* Legend */}
      <div className="mt-6 p-4 bg-secondary rounded">
        <h4 className="text-sm font-semibold mb-2">Chart Legend</h4>
        <div className="flex flex-wrap gap-4 text-xs text-muted-foreground">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 bg-green-500 rounded" />
            <span>Healthy / Normal</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 bg-yellow-500 rounded" />
            <span>Warning / Degraded</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 bg-destructive rounded" />
            <span>Error / Critical</span>
          </div>
        </div>
      </div>
    </div>
  );
}
