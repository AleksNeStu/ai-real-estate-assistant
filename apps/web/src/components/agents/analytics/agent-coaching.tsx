'use client';

import { useTranslations } from 'next-intl';

import { MonoAnnotation } from '@/components/ui/mono-annotation';
import { cn } from '@/lib/utils';

/**
 * The coaching column.
 *
 * Three panels down the right of the page: the agent at the top, the agent
 * who needs support, and the coaching notes. Each panel is a small card -
 * these are objects, not lists - and each one says what it holds before it
 * holds it.
 *
 * The notes are generated from the team's numbers, so the panel says so and
 * asks that they be checked before they are acted on.
 */

export interface CoachingNote {
  /** The kind of note: a strength, an improvement, an opportunity. */
  category: 'strength' | 'improvement' | 'opportunity';
  /** The headline. */
  title: string;
  /** What the note says. */
  description: string;
  /** What to do about it. */
  recommendation: string;
}

export interface AgentCoachingProps {
  /** The agent at the top of the team, if the API named one. */
  topPerformer?: { name: string; metricValue: number; rank: number } | null;
  /** The agent who needs support, if the API named one. */
  needsSupport?: {
    name: string;
    daysWithoutDeal: number;
    totalLeads: number;
    conversionRate: number;
  } | null;
  notes: CoachingNote[];
  className?: string;
}

export function AgentCoaching({
  topPerformer,
  needsSupport,
  notes,
  className,
}: AgentCoachingProps) {
  const t = useTranslations('pages.agentAnalytics.board.coaching');

  return (
    <div className={cn('flex flex-col gap-4', className)}>
      <section className="rounded-lg border border-border">
        <h3 className="border-b border-border px-4 py-2.5 text-[13px] font-semibold text-foreground">
          {t('topPerformer')}
        </h3>
        <div className="flex flex-col gap-1 px-4 py-3">
          {topPerformer ? (
            <>
              <span className="text-[14px] font-medium text-foreground">{topPerformer.name}</span>
              <span className="text-[13px] leading-[19px] text-muted-foreground">
                {t('topPerformerBody', { metric: topPerformer.metricValue, rank: topPerformer.rank })}
              </span>
            </>
          ) : (
            <span className="text-[13px] text-muted-foreground">{t('none')}</span>
          )}
        </div>
      </section>

      <section className="rounded-lg border border-border">
        <h3 className="flex items-center gap-2 border-b border-border px-4 py-2.5 text-[13px] font-semibold text-foreground">
          <span
            className="inline-block size-2 rounded-full bg-warning"
            aria-hidden="true"
          />
          {t('needsSupport')}
        </h3>
        <div className="flex flex-col gap-1 px-4 py-3">
          {needsSupport ? (
            <>
              <span className="text-[14px] font-medium text-foreground">{needsSupport.name}</span>
              <span className="text-[13px] leading-[19px] text-muted-foreground">
                {t('needsSupportBody', {
                  days: needsSupport.daysWithoutDeal,
                  leads: needsSupport.totalLeads,
                  conversion: needsSupport.conversionRate,
                })}
              </span>
            </>
          ) : (
            <span className="text-[13px] text-muted-foreground">{t('none')}</span>
          )}
        </div>
      </section>

      <section className="rounded-lg border border-border">
        <h3 className="border-b border-border px-4 py-2.5 text-[13px] font-semibold text-foreground">
          {t('insights')}
        </h3>
        {notes.length === 0 ? (
          <p className="px-4 py-3 text-[13px] text-muted-foreground">{t('empty')}</p>
        ) : (
          notes.map((note, index) => (
            <div
              key={`${note.title}-${index}`}
              className="flex flex-col gap-1 border-b border-border px-4 py-2.5 last:border-b-0"
            >
              <span className="text-[13px] font-medium text-foreground">{note.title}</span>
              <span className="text-[13px] leading-[19px] text-muted-foreground">
                {note.description}
              </span>
              <MonoAnnotation>{`→ ${note.recommendation}`}</MonoAnnotation>
            </div>
          ))
        )}
        <span className="block px-4 py-2 text-[11px] leading-4 text-muted-foreground">
          {t('disclaimer')}
        </span>
      </section>
    </div>
  );
}
