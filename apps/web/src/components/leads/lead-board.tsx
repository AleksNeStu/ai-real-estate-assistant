'use client';

import { useLocale, useTranslations } from 'next-intl';

import { MonoAnnotation } from '@/components/ui/mono-annotation';
import { formatTimeAgo, leadInterestParts } from '@/components/leads/lead-format';
import { cn } from '@/lib/utils';
import type { LeadWithScore, LeadStatus } from '@/lib/types';

/**
 * The board: five columns, one per status.
 *
 * A list of leads is a list, but a board is a list read in five directions
 * at once, so each column is its own panel with its own rule and the cards
 * inside it are the objects - a lead is an object, a card is fair.
 *
 * The five columns are the five statuses the API carries. The card states
 * the score in mono, the interest line below it, and the moment the lead
 * was last seen. The button moves the lead one stage along.
 */

/** The columns of the board, in the order a lead travels through them. */
export const LEAD_COLUMNS: LeadStatus[] = [
  'new',
  'contacted',
  'qualified',
  'converted',
  'lost',
];

/** The stage a lead moves to when it is advanced. `null` when there is none. */
export function nextStatus(status: LeadStatus): LeadStatus | null {
  const index = LEAD_COLUMNS.indexOf(status);
  if (index < 0 || index >= LEAD_COLUMNS.length - 1) return null;
  // "Lost" is not a stage a lead advances into.
  if (LEAD_COLUMNS[index + 1] === 'lost') return null;
  return LEAD_COLUMNS[index + 1];
}

export interface LeadBoardProps {
  leads: LeadWithScore[];
  /** Called with the lead and the status it should move to. */
  onAdvance?: (lead: LeadWithScore, status: LeadStatus) => void;
  /** The reference point for "how long ago", in milliseconds. */
  now: number | null;
  className?: string;
}

export function LeadBoard({ leads, onAdvance, now, className }: LeadBoardProps) {
  const t = useTranslations('pages.leads.board');
  const tStatus = useTranslations('pages.leads.status');
  const locale = useLocale();

  return (
    <div
      className={cn(
        'grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5',
        className
      )}
    >
      {LEAD_COLUMNS.map((status) => {
        const column = leads.filter((lead) => lead.status === status);
        return (
          <section
            key={status}
            aria-label={tStatus(status)}
            className="flex flex-col gap-2 rounded-lg bg-muted p-2"
          >
            <div className="flex items-baseline justify-between gap-2 px-1 pt-1">
              <span className="text-[13px] font-semibold text-foreground">
                {tStatus(status)}
              </span>
              <MonoAnnotation>{column.length}</MonoAnnotation>
            </div>

            {column.length === 0 ? (
              <p className="px-1 py-2 text-[12px] leading-4 text-muted-foreground">
                {t('emptyColumn')}
              </p>
            ) : (
              column.map((lead) => {
                const target = nextStatus(lead.status);
                return (
                  <article
                    key={lead.id}
                    data-testid="lead-card"
                    className="flex flex-col gap-1.5 rounded-md border border-border bg-background p-2.5"
                  >
                    <div className="flex items-baseline justify-between gap-2">
                      <span className="truncate text-[13px] font-medium text-foreground">
                        {lead.name?.trim() || lead.email?.trim() || t('anonymous')}
                      </span>
                      <span
                        className={cn(
                          'font-mono text-[12px] font-semibold',
                          lead.total_score >= 80 ? 'text-success' : 'text-foreground'
                        )}
                      >
                        {lead.total_score}
                      </span>
                    </div>

                    <LeadInterest lead={lead} />

                    <div className="mt-0.5 flex items-center justify-between gap-2">
                      <MonoAnnotation>
                        {formatTimeAgo(lead.last_activity_at, locale, now)}
                      </MonoAnnotation>
                      {target && onAdvance ? (
                        <button
                          type="button"
                          onClick={() => onAdvance(lead, target)}
                          className="rounded-sm px-0 py-0 text-[12px] font-medium text-foreground hover:underline"
                        >
                          {t('advance')}
                        </button>
                      ) : null}
                    </div>
                  </article>
                );
              })
            )}
          </section>
        );
      })}
    </div>
  );
}

/**
 * The line under a lead's name.
 *
 * It says what the lead was after, in the words the API holds: the places
 * it asked about, the budget it gave, the source it came from. When the
 * lead carries none of those the line is not drawn at all.
 */
function LeadInterest({ lead }: { lead: LeadWithScore }) {
  const t = useTranslations('pages.leads.board');
  const { locations, budgetMax, source } = leadInterestParts(lead);

  const parts: string[] = [];
  if (locations) parts.push(locations);
  if (budgetMax !== null) parts.push(t('budgetMax', { amount: budgetMax }));
  if (source) parts.push(source);

  if (parts.length === 0) return null;

  return (
    <p className="text-[12px] leading-[17px] text-muted-foreground">{parts.join(' · ')}</p>
  );
}
