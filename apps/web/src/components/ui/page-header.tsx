import * as React from 'react';

import { cn } from '@/lib/utils';

/**
 * The one page title block in the product.
 *
 * Every route renders its heading through this component, so the H1 size,
 * the tracking, the gap to the description and the place of the primary
 * action are the same on all thirty routes. A route that needs a different
 * measure inherits it from here — it does not invent a new heading.
 */
export interface PageHeaderProps {
  /** The page title. Rendered as the single H1 of the route. */
  title: React.ReactNode;
  /** One line that says what the page is for. */
  description?: React.ReactNode;
  /** Primary and secondary actions, rendered right-aligned on wide screens. */
  actions?: React.ReactNode;
  /** Optional content under the description (filters, tabs, counters). */
  children?: React.ReactNode;
  className?: string;
}

export function PageHeader({
  title,
  description,
  actions,
  children,
  className,
}: PageHeaderProps) {
  return (
    <div
      className={cn(
        'flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between',
        className
      )}
    >
      <div className="space-y-1.5">
        <h1 className="text-3xl font-semibold tracking-tight text-foreground">{title}</h1>
        {description ? (
          <p className="max-w-2xl text-sm text-muted-foreground">{description}</p>
        ) : null}
        {children}
      </div>
      {actions ? (
        <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div>
      ) : null}
    </div>
  );
}

/**
 * The one section heading inside a page. Sits under a `PageHeader`.
 */
export interface SectionHeaderProps {
  title: React.ReactNode;
  description?: React.ReactNode;
  actions?: React.ReactNode;
  className?: string;
  /** Heading level. Defaults to H2 so the page keeps one H1. */
  as?: 'h2' | 'h3';
}

export function SectionHeader({
  title,
  description,
  actions,
  className,
  as: Heading = 'h2',
}: SectionHeaderProps) {
  return (
    <div
      className={cn(
        'flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between',
        className
      )}
    >
      <div className="space-y-1">
        <Heading className="text-xl font-semibold tracking-tight text-foreground">
          {title}
        </Heading>
        {description ? (
          <p className="text-sm text-muted-foreground">{description}</p>
        ) : null}
      </div>
      {actions ? (
        <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div>
      ) : null}
    </div>
  );
}
