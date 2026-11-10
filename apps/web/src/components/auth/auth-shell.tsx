import type { ReactNode } from 'react';

import { cn } from '@/lib/utils';

/**
 * The shell of the six auth screens.
 *
 * The measure is 380px - the prototype's. A sign-in form is one column and
 * one action; a wider card reads as a page of options, and the auth routes
 * are not that.
 *
 * The rules the shell keeps, so the six pages cannot drift apart:
 *
 * - one card, flat, with a hairline border and no shadow (the design allows
 *   a shadow only on a popover or a dialog);
 * - the heading is the H1 of the route, and the one line under it says what
 *   the screen is for;
 * - the OAuth buttons sit ABOVE the divider, the divider separates them from
 *   the e-mail form - the other order tells the reader that the mail is the
 *   primary way in;
 * - a field carries its label and, on the right of the label, its hint;
 * - the primary action is the teal, and it is the only teal on the card.
 */

export function AuthCard({ className, children }: { className?: string; children: ReactNode }) {
  return (
    <div
      data-testid="auth-card"
      className={cn(
        'flex w-full max-w-[380px] flex-col gap-4 rounded-lg border border-border bg-card p-6',
        className
      )}
    >
      {children}
    </div>
  );
}

/** The heading block: the H1 of the route and the one line under it. */
export function AuthHeading({
  title,
  description,
}: {
  title: ReactNode;
  description?: ReactNode;
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <h1 className="text-2xl font-semibold tracking-tight text-foreground">{title}</h1>
      {description ? (
        <p className="text-sm leading-[21px] text-muted-foreground">{description}</p>
      ) : null}
    </div>
  );
}

/**
 * The field: the label, the hint on the right of the label, the control.
 *
 * The hint is not a second label - it is what the reader needs before
 * typing (the length, the forgot link), so it sits with the label and not
 * under the control.
 *
 * The hint is deliberately OUTSIDE the `<label>`: the label names the
 * control and nothing else, so the control's accessible name stays the
 * label alone.
 */
export function AuthField({
  label,
  htmlFor,
  hint,
  children,
}: {
  label: ReactNode;
  htmlFor?: string;
  hint?: ReactNode;
  children: ReactNode;
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex items-baseline justify-between gap-3">
        <label
          htmlFor={htmlFor}
          className="text-xs font-medium text-foreground"
        >
          {label}
        </label>
        {hint ? <span className="text-xs font-normal text-muted-foreground">{hint}</span> : null}
      </div>
      {children}
    </div>
  );
}

/** The divider: a hairline, a word, a hairline. */
export function AuthDivider({ label }: { label: ReactNode }) {
  return (
    <div className="flex items-center gap-2.5 text-xs text-muted-foreground">
      <span className="h-px flex-1 bg-border" aria-hidden="true" />
      <span>{label}</span>
      <span className="h-px flex-1 bg-border" aria-hidden="true" />
    </div>
  );
}

/**
 * The status line: a dot and a sentence.
 *
 * The dot carries the meaning, the sentence carries the detail. The tone is
 * the same three the design uses everywhere - green for done, amber for what
 * needs attention, red for what failed.
 */
export function AuthStatus({
  tone = 'neutral',
  children,
  className,
}: {
  tone?: 'neutral' | 'success' | 'warning' | 'destructive';
  children: ReactNode;
  className?: string;
}) {
  const dot: Record<string, string> = {
    neutral: 'bg-muted-foreground',
    success: 'bg-success',
    warning: 'bg-warning',
    destructive: 'bg-destructive',
  };

  return (
    <div
      role="status"
      className={cn(
        'flex items-center gap-2.5 rounded-lg border border-border p-3 text-sm text-foreground',
        className
      )}
    >
      <span
        data-testid="auth-status-dot"
        className={cn('size-2 shrink-0 rounded-full', dot[tone])}
        aria-hidden="true"
      />
      <span className="min-w-0">{children}</span>
    </div>
  );
}

/** The row of links under the form: sign in / create an account and the like. */
export function AuthLinks({ className, children }: { className?: string; children: ReactNode }) {
  return (
    <div className={cn('flex flex-wrap items-center justify-between gap-3 text-[13px]', className)}>
      {children}
    </div>
  );
}

/**
 * The note under the links.
 *
 * It says what an account is in this repository: part of the open source,
 * free on your own deployment. It is not a marketing line - it is the
 * answer to "what does an account cost me here".
 */
export function AuthNote({ className, children }: { className?: string; children: ReactNode }) {
  return (
    <p className={cn('text-xs leading-[18px] text-muted-foreground', className)}>{children}</p>
  );
}
