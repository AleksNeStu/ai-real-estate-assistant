'use client';

import { useTranslations } from 'next-intl';

import { MonoAnnotation } from '@/components/ui/mono-annotation';
import { cn } from '@/lib/utils';

/**
 * The context pane: the 420px column beside the conversation.
 *
 * It answers "what is the assistant working on right now" - the calls it
 * made, and the session they belong to. Every line of it is data: a tool
 * name, a count, a session id. The pane is a ledger, not a panel of cards.
 */

export interface ContextPaneTool {
  /** The id of the tool card in the conversation. */
  id: string;
  /** The tool's name, in mono. */
  name: string;
  /** What the call was called, in the reader's language. */
  label?: string;
}

export interface ContextPaneProps {
  /** The calls of the conversation, newest last. */
  tools: ContextPaneTool[];
  /** The session the conversation belongs to. */
  sessionId?: string;
  /** The request id of the last answer. */
  requestId?: string;
  className?: string;
}

export function ContextPane({ tools, sessionId, requestId, className }: ContextPaneProps) {
  const t = useTranslations('chat');

  return (
    <aside
      className={cn(
        'flex w-[420px] shrink-0 flex-col border-l border-border bg-background',
        className
      )}
      aria-label={t('context.toolsUsed')}
    >
      <div className="flex items-baseline justify-between gap-4 border-b border-border px-5 py-3.5">
        <span className="font-semibold text-app text-foreground">{t('context.toolsUsed')}</span>
        <MonoAnnotation>{t('context.calls', { count: tools.length })}</MonoAnnotation>
      </div>

      <div className="flex-1 overflow-auto px-3 py-2">
        {tools.length === 0 ? (
          <p className="px-2 py-1.5 text-annot text-muted-foreground">{t('context.empty')}</p>
        ) : (
          <ul className="flex list-none flex-col pl-0">
            {tools.map((tool) => (
              <li key={tool.id}>
                <a
                  href={`#${tool.id}`}
                  className="flex items-baseline justify-between gap-3 rounded-md px-2 py-1.5 transition-colors hover:bg-muted"
                >
                  {tool.label ? (
                    <span className="text-app text-foreground">{tool.label}</span>
                  ) : (
                    <span />
                  )}
                  <MonoAnnotation className="shrink-0">{tool.name}</MonoAnnotation>
                </a>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="flex flex-col gap-1 border-t border-border px-5 py-3.5">
        {sessionId ? (
          <MonoAnnotation className="truncate">
            {t('context.session', { id: sessionId })}
          </MonoAnnotation>
        ) : null}
        {requestId ? (
          <MonoAnnotation className="truncate">
            {t('context.request', { id: requestId })}
          </MonoAnnotation>
        ) : null}
      </div>
    </aside>
  );
}
