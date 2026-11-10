'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { useLocale, useTranslations } from 'next-intl';

import { AgentCoaching, type CoachingNote } from '@/components/agents/analytics/agent-coaching';
import { AgentKpiStrip, type AgentKpi } from '@/components/agents/analytics/agent-kpi-strip';
import { AgentTeamLedger, type TeamRow } from '@/components/agents/analytics/agent-team-ledger';
import { AgentTrendChart } from '@/components/agents/analytics/agent-trend-chart';
import { AccountGate } from '@/components/shell/gate';
import { MonoAnnotation } from '@/components/ui/mono-annotation';
import { PageHeader } from '@/components/ui/page-header';
import { ErrorState } from '@/components/ui/states';
import {
  getAgentMetrics,
  getAgentsNeedingSupport,
  getCoachingInsights,
  getGoalProgress,
  getPerformanceTrends,
  getTeamComparison,
  getTopPerformers,
} from '@/lib/api';
import type {
  AgentMetrics,
  AgentNeedingSupport,
  CoachingInsight,
  GoalProgress,
  PerformanceTrendPoint,
  TeamComparison,
  TopPerformerEntry,
} from '@/lib/types';

/**
 * The agent analytics.
 *
 * One agent's work, and the team's: the numbers that judge the work, the
 * table that puts the agents beside each other, the months of deals, and
 * the notes that say what to do about it.
 *
 * The period tabs drive every number on the page. The team views - the
 * leaderboard and the agents who need support - are an administrator's
 * view, so they are fetched on their own: an agent who is not one still
 * gets their own numbers, without a wall of errors.
 */

/** The periods the page speaks about. */
const PERIODS = [
  { key: '30d', days: 30, interval: 'day' as const, periods: 30, label: '30 d' },
  { key: '90d', days: 90, interval: 'week' as const, periods: 13, label: '90 d' },
  { key: '12mo', days: 365, interval: 'month' as const, periods: 12, label: '12 mo' },
];

/** The window the API is asked about, in days, counted back from today. */
function periodBounds(days: number): { period_start: string; period_end: string } {
  const end = new Date();
  const start = new Date(end.getTime() - days * 24 * 60 * 60 * 1000);
  return { period_start: start.toISOString(), period_end: end.toISOString() };
}

