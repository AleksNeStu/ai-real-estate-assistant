'use client';

import { useTranslations } from 'next-intl';

import { MonoAnnotation } from '@/components/ui/mono-annotation';
import { cn } from '@/lib/utils';

/**
 * The tool list: the left rail of the console.
 *
 * One entry per tool - what it calls itself, and whether it can run at all.
 * The name and the status are data, so they are mono. The console shows
 * one tool at a time, so an entry is a button: it picks the tool.
 */

export type ToolRailStatus = 'ready' | 'needsConfig' | 'needsAccount';

export interface ToolRailEntry {
  /** The id of the tool's section on the page. */
  id: string;
  /** The tool's own name, in mono. */
  name: string;
  /** Whether it can run as it stands. */
  status?: ToolRailStatus;
}

export interface ToolRailProps {
  tools: ToolRailEntry[];
  /** The tool the console is showing. */
  selected: string;
  /** Picks a tool. */
  onSelect: (id: string) => void;
  className?: string;
}

export function ToolRail({ tools, selected, onSelect, className }: ToolRailProps) {
  const t = useTranslations('pages.tools');

  const statusLabel = (status?: ToolRailStatus) => {
    if (status === 'needsConfig') return t('console.needsConfig');
    if (status === 'needsAccount') return t('console.needsAccount');
    return t('console.ready');
  };

  return (
    <nav className={cn('flex flex-col gap-0.5', className)} aria-label={t('console.tools')}>
      {tools.map((tool) => {
        const isSelected = tool.id === selected;
        return (
          <button
            key={tool.id}
            type="button"
            data-testid={`tool-${tool.name}`}
            aria-pressed={isSelected}
            onClick={() => onSelect(tool.id)}
            className={cn(
              'flex items-baseline justify-between gap-2 rounded-md px-2.5 py-2 text-left transition-colors',
              isSelected ? 'bg-muted' : 'hover:bg-muted/60'
            )}
          >
            <MonoAnnotation className="text-app text-foreground">{tool.name}</MonoAnnotation>
            <MonoAnnotation
              className="shrink-0 text-[10px]"
              tone={tool.status && tool.status !== 'ready' ? 'warning' : 'success'}
            >
              {statusLabel(tool.status)}
            </MonoAnnotation>
          </button>
        );
      })}
    </nav>
  );
}
