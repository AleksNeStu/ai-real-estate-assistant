'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useTranslations } from 'next-intl';

import { MonoAnnotation } from '@/components/ui/mono-annotation';

/**
 * The showcase body.
 *
 * The page it belongs to is the public face of the work, so it is written in
 * the same measure as the prototype: a 1040px page, a 280px column that
 * names the section and counts its entries, and the section itself on the
 * right. Every section opens with a 1px ink rule - the ledger rule - because
 * a section here is a row of a catalogue, not a card.
 *
 * The empty state is a dashed outline, not a panel: the section is waiting
 * for an entry, and the format below it says what an entry looks like. The
 * checkbox toggles that format for all three sections at once, because the
 * format is one format.
 */

const SECTION_FIELDS = {
  forks: [
    ['fieldProject', 'fieldProjectHint'],
    ['fieldWhatItDoes', 'fieldWhatItDoesHint'],
    ['fieldChanged', 'fieldChangedHint'],
  ],
  companies: [
    ['fieldOrganisation', 'fieldOrganisationHint'],
    ['fieldDeployment', 'fieldDeploymentHint'],
    ['fieldSince', 'fieldSinceHint'],
  ],
  quotes: [
    ['fieldQuote', 'fieldQuoteHint'],
    ['fieldPerson', 'fieldPersonHint'],
    ['fieldLink', 'fieldLinkHint'],
  ],
} as const;

const SECTIONS = [
  {
    id: 'forks',
    titleKey: 'forksTitle',
    emptyKey: 'forksEmpty',
    helperKey: 'forksEmptyHelper',
  },
  {
    id: 'companies',
    titleKey: 'companiesTitle',
    emptyKey: 'companiesEmpty',
    helperKey: 'companiesEmptyHelper',
  },
  {
    id: 'quotes',
    titleKey: 'quotesTitle',
    emptyKey: 'quotesEmpty',
    helperKey: 'quotesEmptyHelper',
  },
] as const;

export interface ShowcaseBodyProps {
  locale: string;
}

export function ShowcaseBody({ locale }: ShowcaseBodyProps) {
  const t = useTranslations('showcase');
  const [showFormat, setShowFormat] = useState(false);

  return (
    <div className="mx-auto flex w-full max-w-[1040px] flex-col gap-8 px-6 pb-24 pt-8">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div className="flex flex-col gap-1.5">
          <h1 className="text-3xl font-semibold tracking-tight text-foreground">
            {t('heroTitle')}
          </h1>
          <p className="text-sm text-muted-foreground">{t('heroSubtitle')}</p>
        </div>
        <label className="flex cursor-pointer items-center gap-2 text-[13px] text-muted-foreground">
          <input
            type="checkbox"
            checked={showFormat}
            onChange={(event) => setShowFormat(event.target.checked)}
            className="size-3.5 accent-action"
            aria-label={t('showFormat')}
          />
          {t('showFormat')}
        </label>
      </div>

      {SECTIONS.map((section) => (
        <section
          key={section.id}
          className="grid gap-8 border-t border-foreground pt-4 sm:grid-cols-[280px_minmax(0,1fr)]"
        >
          <div className="flex flex-col gap-1">
            <h2 className="text-[17px] font-semibold text-foreground">{t(section.titleKey)}</h2>
            <MonoAnnotation>{t('entries', { count: 0 })}</MonoAnnotation>
          </div>

          <div className="flex flex-col gap-3">
            <div className="flex flex-col gap-1.5 rounded-lg border border-dashed border-border p-5">
              <span className="font-medium text-foreground">{t(section.emptyKey)}</span>
              <span className="text-[14px] leading-5 text-muted-foreground">
                {t(section.helperKey)}
              </span>
            </div>

            {showFormat ? (
              <div className="grid gap-px overflow-hidden rounded-lg border border-border bg-border sm:grid-cols-3">
                {SECTION_FIELDS[section.id].map(([key, hint]) => (
                  <div
                    key={key}
                    className="flex flex-col gap-0.5 bg-background px-3 py-2.5"
                  >
                    <span className="font-mono text-[12px] font-medium text-foreground">
                      {t(key)}
                    </span>
                    <span className="text-[12px] leading-4 text-muted-foreground">
                      {t(hint)}
                    </span>
                  </div>
                ))}
              </div>
            ) : null}
          </div>
        </section>
      ))}

      <div className="flex flex-col gap-4 rounded-lg border border-border p-5 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-col gap-1">
          <span className="font-semibold text-foreground">{t('ctaTitle')}</span>
          <span className="text-[14px] leading-5 text-muted-foreground">{t('ctaSubtitle')}</span>
        </div>
        <div className="flex shrink-0 flex-wrap items-center gap-2">
          <Link
            href={`/${locale}/search`}
            className="inline-flex h-[38px] items-center rounded-md bg-action px-4 text-[14px] font-medium text-action-foreground hover:opacity-90"
          >
            {t('ctaTryDemo')}
          </Link>
          <a
            href="https://github.com/AleksNeStu/ai-real-estate-assistant?utm_source=realty.kittray.com&utm_medium=app&utm_campaign=oss&utm_content=showcase_star"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex h-[38px] items-center rounded-md border border-border px-4 text-[14px] font-medium text-foreground hover:bg-muted"
          >
            {t('ctaStar')}
          </a>
        </div>
      </div>
    </div>
  );
}
