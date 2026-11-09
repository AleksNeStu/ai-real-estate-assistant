'use client';

import { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { AlertCircle, Loader2, RefreshCw, Search, Trash2 } from 'lucide-react';
import { useLocale, useTranslations } from 'next-intl';

import { Button } from '@/components/ui/button';
import { MonoAnnotation } from '@/components/ui/mono-annotation';
import { PageHeader } from '@/components/ui/page-header';
import { EmptyState } from '@/components/ui/states';
import { getSavedSearches, deleteSavedSearch, toggleSavedSearchAlert, ApiError } from '@/lib/api';
import { resolveLocale } from '@/lib/format';
import type { SavedSearch } from '@/lib/types';

/**
 * The saved searches as a ledger.
 *
 * The route is the prototype's arrangement: a heading that says how many
 * alerts are running, and a ledger under it - one row per search, the
 * filters it was parsed into under its name, the rule it watches with, the
 * switch that turns it on and off, and the way out.
 *
 * Every number on the row is a number the API carried: the filters are the
 * ones the search was saved with, the use count is the count of the runs, and
 * the switch is the state of the alert. The prototype also draws a column of
 * "3 new" matches and a price-drop threshold; the API carries neither, so
 * neither is written here.
 */

export default function SavedSearchesPage() {
  const t = useTranslations('pages.savedSearches');
  const locale = useLocale();
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

  /**
   * The filters of the search, written the way the search route writes its
   * chips: the name of the filter, the sign, the value.
   *
   * A saved search carries no currency, so the price is written as a bare
   * number - a dollar sign in front of it would be a guess.
   */
  const formatFilters = (filters: Record<string, unknown>): string => {
    const parts: string[] = [];

    if (filters.city) parts.push(`city = ${filters.city}`);

    const amount = (value: unknown): string | null => {
      const parsed = Number(value);
      if (!Number.isFinite(parsed)) return null;
      return parsed.toLocaleString(resolveLocale(locale));
    };

    const min = amount(filters.min_price);
    const max = amount(filters.max_price);
    if (min) parts.push(`price ≥ ${min}`);
    if (max) parts.push(`price ≤ ${max}`);

    if (Array.isArray(filters.property_types) && filters.property_types.length > 0) {
      parts.push(`type = ${filters.property_types.join(', ')}`);
    }

    const minRooms = filters.min_rooms;
    const maxRooms = filters.max_rooms;
    if (minRooms !== undefined || maxRooms !== undefined) {
      const rooms = [minRooms, maxRooms].filter((value) => value !== undefined).join('-');
      parts.push(`rooms = ${rooms}`);
    }

    return parts.join(' · ');
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
      return new Date(dateStr).toLocaleDateString(locale);
    } catch {
      return dateStr;
    }
  };

  const activeCount = useMemo(() => searches.filter((search) => search.is_active).length, [searches]);

  const alertRule = (search: SavedSearch): string => {
    if (search.notify_on_new && search.notify_on_price_drop) return t('alertRule.both');
    if (search.notify_on_new) return t('alerts.newMatches');
    if (search.notify_on_price_drop) return t('alerts.priceDrops');
    return t('alertRule.none');
  };

  if (loading) {
    return (
      <div className="flex min-h-[calc(100vh-56px)] items-center justify-center px-6 py-8">
        <div
          className="flex items-center justify-center"
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
    <div className="mx-auto flex min-h-[calc(100vh-56px)] w-full max-w-[1100px] flex-col px-6 pb-16 pt-7">
      <PageHeader
        title={t('title')}
        description={t('summary', { active: activeCount, total: searches.length })}
        actions={
          <>
            <Button
              type="button"
              variant="outline"
              onClick={fetchSearches}
              disabled={loading}
              aria-label={t('refreshAria')}
              className="h-9 w-9 px-0"
            >
              <RefreshCw className="h-4 w-4" aria-hidden="true" />
            </Button>
            <Link
              href={`/${locale}/search`}
              className="inline-flex h-9 items-center justify-center rounded-md bg-action px-3.5 text-[13px] font-medium text-action-foreground transition-colors hover:bg-action/90 focus-visible:outline-none focus-visible:outline-2 focus-visible:outline-ring/50"
            >
              {t('newSearch')}
            </Link>
          </>
        }
      />

      {error ? (
        <p
          className="mt-4 border-t border-destructive py-3 text-[14px] text-destructive"
          role="alert"
        >
          <AlertCircle className="mr-2 inline h-4 w-4 align-text-bottom" aria-hidden="true" />
          {error}
        </p>
      ) : null}

      {searches.length === 0 ? (
        <div className="mt-6">
          <EmptyState
            icon={Search}
            title={t('emptyTitle')}
            description={t('emptyDescription')}
            action={
              <Link
                href={`/${locale}/search`}
                className="inline-flex h-9 items-center justify-center rounded-md bg-action px-3.5 text-[13px] font-medium text-action-foreground transition-colors hover:bg-action/90"
              >
                {t('newSearch')}
              </Link>
            }
          />
        </div>
      ) : (
        <div className="mt-6 border-t border-foreground">
          {searches.map((search) => {
            const busy = actionLoading === search.id;
            const filters = formatFilters(search.filters);

            return (
              <article
                key={search.id}
                data-testid="saved-search-row"
                className={[
                  'grid grid-cols-1 items-baseline gap-x-4 gap-y-2 border-b border-border py-3.5 md:grid-cols-[minmax(0,1.6fr)_1.4fr_120px_180px]',
                  search.is_active ? 'opacity-100' : 'opacity-60',
                ].join(' ')}
              >
                <div className="min-w-0">
                  <h2 className="m-0 truncate text-[14px] font-medium leading-5 text-foreground">
                    {search.name}
                  </h2>
                  {filters ? (
                    <MonoAnnotation className="mt-0.5 block truncate">{filters}</MonoAnnotation>
                  ) : null}
                  <MonoAnnotation className="mt-0.5 block">
                    {t('created', { date: formatDate(search.created_at) })} ·{' '}
                    {t('used', { count: search.use_count })}
                  </MonoAnnotation>
                  {search.description ? (
                    <p className="mt-1 text-[13px] leading-5 text-muted-foreground">
                      {search.description}
                    </p>
                  ) : null}
                </div>

                <div className="min-w-0">
                  <span className="text-[13px] leading-5 text-foreground">{alertRule(search)}</span>
                  <MonoAnnotation className="mt-0.5 block">
                    {formatFrequency(search.alert_frequency)}
                  </MonoAnnotation>
                </div>

                <div>
                  <button
                    type="button"
                    role="switch"
                    aria-checked={search.is_active}
                    onClick={() => handleToggleAlert(search.id, search.is_active)}
                    disabled={busy}
                    className="inline-flex items-center gap-2 border-0 bg-transparent p-0 text-[13px] text-foreground disabled:opacity-50 focus-visible:outline-none focus-visible:outline-2 focus-visible:outline-ring/50"
                  >
                    <span
                      className={[
                        'relative inline-block h-5 w-[34px] rounded-full transition-colors',
                        search.is_active ? 'bg-foreground' : 'bg-border',
                      ].join(' ')}
                    >
                      <span
                        className="absolute top-[2px] size-4 rounded-full border border-border bg-background transition-[left]"
                        style={{ left: search.is_active ? '16px' : '2px' }}
                      />
                    </span>
                    {search.is_active ? t('state.on') : t('state.off')}
                  </button>
                </div>

                <div className="flex items-center justify-start gap-3 md:justify-end">
                  <button
                    type="button"
                    onClick={() => handleDelete(search.id, search.name)}
                    disabled={busy}
                    title={t('deleteSearch')}
                    aria-label={t('deleteSearch')}
                    className="inline-flex items-center border-0 bg-transparent p-0 text-[13px] text-muted-foreground transition-colors hover:text-destructive disabled:opacity-50 focus-visible:outline-none focus-visible:outline-2 focus-visible:outline-ring/50"
                  >
                    <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
                    <span className="ml-1.5">{t('deleteSearch')}</span>
                  </button>
                </div>
              </article>
            );
          })}
        </div>
      )}
    </div>
  );
}
