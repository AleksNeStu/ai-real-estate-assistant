import * as React from 'react';
import { AlertTriangle, type LucideIcon } from 'lucide-react';

import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';

/**
 * The three states every data surface in the product can be in.
 *
 * Before this existed each route drew its own empty box and its own error
 * box, in a different radius, with a different icon and — in most cases —
 * with an English string hard-coded into the markup.
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
    <Card
      className={cn('border-dashed', className)}
      role="status"
      aria-live="polite"
    >
      <CardContent className="flex flex-col items-center gap-3 px-6 py-12 text-center">
        {Icon ? (
          <span
            className="flex size-10 items-center justify-center rounded-full bg-muted text-muted-foreground"
            aria-hidden="true"
          >
            <Icon className="size-5" />
          </span>
        ) : null}
        <div className="space-y-1">
          <p className="text-base font-semibold text-foreground">{title}</p>
          {description ? (
            <p className="max-w-md text-sm text-muted-foreground">{description}</p>
          ) : null}
        </div>
        {action ? <div className="pt-1">{action}</div> : null}
      </CardContent>
    </Card>
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
    <Card className={cn('border-destructive/40', className)} role="alert">
      <CardContent className="flex flex-col items-center gap-3 px-6 py-12 text-center">
        <span
          className="flex size-10 items-center justify-center rounded-full bg-destructive/10 text-destructive"
          aria-hidden="true"
        >
          <AlertTriangle className="size-5" />
        </span>
        <div className="space-y-1">
          <p className="text-base font-semibold text-foreground">{title}</p>
          {description ? (
            <p className="max-w-md text-sm text-muted-foreground">{description}</p>
          ) : null}
        </div>
        <div className="flex items-center gap-2 pt-1">
          {onRetry && retryLabel ? (
            <Button type="button" variant="outline" size="sm" onClick={onRetry}>
              {retryLabel}
            </Button>
          ) : null}
          {action}
        </div>
      </CardContent>
    </Card>
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
