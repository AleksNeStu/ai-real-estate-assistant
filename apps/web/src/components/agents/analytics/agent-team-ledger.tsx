'use client';

import { useTranslations } from 'next-intl';

import { MonoAnnotation } from '@/components/ui/mono-annotation';
import { cn } from '@/lib/utils';

/**
 * The team, as a ledger.
 *
 * A comparison of people is a table, and the design draws it as a table:
 * a head row under an ink rule, then one row per agent with the numbers in
 * mono and the goal as a bar at the end.
 *
 * The API knows different agents to different depths - the agent who is
 * looking has their own numbers in full, the leaderboard carries a name
 * and one metric, the agents who need support carry their leads and their
 * conversion. A cell the API does not carry says so with a dash; it is
 * never filled in from another row.
 */

export interface TeamRow {
  /** The agent. */
  name: string;
  /** How many leads they hold. `null` when the API does not say. */
  leads?: number | null;
  /** Their conversion rate, as a percentage. `null` when unknown. */
  conversion?: number | null;
  /** Their closed deals. `null` when unknown. */
  deals?: number | null;
  /** The goal bar: how far along they are, and whether it is met. */
  goal?: { percent: number; achieved: boolean } | null;
  /** Whether this is the agent who is looking. */
  isCurrent?: boolean;
}

export interface AgentTeamLedgerProps {
  rows: TeamRow[];
  /** The heading of the goal column - what the bar is measured against. */
  goalLabel: string;
  className?: string;
}

export function AgentTeamLedger({ rows, goalLabel, className }: AgentTeamLedgerProps) {
  const t = useTranslations('pages.agentAnalytics.board.team');

  return (
    <div className={cn('flex flex-col gap-2', className)}>
      <div
        className="grid grid-cols-[minmax(0,1.4fr)_0.8fr_0.8fr_0.8fr_minmax(0,1.4fr)] gap-3 border-b border-foreground pb-2 text-[12px] text-muted-foreground"
        data-testid="team-ledger-head"
      >
        <span>{t('agent')}</span>
        <span>{t('leads')}</span>
        <span>{t('conversion')}</span>
        <span>{t('deals')}</span>
        <span>{goalLabel}</span>
      </div>

      {rows.length === 0 ? (
        <p className="py-3 text-[13px] text-muted-foreground">{t('empty')}</p>
      ) : (
        rows.map((row) => (
          <div
            key={row.name}
            data-testid="team-ledger-row"
            className="grid grid-cols-[minmax(0,1.4fr)_0.8fr_0.8fr_0.8fr_minmax(0,1.4fr)] items-center gap-3 border-b border-border py-2.5"
          >
            <span className="truncate text-[13px] font-medium text-foreground">
              {row.name}
              {row.isCurrent ? <span className="ml-2 font-mono text-[11px] text-muted-foreground">({t('you')})</span> : null}
            </span>
            <span className="font-mono text-[13px] text-foreground">
              {row.leads === null || row.leads === undefined ? t('unknown') : row.leads}
            </span>
            <span className="font-mono text-[13px] text-foreground">
              {row.conversion === null || row.conversion === undefined
                ? t('unknown')
                : `${row.conversion}%`}
            </span>
            <span className="font-mono text-[13px] text-foreground">
              {row.deals === null || row.deals === undefined ? t('unknown') : row.deals}
            </span>
            <span className="flex items-center gap-2">
              {row.goal ? (
                <>
                  <span className="h-1.5 flex-1 overflow-hidden rounded-[1px] bg-muted">
                    <span
                      className={cn('block h-full rounded-[1px]', row.goal.achieved ? 'bg-foreground' : 'bg-warning')}
                      style={{ width: `${Math.min(100, Math.max(0, row.goal.percent))}%` }}
                    />
                  </span>
                  <MonoAnnotation>{`${Math.round(row.goal.percent)}%`}</MonoAnnotation>
                </>
              ) : (
                <MonoAnnotation>{t('unknown')}</MonoAnnotation>
              )}
            </span>
          </div>
        ))
      )}
    </div>
  );
}
