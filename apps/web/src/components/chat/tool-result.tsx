import type { ReactNode } from 'react';

import { cn } from '@/lib/utils';

/**
 * The shapes a tool's answer can take.
 *
 * The tool card carries the arguments and the frame; the answer itself is
 * shaped by the tool, so the caller renders it. These are the three shapes
 * the prototype uses - the key-value rows, the bar rows and the result
 * table - and the dispatcher that picks between them from the payload.
 *
 * Only the chat draws these, so they live here and not in `components/ui`:
 * the tools console shows its output as a ledger, which the ledger already
 * landed draws.
 */

export interface ToolResultRow {
  /** The field's name. Data, so it stays in mono. */
  label: string;
  /** The field's value. */
  value: ReactNode;
}

/** The key-value rows: a name over a number. */
export function ToolResultKv({ rows, className }: { rows: ToolResultRow[]; className?: string }) {
  return (
    <div className={cn('grid grid-cols-[repeat(auto-fill,minmax(150px,1fr))] gap-3', className)}>
      {rows.map((row) => (
        <div key={row.label} className="flex flex-col">
          <span className="font-mono text-annot text-muted-foreground">{row.label}</span>
          <span className="font-mono text-h3 font-semibold text-foreground">{row.value}</span>
        </div>
      ))}
    </div>
  );
}

/** The bar rows: a name, a bar and a number. */
export function ToolResultBars({
  rows,
  className,
}: {
  rows: { label: string; value: number; display?: string }[];
  className?: string;
}) {
  const widest = Math.max(...rows.map((row) => row.value), 0);

  return (
    <div className={cn('flex flex-col gap-2', className)}>
      {rows.map((row) => (
        <div
          key={row.label}
          className="grid grid-cols-[150px_minmax(0,1fr)_110px] items-center gap-3"
        >
          <span className="text-app text-foreground">{row.label}</span>
          <span className="h-1.5 overflow-hidden rounded-[1px] bg-muted">
            <span
              className="block h-full rounded-[1px] bg-foreground"
              style={{ width: `${widest > 0 ? (row.value / widest) * 100 : 0}%` }}
            />
          </span>
          <span className="text-right font-mono text-app font-medium text-foreground">
            {row.display ?? row.value}
          </span>
        </div>
      ))}
    </div>
  );
}

/** The result table: a head row and the rows under it. */
export function ToolResultTable({
  head,
  rows,
  className,
}: {
  head: string[];
  rows: ReactNode[][];
  className?: string;
}) {
  return (
    <div className={cn('flex flex-col text-app', className)}>
      <div
        className="grid gap-3 border-b border-foreground pb-1.5 text-annot text-muted-foreground"
        style={{ gridTemplateColumns: `repeat(${head.length}, minmax(0, 1fr))` }}
      >
        {head.map((cell) => (
          <span key={cell}>{cell}</span>
        ))}
      </div>
      {rows.map((row, index) => (
        <div
          key={index}
          className="grid gap-3 border-b border-border py-2"
          style={{ gridTemplateColumns: `repeat(${head.length}, minmax(0, 1fr))` }}
        >
          {row.map((cell, cellIndex) => (
            <span key={cellIndex} className={cellIndex === 0 ? undefined : 'font-mono'}>
              {cell}
            </span>
          ))}
        </div>
      ))}
    </div>
  );
}

/** The answer as plain text, when the tool answered in prose. */
export function ToolResultText({ text, className }: { text: string; className?: string }) {
  return (
    <p className={cn('m-0 whitespace-pre-wrap break-words text-app text-foreground', className)}>
      {text}
    </p>
  );
}

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

/**
 * The answer of a tool, drawn in the shape its payload asks for.
 *
 * A payload of numbers is a score sheet and gets the bars; a payload of
 * mixed values gets the key-value rows; a list of objects gets the table;
 * anything else is prose.
 */
export function ToolResult({ observation }: { observation?: string }) {
  if (!observation) return null;

  let payload: unknown;
  try {
    payload = JSON.parse(observation);
  } catch {
    return <ToolResultText text={observation} />;
  }

  if (Array.isArray(payload) && payload.length > 0 && payload.every(isPlainObject)) {
    const objects = payload as Record<string, unknown>[];
    const head = Array.from(new Set(objects.flatMap((object) => Object.keys(object))));
    const rows = objects.map((object) =>
      head.map((key) => {
        const value = object[key];
        return typeof value === 'object' && value !== null
          ? JSON.stringify(value)
          : String(value ?? '—');
      })
    );
    return <ToolResultTable head={head} rows={rows} />;
  }

  if (isPlainObject(payload)) {
    const entries = Object.entries(payload);
    if (entries.length > 0 && entries.every(([, value]) => value !== null && !isPlainObject(value) && !Array.isArray(value))) {
      const numeric = entries.every(([, value]) => typeof value === 'number');
      if (numeric) {
        return (
          <ToolResultBars
            rows={entries.map(([label, value]) => ({
              label,
              value: value as number,
            }))}
          />
        );
      }
      return (
        <ToolResultKv
          rows={entries.map(([label, value]) => ({
            label,
            value: typeof value === 'boolean' ? (value ? 'yes' : 'no') : String(value),
          }))}
        />
      );
    }
  }

  return <ToolResultText text={observation} />;
}
