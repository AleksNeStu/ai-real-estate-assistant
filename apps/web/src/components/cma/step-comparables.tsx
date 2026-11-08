'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { useLocale, useTranslations } from 'next-intl';
import { Button } from '@/components/ui/button';
import { findComparables } from '@/lib/api';
import { formatPrice as formatPriceInLocale } from '@/lib/format';
import type { CMAComparable, Property } from '@/lib/types';

interface StepComparablesProps {
  subjectPropertyId: string | null;
  selectedComparables: CMAComparable[];
  onComparablesChange: (comparables: CMAComparable[]) => void;
  onNext: () => void;
  onPrev: () => void;
}

const MIN_COMPARABLES = 3;
const MAX_COMPARABLES = 6;

export function StepComparables({
  subjectPropertyId,
  selectedComparables,
  onComparablesChange,
  onNext,
  onPrev,
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

  const getScoreColor = (score: number): string => {
    if (score >= 80) return 'text-success';
    if (score >= 60) return 'text-warning';
    return 'text-warning';
  };

  const canProceed = selectedComparables.length >= MIN_COMPARABLES;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          {t('selectRange', { min: MIN_COMPARABLES, max: MAX_COMPARABLES })}
        </p>
        <Button variant="outline" size="sm" onClick={fetchComparables} disabled={isLoading}>
          {t('refresh')}
        </Button>
      </div>

      {/* Loading state */}
      {isLoading && (
        <div className="flex items-center justify-center py-8">
          <div
            className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"
            aria-hidden="true"
          ></div>
          <span className="ml-3 text-muted-foreground">{t('finding')}</span>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="text-sm text-destructive bg-destructive/10 px-3 py-2 rounded" role="alert">
          {error}
        </div>
      )}

      {/* Selected count */}
      <div className="flex items-center gap-4">
        <span className="text-sm">
          {t('selected')} <strong>{selectedComparables.length}</strong> / {MAX_COMPARABLES}
        </span>
        {selectedComparables.length < MIN_COMPARABLES && (
          <span className="text-xs text-warning">
            {t('selectMore', { count: MIN_COMPARABLES - selectedComparables.length })}
          </span>
        )}
      </div>

      {/* Comparables list */}
      {!isLoading && suggestedComparables.length > 0 && (
        <div className="space-y-2 max-h-[400px] overflow-y-auto">
          {suggestedComparables.map((comp) => {
            const isSelected = selectedComparables.some((c) => c.property_id === comp.property_id);
            const property = comp as unknown as Property;

            return (
              <div
                key={comp.property_id}
                className={`border rounded-lg p-3 cursor-pointer transition-colors ${
                  isSelected ? 'border-primary bg-primary/5' : 'hover:bg-muted/50'
                }`}
                onClick={() => toggleComparable(comp)}
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-start gap-3">
                    <input
                      type="checkbox"
                      checked={isSelected}
                      onChange={() => toggleComparable(comp)}
                      className="mt-1"
                      disabled={!isSelected && selectedComparables.length >= MAX_COMPARABLES}
                    />
                    <div>
                      <p className="font-medium text-sm">
                        {property.address || t('property', { id: comp.property_id.slice(0, 8) })}
                      </p>
                      <div className="flex gap-3 mt-1 text-xs text-muted-foreground">
                        <span>{formatPrice(comp.adjusted_price, comp.currency)}</span>
                        <span>{property.area_sqm ? `${property.area_sqm} m²` : '-'}</span>
                        <span>
                          {property.rooms ? t('roomsCount', { count: property.rooms }) : '-'}
                        </span>
                      </div>
                    </div>
                  </div>
                  <div className="text-right">
                    <span className={`text-sm font-medium ${getScoreColor(comp.similarity_score)}`}>
                      {comp.similarity_score.toFixed(0)}%
                    </span>
                    <p className="text-xs text-muted-foreground">{t('similarity')}</p>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Empty state */}
      {!isLoading && !error && suggestedComparables.length === 0 && (
        <div className="text-center py-8 text-muted-foreground">{t('noComparables')}</div>
      )}

      {/* Selected comparables summary */}
      {selectedComparables.length > 0 && (
        <div className="border-t pt-4">
          <h4 className="text-sm font-medium mb-2">{t('selectedComparables')}</h4>
          <div className="flex flex-wrap gap-2">
            {selectedComparables.map((comp, index) => (
              <span
                key={comp.property_id}
                className="bg-primary/10 text-primary text-xs px-2 py-1 rounded"
              >
                #{index + 1} {comp.property_id.slice(0, 8)} ({comp.similarity_score.toFixed(0)}%)
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Navigation */}
      <div className="flex justify-between pt-4">
        <Button variant="outline" onClick={onPrev}>
          {t('back')}
        </Button>
        <Button onClick={onNext} disabled={!canProceed}>
          {t('nextAdjustments')}
        </Button>
      </div>
    </div>
  );
}
