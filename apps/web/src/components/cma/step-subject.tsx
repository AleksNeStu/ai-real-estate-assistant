'use client';

import React, { useState } from 'react';
import { useLocale, useTranslations } from 'next-intl';
import { Button } from '@/components/ui/button';
import { searchProperties } from '@/lib/api';
import { formatPrice as formatPriceInLocale } from '@/lib/format';
import type { Property } from '@/lib/types';

interface StepSubjectProps {
  subjectPropertyId: string | null;
  subjectProperty: Property | null;
  onPropertySelect: (property: Property) => void;
  onNext: () => void;
  canProceed: boolean;
}

export function StepSubject({
  subjectProperty,
  onPropertySelect,
  onNext,
  canProceed,
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

  return (
    <div className="space-y-6">
      {/* Search input */}
      <div className="flex gap-2">
        <input
          type="text"
          className="flex-1 border rounded-md px-3 py-2 text-sm"
          placeholder={t('searchPlaceholder')}
          aria-label={t('searchAriaLabel')}
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
        />
        <Button onClick={handleSearch} disabled={isSearching}>
          {isSearching ? t('searching') : t('searchButton')}
        </Button>
      </div>

      {/* Search error */}
      {searchError && (
        <div className="text-sm text-destructive bg-destructive/10 px-3 py-2 rounded" role="alert">
          {searchError}
        </div>
      )}

      {/* Selected property */}
      {subjectProperty && (
        <div className="border rounded-lg p-4 bg-primary/5">
          <div className="flex items-start justify-between">
            <div>
              <h3 className="font-medium">{t('selectedSubject')}</h3>
              <p className="text-sm text-muted-foreground mt-1">
                {subjectProperty.address || subjectProperty.city}
                {subjectProperty.district ? `, ${subjectProperty.district}` : ''}
              </p>
            </div>
            <span className="text-xs bg-primary/10 text-primary px-2 py-1 rounded">
              {t('selected')}
            </span>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4 text-sm">
            <div>
              <span className="text-muted-foreground">{t('price')}</span>
              <p className="font-medium">{formatPrice(subjectProperty.price)}</p>
            </div>
            <div>
              <span className="text-muted-foreground">{t('area')}</span>
              <p className="font-medium">
                {subjectProperty.area_sqm ? `${subjectProperty.area_sqm} m²` : 'N/A'}
              </p>
            </div>
            <div>
              <span className="text-muted-foreground">{t('rooms')}</span>
              <p className="font-medium">{subjectProperty.rooms || 'N/A'}</p>
            </div>
            <div>
              <span className="text-muted-foreground">{t('type')}</span>
              <p className="font-medium capitalize">{subjectProperty.property_type}</p>
            </div>
          </div>
        </div>
      )}

      {/* Search results */}
      {searchResults.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-sm font-medium text-muted-foreground">
            {t('searchResults', { count: searchResults.length })}
          </h4>
          <div className="max-h-[300px] overflow-y-auto space-y-2">
            {searchResults.map((property) => (
              <div
                key={property.id}
                className={`border rounded-lg p-3 cursor-pointer transition-colors hover:bg-muted/50 ${
                  subjectProperty?.id === property.id ? 'border-primary bg-primary/5' : ''
                }`}
                onClick={() => onPropertySelect(property)}
              >
                <div className="flex justify-between items-start">
                  <div>
                    <p className="font-medium text-sm">
                      {property.address || property.title || t('property')}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {property.city}
                      {property.district ? `, ${property.district}` : ''}
                    </p>
                  </div>
                  <span className="text-sm font-medium">{formatPrice(property.price)}</span>
                </div>
                <div className="flex gap-4 mt-2 text-xs text-muted-foreground">
                  <span>{property.area_sqm ? `${property.area_sqm} m²` : '-'}</span>
                  <span>{property.rooms ? t('roomsCount', { count: property.rooms }) : '-'}</span>
                  <span className="capitalize">{property.property_type}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Navigation */}
      <div className="flex justify-end pt-4">
        <Button onClick={onNext} disabled={!canProceed}>
          {t('nextComparables')}
        </Button>
      </div>
    </div>
  );
}
