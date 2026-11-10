import type { ReactNode } from 'react';

import { cn } from '@/lib/utils';

/**
 * The two shapes every settings section is built from.
 *
 * A settings screen is a list of things a person can change, so the shape is
 * a ledger: one ink rule opens it and every row is one thing - a label that
 * says what it is, the value, and the control that changes it. A card is
 * reserved for the one thing that is an object: the avatar.
 */

/** A section of the settings screen: a heading, a rule and its rows. */
export function SettingsPanel({
  title,
  description,
  action,
  children,
  className,
}: {
  title: ReactNode;
  description?: ReactNode;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={cn('flex flex-col gap-3', className)}>
      <div className="flex flex-col gap-1 sm:flex-row sm:items-start sm:justify-between">
        <div className="space-y-1">
          <h2 className="text-h3 font-semibold tracking-tight text-foreground">{title}</h2>
          {description ? (
            <p className="max-w-2xl text-app text-muted-foreground">{description}</p>
          ) : null}
        </div>
        {action ? <div className="flex shrink-0 items-center gap-2">{action}</div> : null}
      </div>
      <div className="border-t border-foreground">{children}</div>
    </section>
  );
}

/**
 * One row of the ledger.
 *
 * On a wide screen the label sits in its own column and the value and the
 * control follow it; on a narrow one the row stacks and the label says what
 * the thing is above its value.
 */
export function SettingsRow({
  label,
  description,
  action,
  children,
  className,
}: {
  label: ReactNode;
  description?: ReactNode;
  action?: ReactNode;
  children?: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        'grid grid-cols-1 items-center gap-x-6 gap-y-2 border-b border-border py-3 md:grid-cols-[220px_minmax(0,1fr)_auto]',
        className
      )}
    >
      <div className="min-w-0">
        <span className="text-app font-medium text-foreground">{label}</span>
        {description ? (
          <p className="text-annot text-muted-foreground">{description}</p>
        ) : null}
      </div>
      <div className="min-w-0">{children}</div>
      {action ? <div className="flex items-center gap-3 md:justify-end">{action}</div> : null}
    </div>
  );
}
