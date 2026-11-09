'use client';

import { useTranslations } from 'next-intl';

import { MonoAnnotation } from '@/components/ui/mono-annotation';
import { StatTile } from '@/components/ui/stat-tile';
import { cn } from '@/lib/utils';
import type { LeadWithScore, LeadStatus } from '@/lib/types';

/**
 * The funnel, as a strip of stat tiles.
 *
 * The strip says where the leads drop off: how many reached every stage.
 * A lead that is converted has passed through every stage before it, so the
 * stages are cumulative - the number under "Contacted" counts the leads
 * that are contacted and the ones that moved past.
 *
 * Every number is counted from the leads the API returned. A stage the API
 * does not carry a number for is not drawn.
 */

/** The stages of the funnel, in the order a lead passes through them. */
const STAGES: Array<{ key: string; status: LeadStatus[] | null }> = [
  // Every lead starts as a lead - including the ones that were lost, which
  // never got further than this.
  { key: 'new', status: null },
  { key: 'contacted', status: ['contacted', 'qualified', 'converted'] },
  { key: 'qualified', status: ['qualified', 'converted'] },
  { key: 'converted', status: ['converted'] },
];

export interface FunnelStage {
  /** The stage key, used to look the label up. */
  key: string;
  /** How many leads reached this stage. */
  value: number;
  /** This stage as a percentage of the previous one. `null` for the first. */
  rate: number | null;
}

/**
 * Count the funnel from the leads.
 *
 * A lead that is lost dropped out of the pipeline, so it never reached the
 * stages after the one it left in: it is counted where it stopped and
 * nowhere else.
 */
export function buildFunnelStages(leads: LeadWithScore[]): FunnelStage[] {
  const stages: FunnelStage[] = [];

  for (const stage of STAGES) {
    const value = leads.filter(
      (lead) => stage.status === null || stage.status.includes(lead.status)
    ).length;
    const previous = stages.length > 0 ? stages[stages.length - 1].value : null;
    stages.push({
      key: stage.key,
      value,
      rate: previous === null || previous === 0 ? null : Math.round((value / previous) * 100),
    });
  }

  return stages;
}

export interface LeadFunnelProps {
  stages: FunnelStage[];
  className?: string;
}

export function LeadFunnel({ stages, className }: LeadFunnelProps) {
  const t = useTranslations('pages.leads.board.funnel');
  const first = stages[0]?.value ?? 0;

  return (
    <div
      className={cn(
        'grid grid-cols-2 gap-x-6 gap-y-5 border-b border-border pb-5 md:grid-cols-4',
        className
      )}
    >
      {stages.map((stage) => {
        const width = first > 0 ? Math.max(2, Math.round((stage.value / first) * 100)) : 0;
        return (
          <div key={stage.key} className="flex flex-col gap-1.5">
            <StatTile
              value={stage.value}
              label={t(stage.key)}
              hint={
                stage.rate === null ? null : t('rate', { value: stage.rate })
              }
            />
            <div className="h-1.5 w-full overflow-hidden rounded-[1px] bg-muted">
              <div className="h-full rounded-[1px] bg-foreground" style={{ width: `${width}%` }} />
            </div>
          </div>
        );
      })}
    </div>
  );
}

/**
 * The note under the strip: how much of the whole board is on screen.
 *
 * The API pages the list, so a board that holds more leads than it shows
 * says so rather than pretending it holds them all.
 */
export function LeadFunnelNote({ shown, total }: { shown: number; total: number }) {
  const t = useTranslations('pages.leads.board');
  if (total <= shown) return null;
  return <MonoAnnotation>{t('showing', { shown, total })}</MonoAnnotation>;
}
