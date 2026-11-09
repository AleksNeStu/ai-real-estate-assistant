import type { ReactNode } from 'react';

import { cn } from '@/lib/utils';

/**
 * The ledger: rows separated by hairlines, opened by a 1px ink rule.
 *
 * The design uses it wherever a list is a list - features, comparisons,
 * catalogues, routes - and reserves cards for the things that are objects:
 * a listing, a tool result, a dialog.
 */

export function Ledger({ className, children }: { className?: string; children: ReactNode }) {
  return <div className={cn('border-t border-foreground', className)}>{children}</div>;
}

export function LedgerRow({
  className,
  children,
}: {
  className?: string;
  children: ReactNode;
}) {
  return (
    <div
      className={cn(
        'grid items-baseline gap-6 border-b border-border py-[18px]',
        className
      )}
    >
      {children}
    </div>
  );
}

/** The mono annotation: a number, a route, a source, a status. */
export function MonoAnnotation({
  className,
  children,
}: {
  className?: string;
  children: ReactNode;
}) {
  return (
    <span className={cn('font-mono text-[12px] leading-4 text-muted-foreground', className)}>
      {children}
    </span>
  );
}

/** A small label in the muted foreground - the secondary voice of the page. */
export function MutedText({ className, children }: { className?: string; children: ReactNode }) {
  return <span className={cn('text-muted-foreground', className)}>{children}</span>;
}
