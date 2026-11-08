'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';
import {
  Database,
  Globe,
  FileUp,
  Code,
  MoreVertical,
  RefreshCw,
  Trash2,
  Edit,
  Clock,
  AlertCircle,
  CheckCircle2,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { DataSourceHealthBadge } from './data-source-health-badge';
import type { DataSource } from '@/lib/types';

interface DataSourceCardProps {
  source: DataSource;
  onSync: (id: string) => void;
  onEdit: (source: DataSource) => void;
  onDelete: (source: DataSource) => void;
  isSyncing?: boolean;
}

export function DataSourceCard({
  source,
  onSync,
  onEdit,
  onDelete,
  isSyncing = false,
}: DataSourceCardProps) {
  const t = useTranslations('pages.admin.dataSources');
  const [showMenu, setShowMenu] = useState(false);

  const getSourceTypeIcon = () => {
    switch (source.source_type) {
      case 'file_upload':
        return <FileUp className="w-4 h-4" />;
      case 'url':
        return <Globe className="w-4 h-4" />;
      case 'portal_api':
        return <Database className="w-4 h-4" />;
      case 'json':
        return <Code className="w-4 h-4" />;
      default:
        return <Database className="w-4 h-4" />;
    }
  };

  const getSourceTypeLabel = () => {
    switch (source.source_type) {
      case 'file_upload':
        return t('sourceTypes.fileUpload');
      case 'url':
        return 'URL';
      case 'portal_api':
        return t('sourceTypes.portalApi');
      case 'json':
        return 'JSON';
      default:
        return source.source_type;
    }
  };

  const formatLastSync = () => {
    if (!source.last_sync_at) return t('neverSynced');
    const date = new Date(source.last_sync_at);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffMins < 1) return t('justNow');
    if (diffMins < 60) return t('minutesAgo', { count: diffMins });
    if (diffHours < 24) return t('hoursAgo', { count: diffHours });
    return t('daysAgo', { count: diffDays });
  };

  const getStatusIcon = () => {
    if (source.status === 'error' || source.consecutive_failures > 0) {
      return <AlertCircle className="w-4 h-4 text-destructive" />;
    }
    if (source.status === 'syncing' || isSyncing) {
      return <RefreshCw className="w-4 h-4 text-warning animate-spin" />;
    }
    if (source.status === 'active' && source.last_sync_status === 'success') {
      return <CheckCircle2 className="w-4 h-4 text-success" />;
    }
    return <Clock className="w-4 h-4 text-muted-foreground" />;
  };

  return (
    <div className="border rounded-lg p-4 hover:shadow-md transition-shadow relative">
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          <div className="p-2 bg-muted rounded">{getSourceTypeIcon()}</div>
          <div>
            <h3 className="font-semibold text-sm">{source.name}</h3>
            <p className="text-xs text-muted-foreground">{getSourceTypeLabel()}</p>
          </div>
        </div>

        {/* Actions Menu */}
        <div className="relative">
          <Button
            variant="ghost"
            size="sm"
            className="h-8 w-8 p-0"
            onClick={() => setShowMenu(!showMenu)}
            aria-label={t('actionsMenu')}
            aria-expanded={showMenu}
          >
            <MoreVertical className="w-4 h-4" aria-hidden="true" />
          </Button>

          {showMenu && (
            <>
              {/* The overlay only closes the menu for the mouse. */}
              <div
                className="fixed inset-0 z-10"
                onClick={() => setShowMenu(false)}
                aria-hidden="true"
              />
              <div className="absolute right-0 top-8 z-20 w-36 bg-card border rounded-md shadow-lg py-1">
                <button
                  type="button"
                  className="w-full px-3 py-2 text-left text-sm hover:bg-muted flex items-center gap-2 focus-visible:outline-none focus-visible:outline-2 focus-visible:outline-ring/50"
                  onClick={() => {
                    setShowMenu(false);
                    onEdit(source);
                  }}
                  disabled={isSyncing}
                >
                  <Edit className="w-4 h-4" />
                  {t('edit')}
                </button>
                <button
                  type="button"
                  className="w-full px-3 py-2 text-left text-sm hover:bg-muted flex items-center gap-2 focus-visible:outline-none focus-visible:outline-2 focus-visible:outline-ring/50"
                  onClick={() => {
                    setShowMenu(false);
                    onSync(source.id);
                  }}
                  disabled={isSyncing || source.status === 'syncing'}
                >
                  <RefreshCw className="w-4 h-4" />
                  {t('syncNow')}
                </button>
                <button
                  type="button"
                  className="w-full px-3 py-2 text-left text-sm hover:bg-muted text-destructive flex items-center gap-2 focus-visible:outline-none focus-visible:outline-2 focus-visible:outline-ring/50"
                  onClick={() => {
                    setShowMenu(false);
                    onDelete(source);
                  }}
                  disabled={isSyncing}
                >
                  <Trash2 className="w-4 h-4" />
                  {t('delete')}
                </button>
              </div>
            </>
          )}
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 gap-2 mb-3 text-sm">
        <div className="flex items-center gap-1.5">
          {getStatusIcon()}
          <span className="text-muted-foreground">
            {isSyncing ? t('syncing') : formatLastSync()}
          </span>
        </div>
        <div className="text-right text-muted-foreground">
          {t('records', { count: source.total_records })}
        </div>
      </div>

      {/* Health Badge */}
      <DataSourceHealthBadge
        healthScore={source.health_score}
        status={isSyncing ? 'syncing' : source.status}
      />

      {/* Error Message */}
      {source.last_error && (
        <div className="mt-3 p-2 bg-destructive/10 rounded text-xs text-destructive" role="alert">
          {source.last_error}
        </div>
      )}

      {/* Auto Sync Badge */}
      {source.auto_sync_enabled && (
        <div className="mt-2 text-xs text-muted-foreground">
          {t('autoSync', { schedule: source.sync_schedule || t('enabled') })}
        </div>
      )}
    </div>
  );
}
