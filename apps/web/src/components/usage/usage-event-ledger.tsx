'use client';

import { EmptyState } from '@/components/ui/states';
import { MonoAnnotation } from '@/components/ui/mono-annotation';

/**
 * The event log, as a ledger.
 *
 * Three columns: when it happened, what happened, and how much of it. The
 * rule opens the ledger and every row is separated by a hairline - a list
 * of events is a list, not a set of cards.
 *
 * The rows are whatever the API carries at the detail it carries: the days
 * of the period, the tools that were used, or the single total of a kind
 * the API does not break down. Nothing is written into a row that the API
 * did not say.
 */

export interface UsageLogRow {
  /** When it happened. */
  when: string;
  /** What happened. */
  event: string;
  /** How much of it. */
  detail: string;
}

export interface UsageEventLedgerProps {
  rows: UsageLogRow[];
  /** The column headings. */
  labels: { when: string; event: string; detail: string };
  /** A note under the ledger: where the full log lives. */
  note?: string;
  /** What to say when there is nothing to log. */
  emptyTitle: string;
  className?: string;
}

export function UsageEventLedger({
  rows,
  labels,
  note,
  emptyTitle,
  className,
}: UsageEventLedgerProps) {
  if (rows.length === 0) {
    return (
      <div className={className}>
        <EmptyState title={emptyTitle} />
      </div>
    );
  }

  return (
    <div className={className}>
      <div className="grid grid-cols-[150px_120px_minmax(0,1fr)] gap-4 border-b border-foreground pb-2 text-[12px] text-muted-foreground">
        <span>{labels.when}</span>
        <span>{labels.event}</span>
        <span>{labels.detail}</span>
      </div>
      <div data-testid="usage-log">
        {rows.map((row, index) => (
          <div
            key={`${row.when}-${row.event}-${index}`}
            className="grid grid-cols-[150px_120px_minmax(0,1fr)] gap-4 border-b border-border py-2"
          >
            <MonoAnnotation>{row.when}</MonoAnnotation>
            <span className="font-mono text-[12px] font-medium text-foreground">{row.event}</span>
            <span className="text-[13px] text-foreground">{row.detail}</span>
          </div>
        ))}
      </div>
      {note ? <p className="mt-3 text-[12px] leading-4 text-muted-foreground">{note}</p> : null}
    </div>
  );
}
