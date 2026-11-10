import type { ReactNode } from 'react';

import { MonoAnnotation } from '@/components/ui/mono-annotation';
import { cn } from '@/lib/utils';

/**
 * The tool card: what the agent called, what it asked for, what came back.
 *
 * A card and not a ledger row, because a tool result is an object: it has
 * a name, a set of arguments, a result and its own sources. The chat draws
 * one of these per call, and the context pane links to them.
 */
export type ToolStatus = 'ok' | 'running' | 'error';

export type ToolConfidence = 'high' | 'medium' | 'low';

export interface ToolSource {
  /** What the source is called. */
  title: string;
  /** Where it came from: a catalogue, the web, an enrichment adapter. */
  kind?: string;
  /** How much the answer leans on it. */
  confidence?: ToolConfidence;
}

export interface ToolCardProps {
  /** The tool's own name, in mono: `search_properties`. */
  name: string;
  /** The human label of the call: `Search`. */
  label?: string;
  /** How long the call took: `0.21s`. */
  duration?: string;
  /** The arguments, as the tool received them. */
  args?: string;
  /** The result, rendered by the caller - the shape differs per tool. */
  result?: ReactNode;
  /** The one-line conclusion under the result. */
  verdict?: ReactNode;
  /** The intermediate steps the agent took to get there. */
  steps?: string[];
  /** The sources the answer leans on. */
  sources?: ToolSource[];
  /** Where the call stands. */
  status?: ToolStatus;
  /**
   * The word before the conclusion. A label, so it is the reader's
   * language: the card defaults to English and the caller passes its own.
   */
  resultLabel?: string;
  /** The name of the intermediate steps, before the count. */
  stepsLabel?: string;
  /** The name of the sources, before the count. */
  sourcesLabel?: string;
  className?: string;
}

const STATUS_DOT: Record<ToolStatus, string> = {
  ok: 'bg-success',
  running: 'bg-warning',
  error: 'bg-destructive',
};

const CONFIDENCE_CLASS: Record<ToolConfidence, string> = {
  high: 'border-success/30 text-success',
  medium: 'border-warning/30 text-warning',
  low: 'border-destructive/30 text-destructive',
};

export function ToolCard({
  name,
  label,
  duration,
  args,
  result,
  verdict,
  steps,
  sources,
  status = 'ok',
  resultLabel = 'Result',
  stepsLabel = 'Intermediate steps',
  sourcesLabel = 'Sources',
  className,
}: ToolCardProps) {
  const call = [label, duration].filter(Boolean).join(' · ');

  return (
    <div
      data-testid="tool-card"
      className={cn(
        'flex flex-col overflow-hidden rounded-lg border border-border bg-background',
        className
      )}
    >
      {/* The head: the tool's name, and what the call was called. */}
      <div className="flex items-center justify-between gap-3 border-b border-border px-3.5 py-2">
        <span className="flex items-center gap-2 font-mono text-annot font-medium text-foreground">
          <span
            className={cn('size-1.5 shrink-0 rounded-full', STATUS_DOT[status])}
            aria-hidden="true"
          />
          {name}
        </span>
        {call ? (
          <MonoAnnotation className="shrink-0 whitespace-nowrap">{call}</MonoAnnotation>
        ) : null}
      </div>

      {/* The arguments, as they were sent. */}
      {args ? (
        <MonoAnnotation className="block border-b border-border bg-muted px-3.5 py-2">
          <span className="text-foreground">args</span> {args}
        </MonoAnnotation>
      ) : null}

      {/* The result, the conclusion, the steps and the sources. */}
      <div className="flex flex-col gap-3 px-3.5 py-3.5">
        {result}

        {verdict ? (
          <p className="m-0 rounded-md bg-muted px-3 py-2 text-app text-foreground">
            <span className="font-semibold">{resultLabel}</span> · {verdict}
          </p>
        ) : null}

        {steps && steps.length > 0 ? (
          <details className="text-annot text-muted-foreground">
            <summary className="cursor-pointer">
              {stepsLabel} ({steps.length})
            </summary>
            <ol className="mt-1.5 list-decimal pl-4 font-mono leading-4">
              {steps.map((step) => (
                <li key={step}>{step}</li>
              ))}
            </ol>
          </details>
        ) : null}

        {sources && sources.length > 0 ? (
          <details className="rounded-md border border-border bg-muted px-3 py-2 text-annot text-foreground">
            <summary className="cursor-pointer font-medium">
              {sourcesLabel} ({sources.length})
            </summary>
            <ol className="mt-2 flex list-none flex-col pl-0">
              {sources.map((source, index) => (
                <li
                  key={`${source.title}-${index}`}
                  className="grid grid-cols-[24px_minmax(0,1fr)_auto] items-baseline gap-2 border-t border-border py-1.5"
                >
                  <span className="font-mono text-muted-foreground">[{index + 1}]</span>
                  <span>
                    <span className="font-medium">{source.title}</span>
                    {source.kind ? (
                      <span className="text-muted-foreground"> · {source.kind}</span>
                    ) : null}
                  </span>
                  {source.confidence ? (
                    <span
                      className={cn(
                        'rounded-sm border px-1.5 text-muted-foreground',
                        CONFIDENCE_CLASS[source.confidence]
                      )}
                    >
                      {source.confidence}
                    </span>
                  ) : null}
                </li>
              ))}
            </ol>
          </details>
        ) : null}
      </div>
    </div>
  );
}
