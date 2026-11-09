'use client';

import { useTranslations } from 'next-intl';

import { MonoAnnotation } from '@/components/ui/mono-annotation';
import { leadInterestParts } from '@/components/leads/lead-format';
import { cn } from '@/lib/utils';
import type { LeadWithScore } from '@/lib/types';

/**
 * The rail beside the board: the leads worth the attention.
 *
 * A rail is a list read down a narrow column, so it is a ledger - a rule
 * under every row - and not a set of cards. The rows are the high-value
 * leads, ordered by the score, with the score in mono on the right.
 */

export interface HighValueRailProps {
  leads: LeadWithScore[];
  /** The score at which a lead counts as high-value. */
  threshold?: number;
  className?: string;
}

export function HighValueRail({
  leads,
  threshold = 80,
  className,
}: HighValueRailProps) {
  const t = useTranslations('pages.leads.board.highValue');
  const tBoard = useTranslations('pages.leads.board');
  const tStatus = useTranslations('pages.leads.status');

  const ordered = [...leads]
    .filter((lead) => lead.total_score >= threshold)
    .sort((a, b) => b.total_score - a.total_score);

  return (
    <aside className={cn('flex flex-col gap-3', className)}>
      <div className="flex flex-col gap-1">
        <span className="text-[14px] font-semibold text-foreground">{t('title')}</span>
        <span className="text-[12px] leading-4 text-muted-foreground">
          {t('hint', { threshold })}
        </span>
      </div>

      {ordered.length === 0 ? (
        <p className="border-t border-border py-3 text-[12px] leading-4 text-muted-foreground">
          {t('empty')}
        </p>
      ) : (
        <div className="border-t border-foreground">
          {ordered.map((lead) => {
            const { locations, budgetMax, source } = leadInterestParts(lead);
            const parts = [
              locations,
              budgetMax !== null ? tBoard('budgetMax', { amount: budgetMax }) : null,
              source,
            ].filter((part): part is string => Boolean(part));

            return (
              <div
                key={lead.id}
                data-testid="high-value-lead"
                className="grid grid-cols-[minmax(0,1fr)_auto] gap-x-2 gap-y-1 border-b border-border py-2.5"
              >
                <span className="truncate text-[13px] font-medium text-foreground">
                  {lead.name?.trim() || lead.email?.trim() || t('anonymous')}
                </span>
                <span className="font-mono text-[13px] font-semibold text-foreground">
                  {lead.total_score}
                </span>
                <span className="col-span-1 truncate text-[12px] leading-4 text-muted-foreground">
                  {parts.length ? parts.join(' · ') : t('noInterest')}
                </span>
                <span className="col-span-1 text-[12px] leading-4 text-muted-foreground">
                  {tStatus(lead.status)}
                </span>
              </div>
            );
          })}
        </div>
      )}

      <p className="rounded-md bg-muted p-3 text-[12px] leading-[18px] text-muted-foreground">
        {t('note')}{' '}
        <a
          href="https://propvectorai.com/?utm_source=realty.kittray.com&utm_medium=app&utm_campaign=propvector&utm_content=leads"
          className="font-medium text-foreground hover:underline"
          target="_blank"
          rel="noreferrer"
        >
          {t('noteLink')}
        </a>
      </p>
    </aside>
  );
}
