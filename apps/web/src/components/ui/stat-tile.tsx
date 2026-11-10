import type { ReactNode } from 'react';

import { cn } from '@/lib/utils';

/**
 * The stat tile: a number in mono, a label under it.
 *
 * The landing's stats row is this, generalised. One number, one thing the
 * number is about - nothing else. The value is the only loud part of the
 * tile; the label is the page's muted voice, and the hint (a source, a
 * date, a unit) stays in mono because it is data.
 */
export interface StatTileProps {
  /** The number. Mono, semibold - the loudest thing in the tile. */
  value: ReactNode;
  /** What the number is about. Muted, small. */
  label: ReactNode;
  /** An optional mono note: a source, a period, a unit. */
  hint?: ReactNode;
  className?: string;
}

export function StatTile({ value, label, hint, className }: StatTileProps) {
  return (
    <div data-testid="stat-tile" className={cn('flex flex-col gap-1', className)}>
      <span className="font-mono text-h3 font-semibold text-foreground">{value}</span>
      <span className="text-annot text-muted-foreground">{label}</span>
      {hint ? <span className="font-mono text-annot text-muted-foreground">{hint}</span> : null}
    </div>
  );
}
