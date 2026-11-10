import type { ReactNode } from 'react';

import { MonoAnnotation as LedgerMonoAnnotation } from '@/components/ui/ledger';
import { cn } from '@/lib/utils';

/**
 * The mono annotation.
 *
 * Small mono text is allowed only when it is data: a route, a source, a
 * count, a status. It is never a decorative label and never an eyebrow -
 * a label states what a thing is, and does not shout.
 *
 * The base is the annotation the ledger already landed, so the two cannot
 * drift apart; this adds the one thing the ledger's version does not have,
 * a tone for the statuses that carry a meaning (green, amber, red).
 */
export type MonoTone = 'neutral' | 'success' | 'warning' | 'destructive';

const TONE_CLASS: Record<MonoTone, string> = {
  neutral: '',
  success: 'text-success',
  warning: 'text-warning',
  destructive: 'text-destructive',
};

export interface MonoAnnotationProps {
  /** The data. A route, a source, a count, a status. */
  children: ReactNode;
  /** The meaning the annotation carries, when it carries one. */
  tone?: MonoTone;
  className?: string;
}

export function MonoAnnotation({ children, tone = 'neutral', className }: MonoAnnotationProps) {
  return (
    <LedgerMonoAnnotation
      data-testid="mono-annotation"
      className={cn(TONE_CLASS[tone], className)}
    >
      {children}
    </LedgerMonoAnnotation>
  );
}
