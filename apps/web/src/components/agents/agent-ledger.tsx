'use client';

import Link from 'next/link';
import { useTranslations } from 'next-intl';

import { Ledger } from '@/components/ui/ledger';
import type { AgentProfile } from '@/lib/types';

/**
 * The agent directory, as a ledger.
 *
 * A catalogue of agents is a list, not a set of objects, so the prototype
 * draws it as rows under an ink rule: the agent on the left, the agency and
 * the areas it covers in the middle, the rating, the number of reviews and
 * the number of listings in mono on the right, and the way in at the end of
 * the row.
 *
 * The number of listings is the count the API carries - the number of that
 * agent's active listings in the catalogue, and the same number the sort
 * orders the catalogue by. Where the response does not carry it, the cell
 * says nothing rather than claiming zero.
 *
 * The card that used to draw them is still there for the surfaces that want
 * an object - this row is the list.
 */

export interface AgentLedgerProps {
  agents: AgentProfile[];
  /** The locale the profile links carry. */
  locale: string;
  className?: string;
}

function initialsOf(name: string): string {
  return (
    name
      .split(/\s+/)
      .filter(Boolean)
      .map((part) => part[0])
      .join('')
      .toUpperCase()
      .slice(0, 2) || '·'
  );
}

export function AgentLedger({ agents, locale, className }: AgentLedgerProps) {
  const t = useTranslations('agents');

  return (
    <Ledger className={className}>
      <div
        className={[
          'hidden gap-3.5 border-b border-foreground px-6 py-2.5',
          'text-[12px] text-muted-foreground',
          'md:grid md:grid-cols-[40px_1.4fr_1.1fr_1.4fr_72px_72px_72px_120px]',
        ].join(' ')}
      >
        <span />
        <span>{t('directory.columns.agent')}</span>
        <span>{t('directory.columns.agency')}</span>
        <span>{t('directory.columns.areas')}</span>
        <span className="text-right">{t('directory.columns.rating')}</span>
        <span className="text-right">{t('directory.columns.reviews')}</span>
        <span className="text-right">{t('directory.columns.listings')}</span>
        <span />
      </div>

      {agents.map((agent) => {
        const displayName =
          agent.name || agent.professional_email?.split('@')[0] || t('profile.defaultName');
        const specialty = agent.specialties?.length ? agent.specialties.join(', ') : null;
        const languages = agent.languages?.length ? agent.languages.join(', ') : null;
        const subtitle = [specialty, languages].filter(Boolean).join(' · ');
        const rating =
          agent.average_rating > 0 ? agent.average_rating.toFixed(1) : t('directory.noRating');

        return (
          <Link
            key={agent.id}
            href={`/${locale}/agents/${agent.id}`}
            data-testid="agent-row"
            className={[
              'grid grid-cols-[minmax(0,1fr)_auto] items-center gap-x-4 gap-y-1',
              'border-b border-border px-6 py-3 transition-colors hover:bg-muted',
              'md:grid-cols-[40px_1.4fr_1.1fr_1.4fr_72px_72px_72px_120px] md:gap-3.5 md:py-2.5',
            ].join(' ')}
          >
            <span
              aria-hidden="true"
              className={[
                'hidden size-8 items-center justify-center rounded-full border border-border',
                'bg-muted text-[11px] font-semibold text-foreground',
                'md:flex',
              ].join(' ')}
            >
              {initialsOf(displayName)}
            </span>

            <span className="flex min-w-0 flex-col">
              <span className="flex items-center gap-1.5">
                <span className="truncate text-[14px] font-medium text-foreground">
                  {displayName}
                </span>
                {agent.is_verified ? (
                  <span className="shrink-0 rounded-sm border border-border px-[5px] font-mono text-[10px] font-medium text-success">
                    {t('verified')}
                  </span>
                ) : null}
              </span>
              {subtitle ? (
                <span className="truncate text-[12px] leading-4 text-muted-foreground">
                  {subtitle}
                </span>
              ) : null}
            </span>

            <span className="hidden truncate text-[13px] text-foreground md:block">
              {agent.agency_name || '—'}
            </span>

            <span className="hidden truncate text-[13px] text-muted-foreground md:block">
              {agent.service_areas?.length ? agent.service_areas.join(', ') : '—'}
            </span>

            <span className="text-right font-mono text-[13px] font-medium text-foreground">
              ★ {rating}
            </span>

            <span className="text-right font-mono text-[13px] text-muted-foreground">
              {agent.total_reviews}
            </span>

            <span className="text-right font-mono text-[13px] text-muted-foreground">
              {agent.listings_count ?? '—'}
            </span>

            <span className="col-span-2 text-right text-[13px] font-medium text-foreground md:col-span-1">
              {t('viewProfile')} →
            </span>
          </Link>
        );
      })}
    </Ledger>
  );
}
