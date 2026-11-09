'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { useLocale, useTranslations } from 'next-intl';
import { Users } from 'lucide-react';

import { EmptyState, ErrorState, LoadingState } from '@/components/ui/states';
import { MonoAnnotation } from '@/components/ui/mono-annotation';
import { PageHeader } from '@/components/ui/page-header';

import {
  AgentFilters,
  EMPTY_AGENT_FILTERS,
  type AgentFilterState,
  type AgentSort,
} from '@/components/agents/agent-filters';
import { AgentLedger } from '@/components/agents/agent-ledger';

import { getAgents } from '@/lib/api';
import type { AgentProfile } from '@/lib/types';

/**
 * The agent directory.
 *
 * The route is a catalogue, and the prototype draws a catalogue as rows
 * under an ink rule with a 248px filter pane beside it - the same measure
 * the search route gives its own filters. The old grid of cards is gone; the
 * card that used to draw an agent is still there for the surfaces that want
 * an object.
 *
 * The catalogue is read once and the filters are applied to it in the
 * browser: the pills answer instantly, and the sort is the one thing the
 * server owns, because only the server knows how many listings an agent has.
 */

/** How many agents the directory reads at once. The catalogue is a demo one. */
const CATALOGUE_SIZE = 100;

export default function AgentsPage() {
  const tPage = useTranslations('pages.agents');
  const tAgents = useTranslations('agents');
  const tCommon = useTranslations('common');
  const locale = useLocale();

  const [catalogue, setCatalogue] = useState<AgentProfile[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<AgentFilterState>(EMPTY_AGENT_FILTERS);

  const loadCatalogue = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await getAgents({
        sort_by: filters.sort as AgentSort,
        sort_order: 'desc',
        page: 1,
        page_size: CATALOGUE_SIZE,
      });

      setCatalogue(response.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : tAgents('errors.load'));
    } finally {
      setLoading(false);
    }
  }, [filters.sort, tAgents]);

  useEffect(() => {
    void loadCatalogue();
  }, [loadCatalogue]);

  /** The cities and the specialties the catalogue itself names. */
  const cities = useMemo(() => {
    const all = catalogue.flatMap((agent) => agent.service_areas ?? []);
    return Array.from(new Set(all)).sort((a, b) => a.localeCompare(b));
  }, [catalogue]);

  const specialties = useMemo(() => {
    const all = catalogue.flatMap((agent) => agent.specialties ?? []);
    return Array.from(new Set(all)).sort((a, b) => a.localeCompare(b));
  }, [catalogue]);

  const rows = useMemo(() => {
    return catalogue.filter((agent) => {
      if (filters.city && !(agent.service_areas ?? []).includes(filters.city)) return false;
      if (filters.specialty && !(agent.specialties ?? []).includes(filters.specialty)) return false;
      if (filters.minRating !== null && agent.average_rating < filters.minRating) return false;
      return true;
    });
  }, [catalogue, filters]);

  const clearFilters = () => {
    setFilters((current) => ({ ...current, city: null, specialty: null, minRating: null }));
  };

  return (
    <div className="flex min-h-full flex-col bg-background">
      <div className="flex flex-col gap-3 border-b border-border px-6 py-5 sm:flex-row sm:items-end sm:justify-between">
        <PageHeader title={tPage('title')} description={tPage('description')} />
        <div className="flex items-center gap-2">
          <MonoAnnotation>
            {tAgents('directory.count', { count: rows.length })}
          </MonoAnnotation>
          {process.env.NEXT_PUBLIC_DEMO_MODE === 'true' ? (
            <MonoAnnotation>{tAgents('directory.demoNote')}</MonoAnnotation>
          ) : null}
        </div>
      </div>

      <div className="grid flex-1 grid-cols-1 lg:grid-cols-[248px_minmax(0,1fr)]">
        <aside className="border-b border-border px-6 py-4 lg:border-b-0 lg:border-r">
          <AgentFilters
            cities={cities}
            specialties={specialties}
            value={filters}
            onChange={setFilters}
            onClear={clearFilters}
          />
        </aside>

        <main className="min-w-0">
          {error ? (
            <ErrorState
              title={tAgents('errors.load')}
              description={error}
              onRetry={() => void loadCatalogue()}
              retryLabel={tCommon('retry')}
            />
          ) : null}

          {loading ? <LoadingState rows={8} /> : null}

          {!loading && !error && rows.length === 0 ? (
            <EmptyState
              icon={Users}
              title={tAgents('noAgents')}
              description={tAgents('noAgentsDescription')}
            />
          ) : null}

          {!loading && !error && rows.length > 0 ? (
            <AgentLedger agents={rows} locale={locale} />
          ) : null}
        </main>
      </div>
    </div>
  );
}
