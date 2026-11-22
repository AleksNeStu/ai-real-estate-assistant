'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useTranslations } from 'next-intl';
import { Check, Link2, Share2 } from 'lucide-react';

import { reportOutbound } from '@/lib/attribution';

/**
 * The link to this answer, and the way to send it to somebody.
 *
 * The valuation used to be a screen: the answer lived in the tab and died
 * with it. The link is what makes the answer a thing that can be shared —
 * and it is reported the way every outbound click on the site is reported,
 * so the funnel can answer where a shared answer went next.
 */
export interface ValuationShareProps {
  /** The absolute address of the answer. */
  url: string;
  /** The slot the outbound click is reported under. */
  slot?: string;
  /** The label of the link to the answer, when the page is not the answer. */
  openLabel?: string;
  className?: string;
}

export function ValuationShare({
  url,
  slot = 'valuation-share',
  openLabel,
  className,
}: ValuationShareProps) {
  const t = useTranslations('pages.valuation');
  const [copied, setCopied] = useState(false);

  /**
   * The click is reported before the browser does anything else, so the
   * request is not lost when the page changes.
   */
  async function report(): Promise<void> {
    await reportOutbound(url, slot);
  }

  async function copy(): Promise<void> {
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
    } catch {
      // A browser that refuses the clipboard keeps the link in view - it is
      // printed next to the button, so it can still be read and copied by
      // hand. The click is reported either way.
    }
    await report();
  }

  async function share(): Promise<void> {
    const canShare = typeof navigator !== 'undefined' && typeof navigator.share === 'function';
    if (!canShare) {
      await copy();
      return;
    }
    try {
      await navigator.share({ title: t('link.title'), url });
      await report();
    } catch {
      // The reader dismissed the sheet - that is not an error, and the
      // clipboard is still there.
      await copy();
    }
  }

  return (
    <div className={['flex flex-col gap-2', className].filter(Boolean).join(' ')} data-testid="valuation-share">
      <span className="text-[12px] font-medium text-foreground">{t('link.title')}</span>
      <p className="text-[12px] leading-5 text-muted-foreground">{t('link.hint')}</p>
      <code className="block overflow-x-auto rounded-md border border-border bg-muted/40 px-2.5 py-2 font-mono text-[12px] text-foreground">
        {url}
      </code>
      <div className="flex flex-wrap gap-2">
        {openLabel ? (
          <Link
            href={url}
            data-testid="valuation-share-open"
            className="inline-flex h-8 items-center rounded-md border border-border bg-background px-2.5 text-[13px] font-medium text-foreground transition-colors hover:bg-muted focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring/50"
          >
            {openLabel}
          </Link>
        ) : null}
        <button
          type="button"
          onClick={copy}
          data-testid="valuation-share-copy"
          className="inline-flex h-8 items-center gap-1.5 rounded-md border border-border bg-background px-2.5 text-[13px] font-medium text-foreground transition-colors hover:bg-muted focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring/50"
        >
          {copied ? (
            <Check className="size-4" aria-hidden />
          ) : (
            <Link2 className="size-4" aria-hidden />
          )}
          {copied ? t('share.copied') : t('share.copy')}
        </button>
        <button
          type="button"
          onClick={share}
          data-testid="valuation-share-share"
          className="inline-flex h-8 items-center gap-1.5 rounded-md border border-border bg-background px-2.5 text-[13px] font-medium text-foreground transition-colors hover:bg-muted focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring/50"
        >
          <Share2 className="size-4" aria-hidden />
          {t('share.share')}
        </button>
      </div>
    </div>
  );
}
