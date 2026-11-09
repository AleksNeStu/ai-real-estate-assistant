'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { useTranslations } from 'next-intl';

import { AccountGate } from '@/components/shell/gate';
import { HighValueRail } from '@/components/leads/high-value-rail';
import { LeadBoard } from '@/components/leads/lead-board';
import { LeadFunnel, LeadFunnelNote, buildFunnelStages } from '@/components/leads/lead-funnel';
import { HIGH_VALUE_THRESHOLD } from '@/components/leads/lead-format';
import { MonoAnnotation } from '@/components/ui/mono-annotation';
import { PageHeader } from '@/components/ui/page-header';
import { ErrorState } from '@/components/ui/states';
import {
  exportLeads,
  getHighValueLeads,
  getLeads,
  getScoringStatistics,
  recalculateScores,
  updateLeadStatus,
} from '@/lib/api';
import type { LeadStatus, LeadWithScore, ScoringStatistics } from '@/lib/types';

/**
 * The leads board.
 *
 * The board answers one question - where does the pipeline stand - so it
 * opens with the funnel, carries the leads in five columns, and keeps the
 * high-value ones in the rail beside them. The CSV export is the way out:
 * the board is for reading, the file is for working.
 */

/** How many leads the board asks for in one page. */
const BOARD_PAGE_SIZE = 200;

export default function LeadsPage() {
  const t = useTranslations('pages.leads');
  const tBoard = useTranslations('pages.leads.board');
  const tCommon = useTranslations('common');

  const [leads, setLeads] = useState<LeadWithScore[]>([]);
  const [total, setTotal] = useState(0);
  const [highValueLeads, setHighValueLeads] = useState<LeadWithScore[]>([]);
  const [statistics, setStatistics] = useState<ScoringStatistics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [recalculating, setRecalculating] = useState(false);
  const [exported, setExported] = useState<string | null>(null);
  const [now, setNow] = useState<number | null>(null);

  const loadLeads = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const [leadsResponse, highValueResponse] = await Promise.all([
        getLeads({ page: 1, page_size: BOARD_PAGE_SIZE, sort_by: 'score', sort_order: 'desc' }),
        getHighValueLeads(HIGH_VALUE_THRESHOLD, 10),
      ]);

      setLeads(leadsResponse.items);
      setTotal(leadsResponse.total);
      setHighValueLeads(highValueResponse);

      // The scoring statistics are an administrator's view of the model.
      // An agent does not get them, and the board does not need them - so
      // they are fetched on their own and their absence is not an error.
      getScoringStatistics()
        .then(setStatistics)
        .catch(() => setStatistics(null));
    } catch (err) {
      setError(err instanceof Error ? err.message : t('errors.load'));
    } finally {
      setLoading(false);
    }
  }, [t]);

  useEffect(() => {
    loadLeads();
  }, [loadLeads]);

  // The reference point for "how long ago" lives in state, so the rendering
  // stays pure and the clock only moves once a minute.
  useEffect(() => {
    const update = () => setNow(Date.now());
    update();
    const interval = setInterval(update, 60000);
    return () => clearInterval(interval);
  }, []);

  const handleAdvance = useCallback(async (lead: LeadWithScore, status: LeadStatus) => {
    try {
      await updateLeadStatus(lead.id, status);
      setLeads((previous) =>
        previous.map((item) => (item.id === lead.id ? { ...item, status } : item))
      );
    } catch (err) {
      console.error(t('errors.updateStatus'), err);
    }
  }, [t]);

  const handleRecalculateScores = useCallback(async () => {
    try {
      setRecalculating(true);
      await recalculateScores();
      await loadLeads();
    } catch (err) {
      console.error(t('errors.recalculate'), err);
    } finally {
      setRecalculating(false);
    }
  }, [loadLeads, t]);

  const handleExport = useCallback(async () => {
    try {
      const blob = await exportLeads();
      const url = window.URL.createObjectURL(blob);
      const file = `leads-${new Date().toISOString().split('T')[0]}.csv`;
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = file;
      anchor.click();
      window.URL.revokeObjectURL(url);
      setExported(tBoard('exported', { file, count: total || leads.length }));
    } catch (err) {
      console.error(t('errors.export'), err);
    }
  }, [leads.length, t, tBoard, total]);

  const stages = useMemo(() => buildFunnelStages(leads), [leads]);

  if (error) {
    return (
      <div className="container mx-auto px-4 py-8">
        <ErrorState title={error} onRetry={loadLeads} retryLabel={tCommon('tryAgain')} />
      </div>
    );
  }

  return (
    <AccountGate route="leads">
      <div className="flex flex-col gap-5 px-6 py-6">
        <PageHeader
          title={tBoard('title')}
          description={tBoard('description')}
          actions={
            <div className="flex items-center gap-3">
              {exported ? <MonoAnnotation>{exported}</MonoAnnotation> : null}
              <button
                type="button"
                onClick={handleRecalculateScores}
                disabled={recalculating}
                className="inline-flex h-[34px] items-center rounded-md border border-border bg-transparent px-3 text-[13px] font-medium text-foreground transition-colors hover:bg-muted disabled:opacity-50"
              >
                {recalculating ? tBoard('recalculating') : tBoard('recalculate')}
              </button>
              <button
                type="button"
                onClick={handleExport}
                className="inline-flex h-[34px] items-center rounded-md border border-border bg-transparent px-3 text-[13px] font-medium text-foreground transition-colors hover:bg-muted"
              >
                {tBoard('export')}
              </button>
            </div>
          }
        />

        {statistics ? (
          <div className="flex flex-wrap items-center gap-x-6 gap-y-2">
            <MonoAnnotation>
              {tBoard('totalLeads', { count: statistics.total_leads })}
            </MonoAnnotation>
            <MonoAnnotation>
              {tBoard('newLast24h', { count: statistics.new_leads_24h })}
            </MonoAnnotation>
            <MonoAnnotation>
              {tBoard('averageScore', { value: statistics.avg_score.toFixed(1) })}
            </MonoAnnotation>
            <MonoAnnotation>
              {tBoard('conversionRate', { value: statistics.conversion_rate.toFixed(1) })}
            </MonoAnnotation>
          </div>
        ) : null}

        <LeadFunnel stages={stages} />

        <div className="flex items-center justify-between gap-4">
          <LeadFunnelNote shown={leads.length} total={total} />
        </div>

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,1fr)_300px]">
          <LeadBoard
            leads={loading ? [] : leads}
            onAdvance={handleAdvance}
            now={now}
          />
          <HighValueRail leads={highValueLeads} threshold={HIGH_VALUE_THRESHOLD} />
        </div>
      </div>
    </AccountGate>
  );
}
