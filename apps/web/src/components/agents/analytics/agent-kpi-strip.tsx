'use client';

import { StatTile } from '@/components/ui/stat-tile';
import { cn } from '@/lib/utils';

/**
 * The KPI strip.
 *
 * Five numbers, one per thing the agent is judged on. Each tile states the
 * number, what it is about, and - where the API carries one - the note that
 * makes it a fact rather than a number: the change against the previous
 * period, the goal it is measured against.
 *
 * A tile that has no note says only its number. Nothing is filled in to
 * make the strip look even.
 */

export interface AgentKpi {
  /** The key of the tile, used to look the label up. */
  key: string;
  /** The number. */
  value: string | number;
  /** What the number is about. */
  label: string;
  /** The note: the change, the goal, the unit. */
  hint?: string;
}

export interface AgentKpiStripProps {
  kpis: AgentKpi[];
  className?: string;
}

export function AgentKpiStrip({ kpis, className }: AgentKpiStripProps) {
  return (
    <div
      className={cn(
        'grid grid-cols-2 gap-x-6 gap-y-4 border-b border-border pb-5 md:grid-cols-5',
        className
      )}
      data-testid="agent-kpi-strip"
    >
      {kpis.map((kpi) => (
        <StatTile
          key={kpi.key}
          value={kpi.value}
          label={kpi.label}
          hint={kpi.hint}
        />
      ))}
    </div>
  );
}
