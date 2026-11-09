'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { useLocale, useTranslations } from 'next-intl';

import { AccountGate } from '@/components/shell/gate';
import { MonoAnnotation } from '@/components/ui/mono-annotation';
import { PageHeader } from '@/components/ui/page-header';
import { ErrorState } from '@/components/ui/states';
import { UsageActivityChart } from '@/components/usage/usage-activity-chart';
import { UsageEventLedger, type UsageLogRow } from '@/components/usage/usage-event-ledger';
import { UsageKindTiles } from '@/components/usage/usage-kind-tiles';
import {
  USAGE_EVENT_KINDS,
  formatDay,
  formatPeriod,
  type UsageEventKind,
} from '@/components/usage/usage-format';
import {
  exportUserActivityCSV,
  getUserActivitySummary,
  getUserActivityTrends,
} from '@/lib/api';
import type { UserActivitySummary, UserActivityTrendPoint } from '@/lib/types';

/**
 * The usage dashboard.
 *
 * What the visitor did here: the kinds of event and how many of each, the
 * day on which they happened, and the file that holds every one of them.
 *
 * The API counts the five kinds over the period and the searches per day.
 * It does not carry a per-event log as data - the CSV export does - so the
 * ledger below speaks at the detail the API does carry, and says where the
 * rest of it lives.
 */

/** How many days the dashboard shows. */
const DAYS = 30;

export default function UsagePage() {
  const t = useTranslations('pages.usage');
  const tBoard = useTranslations('pages.usage.board');
  const tCommon = useTranslations('common');
  const locale = useLocale();

  const [summary, setSummary] = useState<UserActivitySummary | null>(null);
  const [trends, setTrends] = useState<UserActivityTrendPoint[]>([]);
  const [selected, setSelected] = useState<UsageEventKind | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [exported, setExported] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const [summaryData, trendsData] = await Promise.all([
        getUserActivitySummary(),
        getUserActivityTrends({ interval: 'day', periods: DAYS }),
      ]);

      setSummary(summaryData);
      setTrends(trendsData.trends);
    } catch (err) {
      setError(err instanceof Error ? err.message : t('loadFailed'));
    } finally {
      setLoading(false);
    }
  }, [t]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleExport = useCallback(async () => {
    try {
      const blob = await exportUserActivityCSV();
      const url = window.URL.createObjectURL(blob);
      const file = `usage-${new Date().toISOString().split('T')[0]}.csv`;
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = file;
      anchor.click();
      window.URL.revokeObjectURL(url);
      const events =
        (summary?.total_searches ?? 0) +
        (summary?.total_property_views ?? 0) +
        (summary?.total_property_clicks ?? 0) +
        (summary?.total_tool_uses ?? 0) +
        (summary?.total_exports ?? 0);
      setExported(tBoard('exported', { file, count: events }));
    } catch (err) {
      console.error('Failed to export:', err);
    }
  }, [summary, tBoard]);

  const totals = useMemo(
    () => ({
      search: summary?.total_searches ?? 0,
      view: summary?.total_property_views ?? 0,
      click: summary?.total_property_clicks ?? 0,
      tool_call: summary?.total_tool_uses ?? 0,
      download: summary?.total_exports ?? 0,
    }),
    [summary]
  );

  const tiles = useMemo(
    () =>
      USAGE_EVENT_KINDS.map((kind) => ({
        kind,
        value: totals[kind],
        label: tBoard(`kinds.${kind}`),
      })),
    [tBoard, totals]
  );

  // The daily series the API carries: the searches of every day of the
  // period. The other kinds are counted over the period, not per day.
  const dailyPoints = useMemo(
    () =>
      trends.map((trend) => ({
        date: trend.date,
        value: trend.searches ?? 0,
      })),
    [trends]
  );

  const periodLabel = summary
    ? formatPeriod(summary.period_start, summary.period_end, locale)
    : null;

  const rows = useMemo<UsageLogRow[]>(() => {
    if (!summary) return [];

    // The tools the API breaks the tool calls down by.
    if (selected === 'tool_call') {
      return summary.top_tools.map((tool) => ({
        when: periodLabel ?? tBoard('period'),
        event: tool.tool_name,
        detail: tBoard('calls', { count: tool.count }),
      }));
    }

    // A kind the API does not break down: one row, the total it counted.
    if (selected && selected !== 'search') {
      return [
        {
          when: periodLabel ?? tBoard('period'),
          event: tBoard(`kinds.${selected}`),
          detail: tBoard('count', { count: totals[selected] }),
        },
      ];
    }

    // The searches, day by day.
    return dailyPoints
      .filter((point) => point.value > 0)
      .map((point) => ({
        when: formatDay(point.date, locale),
        event: tBoard('kinds.search'),
        detail: tBoard('count', { count: point.value }),
      }));
  }, [dailyPoints, locale, periodLabel, selected, summary, tBoard, totals]);

  if (error) {
    return (
      <div className="container mx-auto px-4 py-8">
        <ErrorState
          title={tCommon('error')}
          description={error}
          onRetry={loadData}
          retryLabel={tCommon('retry')}
        />
      </div>
    );
  }

  return (
    <AccountGate route="usage">
      <div className="mx-auto flex max-w-[1100px] flex-col gap-5 px-6 py-7">
        <PageHeader
          title={tBoard('title')}
          description={tBoard('description')}
          actions={
            <div className="flex items-center gap-3">
              {exported ? <MonoAnnotation>{exported}</MonoAnnotation> : null}
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

        {summary ? (
          <div className="flex flex-wrap items-center gap-x-6 gap-y-1">
            <MonoAnnotation>{periodLabel}</MonoAnnotation>
            <MonoAnnotation>{t('sessions', { count: summary.unique_sessions })}</MonoAnnotation>
            <MonoAnnotation>
              {tBoard('favorites', { count: summary.total_favorites })}
            </MonoAnnotation>
          </div>
        ) : null}

        <UsageKindTiles tiles={tiles} selected={selected} onSelect={setSelected} />

        <UsageActivityChart
          points={dailyPoints}
          title={tBoard('searchesPerDay')}
          caption={tBoard('days', { count: DAYS })}
          axisLabels={
            dailyPoints.length > 0
              ? {
                  first: formatDay(dailyPoints[0].date, locale),
                  last: formatDay(dailyPoints[dailyPoints.length - 1].date, locale),
                }
              : undefined
          }
        />

        <div className="flex flex-col gap-2">
          <span className="text-[15px] font-semibold text-foreground">{tBoard('logTitle')}</span>
          <UsageEventLedger
            rows={rows}
            labels={{
              when: tBoard('logWhen'),
              event: tBoard('logEvent'),
              detail: tBoard('logDetail'),
            }}
            note={tBoard('note')}
            emptyTitle={tBoard('empty')}
          />
        </div>

        {loading ? <MonoAnnotation>{tBoard('loading')}</MonoAnnotation> : null}
      </div>
    </AccountGate>
  );
}
