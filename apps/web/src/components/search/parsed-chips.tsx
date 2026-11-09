'use client';

import { useTranslations } from 'next-intl';

import { MonoAnnotation } from '@/components/ui/mono-annotation';

/**
 * The chips of the parsed sentence.
 *
 * The sentence is read into filters, and the filters are shown as they are:
 * mono, small, one chip per filter. The landing's instrument already renders
 * them this way, so the search route borrows its idiom instead of inventing
 * a second one - the label, the chip and the note are the same three pieces.
 */

export interface ParsedChipsProps {
  /** One chip per filter the sentence produced. */
  chips: string[];
  /** The note beside the chips. */
  note?: string;
  /** How many listings the sentence found - the count the landing's row carries. */
  count?: number;
  className?: string;
}

export function ParsedChips({ chips, note, count, className }: ParsedChipsProps) {
  const t = useTranslations('landing.hero');
  const tSearch = useTranslations('search');

  return (
    <div className={['flex flex-wrap items-center gap-1.5 text-[12px]', className].join(' ')}>
      <MonoAnnotation className="mr-0.5">{t('instrumentParsed')}</MonoAnnotation>

      {chips.length === 0 ? (
        <span className="text-muted-foreground">{tSearch('parsed.empty')}</span>
      ) : (
        chips.map((chip) => (
          <span key={chip} className="rounded-sm bg-muted px-[7px] py-px">
            {chip}
          </span>
        ))
      )}

      {note ? <span className="ml-1 text-muted-foreground">{note}</span> : null}

      {typeof count === 'number' && count > 0 ? (
        <span className="ml-auto font-mono text-muted-foreground">{t('matches', { count })}</span>
      ) : null}
    </div>
  );
}