export default function AgentAnalyticsPage() {
  const t = useTranslations('pages.agentAnalytics');
  const tBoard = useTranslations('pages.agentAnalytics.board');
  const tCommon = useTranslations('common');
  const locale = useLocale();

  const [periodKey, setPeriodKey] = useState(PERIODS[1].key);
  const [metrics, setMetrics] = useState<AgentMetrics | null>(null);
  const [comparison, setComparison] = useState<TeamComparison | null>(null);
  const [trends, setTrends] = useState<PerformanceTrendPoint[]>([]);
  const [insights, setInsights] = useState<CoachingInsight[]>([]);
  const [goals, setGoals] = useState<GoalProgress[]>([]);
  const [performers, setPerformers] = useState<TopPerformerEntry[]>([]);
  const [support, setSupport] = useState<AgentNeedingSupport[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const period = PERIODS.find((entry) => entry.key === periodKey) ?? PERIODS[1];

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const bounds = periodBounds(period.days);
      const [metricsData, comparisonData, trendsData, insightsData, goalsData] = await Promise.all([
        getAgentMetrics(bounds),
        getTeamComparison(bounds),
        getPerformanceTrends({ interval: period.interval, periods: period.periods }),
        getCoachingInsights(),
        getGoalProgress(),
      ]);

      setMetrics(metricsData);
      setComparison(comparisonData);
      setTrends(trendsData.trends);
      setInsights(insightsData.insights);
      setGoals(goalsData.goals);

      // The team views are an administrator's view. They are fetched on their
      // own so that an agent without them still gets their own numbers.
      Promise.all([
        getTopPerformers({ metric: 'deals', limit: 5, period_days: period.days }),
        getAgentsNeedingSupport({ threshold_days: 30 }),
      ])
        .then(([top, needing]) => {
          setPerformers(top.performers ?? []);
          setSupport(needing.agents ?? []);
        })
        .catch(() => {
          setPerformers([]);
          setSupport([]);
        });
    } catch (err) {
      console.error(t('errors.fetch'), err);
      setError(t('errors.load'));
    } finally {
      setLoading(false);
    }
  }, [period, t]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const kpis = useMemo<AgentKpi[]>(() => {
    if (!metrics) return [];
    const goal = goals.find((entry) => entry.goal_type === 'deals');
    const hours = metrics.avg_time_to_first_contact_hours;

    return [
      {
        key: 'leads',
        value: metrics.total_leads,
        label: tBoard('kpis.leads'),
        hint: t('metrics.newThisWeek', { count: metrics.new_leads_week }),
      },
      {
        key: 'response',
        value:
          hours === null || hours === undefined
            ? '—'
            : hours < 1
              ? `${Math.round(hours * 60)} min`
              : `${hours.toFixed(1)} h`,
        label: tBoard('kpis.response'),
        hint: tBoard('kpis.responseHint'),
      },
      {
        key: 'conversion',
        value: `${metrics.lead_to_qualified_rate.toFixed(1)}%`,
        label: tBoard('kpis.leadToQualified'),
        hint: tBoard('kpis.leadToQualifiedHint', {
          rate: metrics.qualified_to_deal_rate.toFixed(1),
        }),
      },
      {
        key: 'deals',
        value: metrics.closed_deals,
        label: tBoard('kpis.dealsClosed'),
        hint: goal
          ? tBoard('kpis.dealsGoal', { current: goal.current_value, target: goal.target_value })
          : t('metrics.closed', { count: metrics.total_deals }),
      },
      {
        key: 'pipeline',
        value: new Intl.NumberFormat(locale, {
          style: 'currency',
          currency: 'EUR',
          notation: 'compact',
          maximumFractionDigits: 1,
        }).format(metrics.total_deal_value),
        label: tBoard('kpis.pipeline'),
        hint: t('metrics.activeDeals'),
      },
    ];
  }, [goals, locale, metrics, t, tBoard]);

  const teamRows = useMemo<TeamRow[]>(() => {
    const rows: TeamRow[] = [];

    if (metrics && comparison) {
      const goal = goals.find((entry) => entry.goal_type === 'deals');
      rows.push({
        name: comparison.agent_name || tBoard('team.you'),
        leads: metrics.total_leads,
        conversion: Number(metrics.overall_conversion_rate.toFixed(1)),
        deals: metrics.closed_deals,
        goal: goal
          ? { percent: goal.progress_percent, achieved: goal.is_achieved }
          : null,
        isCurrent: true,
      });
    }

    for (const performer of performers) {
      rows.push({
        name: performer.agent_name,
        leads: null,
        conversion: null,
        deals: performer.metric_value,
        goal: null,
      });
    }

    for (const agent of support) {
      rows.push({
        name: agent.agent_name,
        leads: agent.total_leads,
        conversion: Number(agent.conversion_rate.toFixed(1)),
        deals: null,
        goal: null,
      });
    }

    // One row per agent: the leaderboard and the support list may name the
    // same person, and the row with more of the numbers wins.
    const seen = new Map<string, TeamRow>();
    for (const row of rows) {
      const existing = seen.get(row.name);
      if (!existing) {
        seen.set(row.name, row);
        continue;
      }
      seen.set(row.name, {
        ...existing,
        leads: existing.leads ?? row.leads,
        conversion: existing.conversion ?? row.conversion,
        deals: existing.deals ?? row.deals,
        goal: existing.goal ?? row.goal,
      });
    }
    return [...seen.values()];
  }, [comparison, goals, metrics, performers, support, tBoard]);

  const notes = useMemo<CoachingNote[]>(
    () =>
      insights.slice(0, 5).map((insight) => ({
        category: insight.category,
        title: insight.title,
        description: insight.description,
        recommendation: insight.actionable_recommendation,
      })),
    [insights]
  );

  const trendPoints = useMemo(
    () => trends.map((trend) => ({ period: trend.period, value: trend.deals_closed })),
    [trends]
  );

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
    <AccountGate route="agent-analytics">
      <div className="flex flex-col gap-5 px-6 py-6">
        <PageHeader
          title={tBoard('title')}
          description={
            comparison
              ? tBoard('description', {
                  agents: comparison.total_agents,
                  period: period.label,
                })
              : tBoard('description', { agents: 0, period: period.label })
          }
          actions={
            <div className="flex overflow-hidden rounded-md border border-border">
              {PERIODS.map((entry) => {
                const active = entry.key === periodKey;
                return (
                  <button
                    key={entry.key}
                    type="button"
                    onClick={() => setPeriodKey(entry.key)}
                    aria-pressed={active}
                    data-testid={`agent-period-${entry.key}`}
                    className="h-8 border-0 border-r border-border px-3 text-[13px] font-medium transition-colors last:border-r-0"
                    style={{
                      backgroundColor: active ? 'hsl(var(--foreground))' : 'transparent',
                      color: active ? 'hsl(var(--background))' : 'hsl(var(--foreground))',
                    }}
                  >
                    {entry.label}
                  </button>
                );
              })}
            </div>
          }
        />

        {loading ? (
          <MonoAnnotation>{t('loading')}</MonoAnnotation>
        ) : (
          <AgentKpiStrip kpis={kpis} />
        )}

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)]">
          <div className="flex flex-col gap-5">
            <section className="flex flex-col gap-2">
              <span className="text-[15px] font-semibold text-foreground">
                {t('team.title')}
              </span>
              <AgentTeamLedger rows={teamRows} goalLabel={tBoard('team.goal')} />
            </section>

            <AgentTrendChart
              points={trendPoints}
              title={tBoard('dealsPerMonth')}
              caption={tBoard('months', { count: trendPoints.length })}
            />
          </div>

          <AgentCoaching
            topPerformer={
              performers[0]
                ? {
                    name: performers[0].agent_name,
                    metricValue: performers[0].metric_value,
                    rank: performers[0].rank,
                  }
                : null
            }
            needsSupport={
              support[0]
                ? {
                    name: support[0].agent_name,
                    daysWithoutDeal: support[0].days_without_deal,
                    totalLeads: support[0].total_leads,
                    conversionRate: Number(support[0].conversion_rate.toFixed(1)),
                  }
                : null
            }
            notes={notes}
          />
        </div>
      </div>
    </AccountGate>
  );
}
