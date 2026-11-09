'use client';

import React, { useState } from 'react';
import { useLocale, useTranslations } from 'next-intl';
import { Button } from '@/components/ui/button';
import { MonoAnnotation } from '@/components/ui/mono-annotation';
import { searchProperties } from '@/lib/api';
import { formatPrice as formatPriceInLocale } from '@/lib/format';
import type { Property } from '@/lib/types';

interface StepSubjectProps {
  subjectPropertyId: string | null;
  subjectProperty: Property | null;
  onPropertySelect: (property: Property) => void;
}

/**
 * The subject of the analysis.
 *
 * The design draws it as a mono ledger of facts under the address: price,
 * area, rooms, type. The numbers are the property's own - nothing here is
 * derived or rounded on the way to the screen.
 */
export function StepSubject({
  subjectProperty,
  onPropertySelect,
}: StepSubjectProps) {
  const t = useTranslations('cma.subject');
  const locale = useLocale();
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<Property[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);

  const handleSearch = async () => {
    if (!searchQuery.trim()) return;

    setIsSearching(true);
    setSearchError(null);

    try {
      const response = await searchProperties({
        query: searchQuery,
        limit: 10,
      });
      setSearchResults(response.results.map((r) => r.property));
    } catch (err) {
      const message = err instanceof Error ? err.message : t('searchFailed');
      setSearchError(message);
    } finally {
      setIsSearching(false);
    }
  };

  const formatPrice = (price?: number, currency?: string) => {
    if (!price) return 'N/A';
    // The wizard used to force every price into euros with German separators,
    // whatever the listing said and whatever language the reader picked.
    return formatPriceInLocale(price, currency || subjectProperty?.currency || 'EUR', locale);
  };

  const facts = subjectProperty
    ? [
        { label: t('price'), value: formatPrice(subjectProperty.price) },
        {
          label: t('area'),
          value: subjectProperty.area_sqm ? `${subjectProperty.area_sqm} m²` : 'N/A',
        },
        { label: t('rooms'), value: subjectProperty.rooms || 'N/A' },
        { label: t('type'), value: subjectProperty.property_type },
      ]
    : [];

  return (
    <div className="flex flex-col gap-5">
      <div className="flex gap-2">
        <input
          type="text"
          className="h-11 min-w-0 flex-1 rounded-lg border border-input bg-background px-3.5 text-[15px] text-foreground outline-none focus-visible:outline-2 focus-visible:outline-ring/50"
          placeholder={t('searchPlaceholder')}
          aria-label={t('searchAriaLabel')}
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
        />
        <Button onClick={handleSearch} disabled={isSearching} className="h-11 shrink-0">
          {isSearching ? t('searching') : t('searchButton')}
        </Button>
      </div>

      {searchError ? (
        <p className="text-[14px] text-destructive" role="alert">
          {searchError}
        </p>
      ) : null}

      {subjectProperty ? (
        <div className="rounded-lg border border-border p-4">
          <div className="flex items-baseline justify-between gap-3">
            <span className="text-[15px] font-semibold text-foreground">
              {subjectProperty.address || subjectProperty.city}
              {subjectProperty.district ? `, ${subjectProperty.district}` : ''}
            </span>
            <MonoAnnotation tone="success">{t('selected')}</MonoAnnotation>
          </div>

          <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-2 border-t border-foreground pt-2.5 sm:grid-cols-4">
            {facts.map((fact) => (
              <div key={fact.label} className="flex flex-col gap-0.5">
                <dt className="text-[12px] leading-4 text-muted-foreground">{fact.label}</dt>
                <dd className="font-mono text-[14px] leading-5 text-foreground">{fact.value}</dd>
              </div>
            ))}
          </dl>
        </div>
      ) : null}

      {searchResults.length > 0 ? (
        <div className="flex flex-col">
          <div className="flex items-baseline justify-between gap-3">
            <span className="text-[14px] font-semibold text-foreground">
              {t('searchResults', { count: searchResults.length })}
            </span>
            <MonoAnnotation>{t('searchResultsHint')}</MonoAnnotation>
          </div>

          <div className="mt-1 border-t border-foreground">
            {searchResults.map((property) => {
              const isSelected = subjectProperty?.id === property.id;
              return (
                <button
                  key={property.id}
                  type="button"
                  onClick={() => onPropertySelect(property)}
                  className="grid w-full grid-cols-[minmax(0,1fr)_auto] items-baseline gap-x-4 gap-y-1 border-b border-border py-3 text-left"
                >
                  <span className="min-w-0">
                    <span className="block truncate text-[15px] font-medium text-foreground">
                      {property.address || property.title || t('property')}
                    </span>
                    <span className="mt-0.5 block truncate text-[12px] text-muted-foreground">
                      {property.city}
                      {property.district ? `, ${property.district}` : ''}
                    </span>
                  </span>
                  <span className="flex flex-col items-end gap-0.5 text-right">
                    <span className="font-mono text-[14px] font-semibold text-foreground">
                      {formatPrice(property.price, property.currency)}
                    </span>
                    <span className="font-mono text-[12px] text-muted-foreground">
                      {property.area_sqm ? `${property.area_sqm} m²` : '-'}
                    </span>
                  </span>
                  {isSelected ? (
                    <span className="col-span-2 text-[12px] text-success">{t('selected')}</span>
                  ) : null}
                </button>
              );
            })}
          </div>
        </div>
      ) : null}
    </div>
  );
}
