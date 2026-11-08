'use client';

import { Plus, Loader2 } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { Button } from '@/components/ui/button';
import { DataSourceCard } from './data-source-card';
import type { DataSource } from '@/lib/types';

interface DataSourceListProps {
  sources: DataSource[];
  onAddNew: () => void;
  onSync: (id: string) => void;
  onEdit: (source: DataSource) => void;
  onDelete: (source: DataSource) => void;
  syncingIds: Set<string>;
  isLoading?: boolean;
}

export function DataSourceList({
  sources,
  onAddNew,
  onSync,
  onEdit,
  onDelete,
  syncingIds,
  isLoading = false,
}: DataSourceListProps) {
  const t = useTranslations('pages.admin.dataSources');

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-6 h-6 animate-spin mr-2" aria-hidden="true" />
        <span className="text-muted-foreground">{t('loadingSources')}</span>
      </div>
    );
  }

  return (
    <div>
      {/* Header with Add Button */}
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold">
          {t('configuredSources', { count: sources.length })}
        </h2>
        <Button onClick={onAddNew} size="sm">
          <Plus className="w-4 h-4 mr-2" aria-hidden="true" />
          {t('addSource')}
        </Button>
      </div>

      {/* Empty State */}
      {sources.length === 0 ? (
        <div className="text-center py-12 border rounded-lg bg-muted/30">
          <p className="text-muted-foreground mb-4">{t('noSources')}</p>
          <Button onClick={onAddNew}>
            <Plus className="w-4 h-4 mr-2" aria-hidden="true" />
            {t('addFirstSource')}
          </Button>
        </div>
      ) : (
        /* Sources Grid */
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {sources.map((source) => (
            <DataSourceCard
              key={source.id}
              source={source}
              onSync={onSync}
              onEdit={onEdit}
              onDelete={onDelete}
              isSyncing={syncingIds.has(source.id)}
            />
          ))}
        </div>
      )}
    </div>
  );
}
