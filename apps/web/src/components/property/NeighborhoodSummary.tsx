'use client';

import React, { useEffect, useState } from 'react';
import { Sparkles, Loader2 } from 'lucide-react';
import { neighborhoodSummaryApi } from '@/lib/api';

interface NeighborhoodSummaryProps {
  city?: string | null;
  neighborhood?: string | null;
  propertyType?: string | null;
  rooms?: number | null;
  area_sqm?: number | null;
  language?: string;
  maxSentences?: number;
  className?: string;
}

/**
 * 2-3 sentence AI summary of a neighborhood for a property detail page.
 *
 * Shows a skeleton while the LLM call is in flight. Falls back silently
 * to nothing if the call fails — the rest of the page still works.
 */
export function NeighborhoodSummary({
  city,
  neighborhood,
  propertyType,
  rooms,
  area_sqm,
  language = 'en',
  maxSentences = 3,
  className,
}: NeighborhoodSummaryProps) {
  const [summary, setSummary] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Skip if neither city nor neighborhood is provided
    if (!city && !neighborhood) {
      return;
    }
    let cancelled = false;
    // Prop-driven fetch is the natural pattern here; setting state directly
    // is intentional.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setLoading(true);
    setError(null);
    neighborhoodSummaryApi({
      city: city ?? undefined,
      neighborhood: neighborhood ?? undefined,
      property_type: propertyType ?? undefined,
      rooms: rooms ?? undefined,
      area_sqm: area_sqm ?? undefined,
      language,
      max_sentences: maxSentences,
    })
      .then((res: { summary: string }) => {
        if (cancelled) return;
        setSummary(res.summary);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        // Don't surface a noisy error to the user; just log it.
        const msg = err instanceof Error ? err.message : 'failed';
        console.warn('Neighborhood summary failed:', err);
        setError(msg);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
    // Re-fetch only when the inputs materially change.
  }, [city, neighborhood, propertyType, rooms, area_sqm, language, maxSentences]);

  if (!city && !neighborhood) return null;

  return (
    <section
      data-testid="neighborhood-summary"
      className={[
        'rounded-lg border bg-card text-card-foreground p-4',
        'flex items-start gap-3',
        className ?? '',
      ]
        .filter(Boolean)
        .join(' ')}
      aria-live="polite"
    >
      <Sparkles className="h-5 w-5 mt-0.5 text-violet-500 shrink-0" aria-hidden />
      <div className="flex-1 min-w-0">
        <div className="text-xs uppercase tracking-wide text-muted-foreground font-medium">
          {neighborhood ? `${neighborhood}, ` : ''}
          {city ?? ''}
        </div>
        {loading ? (
          <div
            data-testid="neighborhood-summary-loading"
            className="mt-2 space-y-2"
            aria-busy="true"
          >
            <div className="h-3 w-11/12 rounded bg-muted animate-pulse" />
            <div className="h-3 w-9/12 rounded bg-muted animate-pulse" />
            <div className="h-3 w-7/12 rounded bg-muted animate-pulse" />
            <span className="sr-only">Loading neighborhood summary</span>
          </div>
        ) : summary ? (
          <p className="mt-1 text-sm leading-relaxed text-foreground">
            {summary}
          </p>
        ) : error ? (
          <p className="mt-1 text-xs italic text-muted-foreground">
            Neighborhood summary unavailable right now.
          </p>
        ) : (
          <div className="mt-1 flex items-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="h-3 w-3 animate-spin" aria-hidden />
            <span>Preparing summary…</span>
          </div>
        )}
      </div>
    </section>
  );
}

export default NeighborhoodSummary;