'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { useLocale, useTranslations } from 'next-intl';
import { Button } from '@/components/ui/button';
import { MonoAnnotation } from '@/components/ui/mono-annotation';
import { findComparables } from '@/lib/api';
import { formatPrice as formatPriceInLocale } from '@/lib/format';
import type { CMAComparable, Property } from '@/lib/types';

interface StepComparablesProps {
  subjectPropertyId: string | null;
  selectedComparables: CMAComparable[];
  onComparablesChange: (comparables: CMAComparable[]) => void;
}

export const MIN_COMPARABLES = 3;
export const MAX_COMPARABLES = 6;

/**
 * The comparables.
 *
 * A list of listings is a list, not a set of objects: the design draws it
 * as rows under a rule, the price and the score in mono on the right.
 */
export function StepComparables({
  subjectPropertyId,
  selectedComparables,
  onComparablesChange,
}: StepComparablesProps) {
  const t = useTranslations('cma.comparables');
  const tExtra = useTranslations('cma.comparablesExtra');
  const locale = useLocale();
  const [suggestedComparables, setSuggestedComparables] = useState<CMAComparable[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchComparables = useCallback(async () => {
    if (!subjectPropertyId) return;

    setIsLoading(true);
    setError(null);

    try {
      const results = await findComparables(subjectPropertyId, {
        max_results: 10,
        min_score: 40,
      });
      setSuggestedComparables(results);

      // Auto-select top 3 if nothing selected yet
      if (selectedComparables.length === 0 && results.length >= MIN_COMPARABLES) {
        const initialSelection = results.slice(0, MIN_COMPARABLES);
        onComparablesChange(initialSelection);
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : t('findFailed');
      setError(message);
    } finally {
      setIsLoading(false);
    }
  }, [subjectPropertyId, selectedComparables.length, onComparablesChange, t]);

  useEffect(() => {
    fetchComparables();
  }, [subjectPropertyId]); // eslint-disable-line react-hooks/exhaustive-deps

  const toggleComparable = (comparable: CMAComparable) => {
    const isSelected = selectedComparables.some((c) => c.property_id === comparable.property_id);

    if (isSelected) {
      onComparablesChange(
        selectedComparables.filter((c) => c.property_id !== comparable.property_id)
      );
    } else if (selectedComparables.length < MAX_COMPARABLES) {
      onComparablesChange([...selectedComparables, comparable]);
    }
  };

  const formatPrice = (price?: number, currency?: string) => {
    if (!price) return tExtra('notAvailable');
    // The wizard used to force every price into euros with German separators,
    // whatever the listing said and whatever language the reader picked.
    return formatPriceInLocale(price, currency || 'EUR', locale);
  };

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-baseline justify-between gap-3">
        <span className="text-[14px] font-semibold text-foreground">
          {t('selectRange', { min: MIN_COMPARABLES, max: MAX_COMPARABLES })}
        </span>
        <div className="flex items-center gap-3">
          <MonoAnnotation tone={selectedComparables.length < MIN_COMPARABLES ? 'warning' : 'neutral'}>
            {t('selected')} {selectedComparables.length} / {MAX_COMPARABLES}
          </MonoAnnotation>
          <Button variant="outline" size="sm" onClick={fetchComparables} disabled={isLoading}>
            {t('refresh')}
          </Button>
        </div>
      </div>

      {isLoading ? (
        <p className="text-[14px] text-muted-foreground" role="status">
          {t('finding')}
        </p>
      ) : null}

      {error ? (
        <p className="text-[14px] text-destructive" role="alert">
          {error}
        </p>
      ) : null}

      {!isLoading && !error && suggestedComparables.length === 0 ? (
        <p className="text-[14px] text-muted-foreground">{t('noComparables')}</p>
      ) : null}

      {suggestedComparables.length > 0 ? (
        <div className="flex flex-col">
          <div className="grid grid-cols-[28px_minmax(0,1fr)_auto_auto] items-baseline gap-x-4 border-b border-foreground py-2 text-[12px] text-muted-foreground">
            <span />
            <span>{t('columnAddress')}</span>
            <span className="text-right">{t('columnPrice')}</span>
            <span className="text-right">{t('similarity')}</span>
          </div>

          {suggestedComparables.map((comp) => {
            const isSelected = selectedComparables.some((c) => c.property_id === comp.property_id);
            const property = comp as unknown as Property;
            const atLimit = !isSelected && selectedComparables.length >= MAX_COMPARABLES;

            return (
              <label
                key={comp.property_id}
                className={[
                  'grid cursor-pointer grid-cols-[28px_minmax(0,1fr)_auto_auto] items-baseline gap-x-4 border-b border-border py-3',
                  atLimit ? 'opacity-40' : '',
                ]
                  .filter(Boolean)
                  .join(' ')}
              >
                <input
                  type="checkbox"
                  checked={isSelected}
                  onChange={() => toggleComparable(comp)}
                  disabled={atLimit}
                  aria-label={t('select', {
                    id: property.address || comp.property_id.slice(0, 8),
                  })}
                />
                <span className="min-w-0">
                  <span className="block truncate text-[15px] font-medium text-foreground">
                    {property.address || t('property', { id: comp.property_id.slice(0, 8) })}
                  </span>
                  <span className="mt-0.5 block truncate font-mono text-[12px] text-muted-foreground">
                    {property.area_sqm ? `${property.area_sqm} m²` : '-'}
                    {property.rooms ? ` · ${t('roomsCount', { count: property.rooms })}` : ''}
                  </span>
                </span>
                <span className="text-right font-mono text-[14px] text-foreground">
                  {formatPrice(comp.adjusted_price, comp.currency)}
                </span>
                <span className="text-right font-mono text-[12px] text-muted-foreground">
                  {comp.similarity_score.toFixed(0)}%
                </span>
              </label>
            );
          })}
        </div>
      ) : null}
    </div>
  );
}
