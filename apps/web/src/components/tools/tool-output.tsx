'use client';

import type { ReactNode } from 'react';
import { useTranslations } from 'next-intl';

import { MonoAnnotation } from '@/components/ui/mono-annotation';
import { cn } from '@/lib/utils';

/**
 * The output panel of the console.
 *
 * The tool's own answer is rendered by the tool - the translated labels
 * live there - and the panel adds what a console owes its reader: the name
 * of the call, and the raw JSON behind it, one click away.
 */

export interface ToolOutputProps {
  /** The tool's name, in mono. Data, so it stays in mono. */
  name: string;
  /** The tool's answer, rendered by the tool. */
  children?: ReactNode;
  /** The raw answer, as the API returned it. */
  raw?: unknown;
  /** A mono note beside the name: the status, the duration. */
  meta?: string;
  className?: string;
}

export function ToolOutput({ name, children, raw, meta, className }: ToolOutputProps) {
  const t = useTranslations('pages.tools');
  const hasRaw = raw !== undefined && raw !== null;

  return (
    <div className={cn('flex flex-col gap-2', className)}>
      <div className="flex items-baseline justify-between gap-4">
        <MonoAnnotation>{name}</MonoAnnotation>
        {meta ? <MonoAnnotation>{meta}</MonoAnnotation> : null}
      </div>

      {children}

      {hasRaw ? (
        <details className="text-annot text-muted-foreground">
          <summary className="cursor-pointer">{t('console.rawJson')}</summary>
          <pre className="mt-2 overflow-x-auto whitespace-pre-wrap break-words rounded-md bg-muted p-3 font-mono text-annot leading-4 text-foreground">
            {JSON.stringify(raw, null, 2)}
          </pre>
        </details>
      ) : null}
    </div>
  );
}
