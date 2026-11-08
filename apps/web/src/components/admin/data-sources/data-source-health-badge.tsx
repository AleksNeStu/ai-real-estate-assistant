'use client';

import { Progress } from '@/components/ui/progress';
import { useTranslations } from 'next-intl';

interface DataSourceHealthBadgeProps {
  healthScore: number;
  status: string;
  className?: string;
}

export function DataSourceHealthBadge({
  healthScore,
  status,
  className = '',
}: DataSourceHealthBadgeProps) {
  const t = useTranslations('pages.admin.dataSources');

  const getColorClass = () => {
    if (status === 'error') return 'bg-destructive';
    if (status === 'syncing') return 'bg-warning';
    if (status === 'pending') return 'bg-muted-foreground';
    if (healthScore >= 80) return 'bg-success';
    if (healthScore >= 50) return 'bg-warning';
    return 'bg-destructive';
  };

  const getLabel = () => {
    if (status === 'error') return t('health.error');
    if (status === 'syncing') return t('health.syncing');
    if (status === 'pending') return t('health.pending');
    if (healthScore >= 80) return t('health.healthy');
    if (healthScore >= 50) return t('health.degraded');
    return t('health.unhealthy');
  };

  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <div className={`w-2 h-2 rounded-full ${getColorClass()}`} />
      <span className="text-xs text-muted-foreground">{getLabel()}</span>
      {status !== 'pending' && status !== 'syncing' && (
        <Progress value={healthScore} className="w-16 h-1.5" />
      )}
      {status !== 'pending' && status !== 'syncing' && (
        <span className="text-xs font-mono">{healthScore.toFixed(0)}%</span>
      )}
    </div>
  );
}
