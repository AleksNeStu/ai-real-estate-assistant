'use client';

import { useTranslations } from 'next-intl';

import { MonoAnnotation } from '@/components/ui/mono-annotation';
import { cn } from '@/lib/utils';

/**
 * The tool list: the left rail of the console.
 *
 * One entry per tool - what it is called, what it calls itself, and whether
 * it can run at all. The name and the status are data, so they are mono;
 * the label is the reader's language, so it is not.
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

export function ToolRail({ tools, className }: { tools: ToolRailEntry[]; className?: string }) {
  const t = useTranslations('pages.tools');

  const statusLabel = (status?: ToolRailStatus) => {
    if (status === 'needsConfig') return t('console.needsConfig');
    if (status === 'needsAccount') return t('console.needsAccount');
    return t('console.ready');
  };

  return (
    <nav className={cn('flex flex-col gap-0.5', className)} aria-label={t('console.tools')}>
      {tools.map((tool) => (
        <a
          key={tool.id}
          href={`#${tool.id}`}
          className="flex items-baseline justify-between gap-2 rounded-md px-2.5 py-2 transition-colors hover:bg-muted"
        >
          <MonoAnnotation className="text-app text-foreground">{tool.name}</MonoAnnotation>
          <MonoAnnotation
            className="shrink-0 text-[10px]"
            tone={tool.status && tool.status !== 'ready' ? 'warning' : 'success'}
          >
            {statusLabel(tool.status)}
          </MonoAnnotation>
        </a>
      ))}
    </nav>
  );
}
