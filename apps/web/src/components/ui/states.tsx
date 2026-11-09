import * as React from 'react';
import { AlertTriangle, type LucideIcon } from 'lucide-react';

import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';

/**
 * The three states every data surface in the product can be in.
 *
 * Before this existed each route drew its own empty box and its own error
 * box, in a different radius, with a different icon and — in most cases —
 * with an English string hard-coded into the markup.
 *
 * The shape is the design's: flat, with a hairline rule instead of a dashed
 * card, and the icon beside the words rather than above them. A state is a
 * line in a ledger, not a panel.
 */

export interface EmptyStateProps {
  title: React.ReactNode;
  description?: React.ReactNode;
  icon?: LucideIcon;
  /** The single action that resolves the emptiness. */
  action?: React.ReactNode;
  className?: string;
}

export function EmptyState({
  title,
  description,
  icon: Icon,
  action,
  className,
}: EmptyStateProps) {
  return (
    <div
      className={cn('border-t border-foreground px-0 py-8', className)}
      role="status"
      aria-live="polite"
    >
      <div className="flex flex-col items-start gap-3">
        <div className="flex items-baseline gap-3">
          {Icon ? (
            <span className="text-muted-foreground" aria-hidden="true">
              <Icon className="size-4" />
            </span>
          ) : null}
          <p className="m-0 text-[15px] font-semibold leading-6 text-foreground">{title}</p>
        </div>
        {description ? (
          <p className="m-0 max-w-md text-[14px] leading-5 text-muted-foreground">{description}</p>
        ) : null}
        {action ? <div className="pt-1">{action}</div> : null}
      </div>
    </div>
  );
}

export interface ErrorStateProps {
  title: React.ReactNode;
  description?: React.ReactNode;
  /** Retry handler. Renders a retry button when present. */
  onRetry?: () => void;
  retryLabel?: string;
  action?: React.ReactNode;
  className?: string;
}

export function ErrorState({
  title,
  description,
  onRetry,
  retryLabel,
  action,
  className,
}: ErrorStateProps) {
  return (
    <div
      className={cn('border-t border-destructive px-0 py-8', className)}
      role="alert"
    >
      <div className="flex flex-col items-start gap-3">
        <div className="flex items-baseline gap-3">
          <span className="text-destructive" aria-hidden="true">
            <AlertTriangle className="size-4" />
          </span>
          <p className="m-0 text-[15px] font-semibold leading-6 text-foreground">{title}</p>
        </div>
        {description ? (
          <p className="m-0 max-w-md text-[14px] leading-5 text-muted-foreground">{description}</p>
        ) : null}
        <div className="flex items-center gap-2 pt-1">
          {onRetry && retryLabel ? (
            <Button type="button" variant="outline" size="sm" onClick={onRetry}>
              {retryLabel}
            </Button>
          ) : null}
          {action}
        </div>
      </div>
    </div>
  );
}

export interface LoadingStateProps {
  /** How many placeholder rows to draw. */
  rows?: number;
  /** Card placeholders instead of plain rows. */
  variant?: 'rows' | 'cards';
  className?: string;
}

/**
 * A placeholder that matches the shape of the content it replaces, so the
 * layout does not jump when the data arrives.
 */
export function LoadingState({
  rows = 3,
  variant = 'rows',
  className,
}: LoadingStateProps) {
  if (variant === 'cards') {
    return (
      <div
        className={cn('grid gap-4 sm:grid-cols-2 lg:grid-cols-3', className)}
        aria-hidden="true"
      >
        {Array.from({ length: rows }).map((_, index) => (
          <div
            key={index}
            className="overflow-hidden rounded-lg border bg-card shadow-sm"
          >
            <Skeleton className="aspect-video w-full rounded-none" />
            <div className="space-y-2 p-6">
              <Skeleton className="h-5 w-3/4" />
              <Skeleton className="h-4 w-1/2" />
              <Skeleton className="h-6 w-1/3" />
            </div>
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className={cn('space-y-3', className)} aria-hidden="true">
      {Array.from({ length: rows }).map((_, index) => (
        <Skeleton key={index} className="h-16 w-full" />
      ))}
    </div>
  );
}
