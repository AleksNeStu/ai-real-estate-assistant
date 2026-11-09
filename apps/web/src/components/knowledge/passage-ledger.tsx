'use client';

import { useTranslations } from 'next-intl';

import { MonoAnnotation } from '@/components/ui/mono-annotation';
import type { EnhancedCitation } from '@/lib/types';

/**
 * The passages the answer was built from.
 *
 * The design draws them as a ledger: a numbered row per passage, the
 * document and the place in it on the left, the passage itself under that,
 * and the confidence of the match on the right in mono.
 *
 * Every field comes from the citation the API returned: the document it
 * names, the page or paragraph it points at, the excerpt it carries and the
 * confidence the citation service scored it with. Nothing is read out of the
 * answer text.
 */

/** Where in the document a passage sits: a page, a paragraph, a chunk. */
function locationOf(citation: EnhancedCitation): string | null {
  if (typeof citation.page_number === 'number') return `p. ${citation.page_number}`;
  if (typeof citation.paragraph_number === 'number') return `¶ ${citation.paragraph_number}`;
  if (typeof citation.chunk_index === 'number') return `chunk ${citation.chunk_index}`;
  return null;
}

export interface PassageLedgerProps {
  citations: EnhancedCitation[];
  /** How many passages the question asked for. */
  topK: number;
  className?: string;
}

export function PassageLedger({ citations, topK, className }: PassageLedgerProps) {
  const t = useTranslations('pages.knowledge');

  return (
    <section className={className} data-testid="knowledge-passages">
      <div className="flex items-baseline justify-between gap-3 border-b border-border px-3.5 py-2">
        <span className="text-[12px] text-muted-foreground">{t('ask.passages')}</span>
        <MonoAnnotation>
          {t('ask.passageCount', { shown: citations.length, total: topK })}
        </MonoAnnotation>
      </div>

      <div className="border-t border-border">
        {citations.map((citation, index) => {
          const location = locationOf(citation);
          const source = citation.source ?? citation.source_title ?? t('ask.unknownSource');
          const score =
            typeof citation.confidence_score === 'number'
              ? citation.confidence_score.toFixed(2)
              : '—';

          return (
            <div
              key={`${citation.citation_hash ?? source}-${index}`}
              className="grid grid-cols-[28px_minmax(0,1fr)_60px] items-start gap-x-3 gap-y-1 border-b border-border px-3.5 py-2.5"
            >
              <span className="font-mono text-[12px] leading-5 text-muted-foreground">
                [{index + 1}]
              </span>
              <span className="flex min-w-0 flex-col gap-1">
                <span className="truncate text-[13px] font-medium leading-5 text-foreground">
                  {source}
                  {location ? ` · ${location}` : ''}
                </span>
                {citation.content_snippet ? (
                  <span className="text-[13px] leading-5 text-muted-foreground">
                    “{citation.content_snippet}”
                  </span>
                ) : null}
              </span>
              <span className="text-right font-mono text-[12px] leading-5 text-foreground">
                {score}
              </span>
            </div>
          );
        })}
      </div>
    </section>
  );
}
