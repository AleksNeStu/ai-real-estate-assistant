'use client';

import Link from 'next/link';
import { Sparkles } from 'lucide-react';
import { useTranslations } from 'next-intl';

interface TryTheseChipsProps {
  /** Locale-prefixed search path. Default: `/${locale}/search`. */
  searchHref?: string;
  /** Optional CSS class for the wrapping container. */
  className?: string;
  /**
   * Heading shown above the chips. If omitted, uses the next-intl
   * translation `common.tryTheseChips.heading`; if the locale doesn't
   * have the key (en, ru, de, es, it, pt, tr, uk still pending), falls
   * back to English "Try one of these".
   */
  heading?: string;
}

// The example queries are translated, so the chip sends the search a
// question in the language the visitor is reading.
const PROMPT_KEYS = ['p1', 'p2', 'p3', 'p4', 'p5', 'p6'] as const;

/**
 * "Try one of these" example-query chips for first-time visitors.
 *
 * Clicking a chip navigates to the search page with `?q=<prompt>` so the
 * existing search bar can pick it up. Reusable on landing, /search empty
 * state, /chat prompt input, and /market-trends empty state.
 *
 * The example queries come from the `common.tryTheseChips` namespace.
 */
export function TryTheseChips({
  searchHref,
  className,
  heading,
}: TryTheseChipsProps) {
  const t = useTranslations('common');
  const resolvedHeading = heading ?? t('tryTheseChips.heading');
  const base = searchHref ?? '/search';
  const hrefFor = (prompt: string) =>
    `${base}?q=${encodeURIComponent(prompt)}`;

  return (
    <div className={className}>
      <div className="flex items-center gap-2 text-xs uppercase tracking-wider text-muted-foreground mb-2">
        <Sparkles className="h-3 w-3" aria-hidden="true" />
        <span>{resolvedHeading}</span>
      </div>
      <div className="flex flex-wrap gap-2">
        {PROMPT_KEYS.map((key) => (
          <Link
            key={key}
            href={hrefFor(t(`tryTheseChips.${key}`))}
            className="inline-flex items-center rounded-full border border-input bg-background/60 px-3 py-1.5 text-xs text-foreground hover:bg-accent hover:text-accent-foreground transition-colors focus-visible:outline-none focus-visible:outline-2 focus-visible:outline-ring/50"
          >
            {t(`tryTheseChips.${key}`)}
          </Link>
        ))}
      </div>
    </div>
  );
}
