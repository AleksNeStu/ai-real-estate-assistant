'use client';

import { useEffect, useState } from 'react';
import { useTranslations } from 'next-intl';

import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

interface DependencyHealth {
  status: string;
  message: string;
  latency_ms?: number;
}

interface HealthStatus {
  status: string;
  version: string;
  uptime_seconds: number;
  dependencies?: Record<string, DependencyHealth>;
}

export function MetricsWidget() {
  const t = useTranslations('admin.systemHealth');
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchHealth = async () => {
      try {
        const res = await fetch('/api/v1/health?include_dependencies=true');
        if (!res.ok) throw new Error(t('fetchError'));
        const data = await res.json();
        setHealth(data);
        setError(null);
      } catch (err) {
        console.error('Failed to fetch health:', err);
        setError(err instanceof Error ? err.message : t('unknownError'));
      } finally {
        setLoading(false);
      }
    };

    fetchHealth();
    const interval = setInterval(fetchHealth, 30000); // Refresh every 30s
    return () => clearInterval(interval);
  }, [t]);

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>{t('title')}</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-muted-foreground">{t('loading')}</div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>{t('title')}</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-destructive">
            {t('errorPrefix')} {error}
          </div>
        </CardContent>
      </Card>
    );
  }

  const statusColorMap: Record<string, string> = {
    healthy: 'bg-success',
    degraded: 'bg-warning',
    unhealthy: 'bg-destructive',
  };

  const statusColor = statusColorMap[health?.status || 'unhealthy'] || 'bg-muted-foreground';

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          {t('title')}
          <Badge className={statusColor}>{health?.status || 'unknown'}</Badge>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <p className="text-sm text-muted-foreground">{t('version')}</p>
            <p className="font-mono">{health?.version || 'N/A'}</p>
          </div>
          <div>
            <p className="text-sm text-muted-foreground">{t('uptime')}</p>
            <p className="font-mono">{formatUptime(health?.uptime_seconds || 0)}</p>
          </div>
        </div>
        {health?.dependencies && (
          <div className="mt-4 space-y-2">
            <p className="text-sm font-medium text-muted-foreground">Dependencies</p>
            {Object.entries(health.dependencies).map(([name, dep]) => (
              <div key={name} className="flex justify-between items-center">
                <span className="capitalize">{name.replace(/_/g, ' ')}</span>
                <Badge
                  variant={dep.status === 'healthy' ? 'default' : 'destructive'}
                  className="text-xs"
                >
                  {dep.status}
                  {dep.latency_ms !== undefined && ` (${dep.latency_ms.toFixed(0)}ms)`}
                </Badge>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function formatUptime(seconds: number): string {
  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  const mins = Math.floor((seconds % 3600) / 60);
  if (days > 0) return `${days}d ${hours}h`;
  if (hours > 0) return `${hours}h ${mins}m`;
  return `${mins}m`;
}
