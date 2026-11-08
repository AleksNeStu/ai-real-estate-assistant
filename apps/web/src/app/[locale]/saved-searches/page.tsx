'use client';

import React, { useEffect, useState } from 'react';
import {
  Bookmark,
  Bell,
  BellOff,
  Trash2,
  Search,
  Loader2,
  RefreshCw,
  AlertCircle,
} from 'lucide-react';
import { useTranslations } from 'next-intl';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { PageHeader } from '@/components/ui/page-header';
import { getSavedSearches, deleteSavedSearch, toggleSavedSearchAlert, ApiError } from '@/lib/api';
import type { SavedSearch } from '@/lib/types';
import { EmptyState } from '@/components/ui/states';

export default function SavedSearchesPage() {
  const t = useTranslations('pages.savedSearches');
  const tCommon = useTranslations('common');
  const [searches, setSearches] = useState<SavedSearch[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  useEffect(() => {
    fetchSearches();
  }, []);

  const fetchSearches = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await getSavedSearches(true);
      setSearches(data.items);
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.category === 'auth') {
          setError(t('loginRequired'));
        } else {
          setError(err.message);
        }
      } else {
        setError(err instanceof Error ? err.message : t('errors.load'));
      }
    } finally {
      setLoading(false);
    }
  };

  const handleToggleAlert = async (id: string, currentState: boolean) => {
    try {
      setActionLoading(id);
      const updated = await toggleSavedSearchAlert(id, !currentState);
      setSearches(searches.map((s) => (s.id === id ? updated : s)));
    } catch (err) {
      setError(err instanceof Error ? err.message : t('errors.toggleAlert'));
    } finally {
      setActionLoading(null);
    }
  };

  const handleDelete = async (id: string, name: string) => {
    if (!confirm(t('deleteConfirm', { name }))) {
      return;
    }

    try {
      setActionLoading(id);
      await deleteSavedSearch(id);
      setSearches(searches.filter((s) => s.id !== id));
    } catch (err) {
      setError(err instanceof Error ? err.message : t('errors.delete'));
    } finally {
      setActionLoading(null);
    }
  };

  const formatFilters = (filters: Record<string, unknown>): string => {
    const parts: string[] = [];
    if (filters.city) parts.push(filters.city as string);
    if (filters.min_price || filters.max_price) {
      const min = filters.min_price ? `$${Number(filters.min_price).toLocaleString()}` : '';
      const max = filters.max_price ? `$${Number(filters.max_price).toLocaleString()}` : '';
      if (min && max) {
        parts.push(`${min}-${max}`);
      } else {
        parts.push(`${min}${max}`);
      }
    }
    if (filters.property_types && Array.isArray(filters.property_types)) {
      parts.push(filters.property_types.join(', '));
    }
    if (filters.min_rooms || filters.max_rooms) {
      const min = filters.min_rooms || '';
      const max = filters.max_rooms || '';
      parts.push(t('roomsLabel', { count: `${min}-${max}` }));
    }
    return parts.join(' | ') || t('filters.allProperties');
  };

  const formatFrequency = (frequency: string): string => {
    switch (frequency) {
      case 'instant':
        return t('frequency.instant');
      case 'daily':
        return t('frequency.daily');
      case 'weekly':
        return t('frequency.weekly');
      case 'none':
        return t('frequency.none');
      default:
        return frequency;
    }
  };

  const formatDate = (dateStr: string): string => {
    try {
      return new Date(dateStr).toLocaleDateString();
    } catch {
      return dateStr;
    }
  };

  if (loading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div
          className="flex items-center justify-center min-h-[400px]"
          role="status"
          aria-live="polite"
        >
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" aria-hidden="true" />
          <span className="sr-only">{t('loading')}</span>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <PageHeader
        className="mb-8"
        title={
          <span className="flex items-center gap-4">
            <Bookmark className="h-8 w-8 text-primary" aria-hidden="true" />
            {t('title')}
          </span>
        }
        description={t('description')}
        actions={
          <Button
            variant="outline"
            onClick={fetchSearches}
            disabled={loading}
            aria-label={t('refreshAria')}
          >
            <RefreshCw className="h-4 w-4 mr-2" aria-hidden="true" />
            {tCommon('refresh')}
          </Button>
        }
      />

      {error && (
        <div
          className="bg-destructive/10 text-destructive px-4 py-3 rounded-md mb-6 flex items-center gap-2"
          role="alert"
        >
          <AlertCircle className="h-5 w-5" aria-hidden="true" />
          {error}
        </div>
      )}

      {searches.length === 0 ? (
        <EmptyState icon={Search} title={t('emptyTitle')} description={t('emptyDescription')} />
      ) : (
        <div className="grid gap-4">
          {searches.map((search) => (
            <Card key={search.id}>
              <CardHeader className="flex flex-row items-start justify-between space-y-0 pb-2">
                <div className="flex-1">
                  <CardTitle className="text-lg flex items-center gap-2">
                    {search.name}
                    {!search.is_active && (
                      <span className="text-xs font-normal text-muted-foreground bg-muted px-2 py-0.5 rounded">
                        {t('paused')}
                      </span>
                    )}
                  </CardTitle>
                  <p className="text-sm text-muted-foreground mt-1">
                    {formatFilters(search.filters)}
                  </p>
                </div>
                <div className="flex items-center gap-2 ml-4">
                  <Button
                    variant={search.is_active ? 'default' : 'outline'}
                    size="sm"
                    onClick={() => handleToggleAlert(search.id, search.is_active)}
                    disabled={actionLoading === search.id}
                    title={search.is_active ? t('pauseAlerts') : t('resumeAlerts')}
                    aria-label={search.is_active ? t('pauseAlerts') : t('resumeAlerts')}
                    aria-pressed={search.is_active}
                  >
                    {actionLoading === search.id ? (
                      <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                    ) : search.is_active ? (
                      <Bell className="h-4 w-4" aria-hidden="true" />
                    ) : (
                      <BellOff className="h-4 w-4" aria-hidden="true" />
                    )}
                    <span className="ml-2 hidden sm:inline">
                      {formatFrequency(search.alert_frequency)}
                    </span>
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleDelete(search.id, search.name)}
                    disabled={actionLoading === search.id}
                    title={t('deleteSearch')}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-muted-foreground">
                  <span>{t('created', { date: formatDate(search.created_at) })}</span>
                  <span>{t('used', { count: search.use_count })}</span>
                  {search.notify_on_new && (
                    <span className="text-success">{t('alerts.newMatches')}</span>
                  )}
                  {search.notify_on_price_drop && (
                    <span className="text-info">{t('alerts.priceDrops')}</span>
                  )}
                </div>
                {search.description && (
                  <p className="text-sm text-muted-foreground mt-2">{search.description}</p>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
