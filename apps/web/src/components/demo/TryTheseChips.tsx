'use client';

import Link from 'next/link';
import { Sparkles } from 'lucide-react';

interface TryTheseChipsProps {
  /** Locale-prefixed search path. Default: `/${locale}/search`. */
  searchHref?: string;
  /** Optional CSS class for the wrapping container. */
  className?: string;
  /** Heading shown above the chips. Default: English "Try one of these". */
  heading?: string;
}

const PROMPTS = [
  '2-bedroom apartment in Kraków under 500k',
  'Family house with garden, Warsaw',
  'Studio near city center, Wrocław',
  'Investment property, Gdańsk, ROI > 5%',
  'Compare mortgage options for 400k',
  'Pet-friendly rentals under 3000 PLN/mo',
];

/**
 * "Try one of these" example-query chips for first-time visitors.
 *
 * Clicking a chip navigates to the search page with `?q=<prompt>` so the
 * existing search bar can pick it up. Reusable on landing, /search empty
 * state, /chat prompt input, and /market-trends empty state.
 *
 * Localization gap (intentional, this session): English-only prompts.
 * Add to next-intl `common` namespace as `tryTheseChips.*` for i18n.
 */
export function TryTheseChips({
  searchHref,
  className,
  heading = 'Try one of these',
}: TryTheseChipsProps) {
  const base = searchHref ?? '/search';
  const hrefFor = (prompt: string) =>
    `${base}?q=${encodeURIComponent(prompt)}`;

  return (
    <div className={className}>
      <div className="flex items-center gap-2 text-xs uppercase tracking-wider text-muted-foreground mb-2">
        <Sparkles className="h-3 w-3" aria-hidden="true" />
        <span>{heading}</span>
      </div>
      <div className="flex flex-wrap gap-2">
        {PROMPTS.map((prompt) => (
          <Link
            key={prompt}
            href={hrefFor(prompt)}
            className="inline-flex items-center rounded-full border border-input bg-background/60 px-3 py-1.5 text-xs text-foreground hover:bg-accent hover:text-accent-foreground transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
          >
            {prompt}
          </Link>
        ))}
      </div>
    </div>
  );
}