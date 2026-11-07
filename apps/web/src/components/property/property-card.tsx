'use client';

import React, { useEffect, useRef } from 'react';
import { useTranslations } from 'next-intl';
import { HeartButton } from './heart-button';
import { MortgageEstimate } from './MortgageEstimate';
import { CommuteBadge } from '@/components/commute';
import { useLeadTracking } from '@/hooks/useLeadTracking';
import type { Property, CommuteTimeResult, CommuteMode } from '@/lib/types';

interface PropertyCardProps {
  property: Property;
  showFavoriteButton?: boolean;
  /** Optional: Commute time data to display on the card */
  commuteData?: CommuteTimeResult | null;
  /** Optional: Whether to show commute time on the card image */
  showCommuteBadge?: boolean;
  /** Optional: Whether to show the inline monthly payment estimate (v5.1). */
  showMortgageEstimate?: boolean;
}

export function PropertyCard({
  property,
  showFavoriteButton = true,
  commuteData,
  showCommuteBadge = false,
  showMortgageEstimate = true,
}: PropertyCardProps) {
  const t = useTranslations('property.card');
  const { trackPropertyView } = useLeadTracking();
  const cardRef = useRef<HTMLElement | null>(null);
  const stopTrackingRef = useRef<(() => void) | null>(null);

  // Lead tracking: a property view is only recorded once the card is actually
  // on screen, so a grid of results does not inflate the engagement score.
  // Tracking must never break the page, so every failure is swallowed.
  useEffect(() => {
    const propertyId = property.id;
    if (!propertyId) return;

    let observer: IntersectionObserver | null = null;

    const startTracking = () => {
      if (stopTrackingRef.current) return;
      try {
        const { stopTracking } = trackPropertyView(propertyId);
        stopTrackingRef.current = stopTracking;
      } catch {
        // Tracking is best-effort — never break rendering over it.
      }
    };

    if (typeof IntersectionObserver === 'undefined') {
      startTracking();
    } else {
      observer = new IntersectionObserver(
        (entries) => {
          if (entries.some((entry) => entry.isIntersecting)) {
            startTracking();
            observer?.disconnect();
          }
        },
        { threshold: 0.5 }
      );
      if (cardRef.current) {
        observer.observe(cardRef.current);
      } else {
        startTracking();
      }
    }

    return () => {
      observer?.disconnect();
      try {
        stopTrackingRef.current?.();
      } catch {
        // ignore — best-effort telemetry
      }
      stopTrackingRef.current = null;
    };
  }, [property.id, trackPropertyView]);

  return (
    <article
      ref={cardRef}
      data-testid="property-card"
      className="rounded-lg border bg-card text-card-foreground shadow-sm overflow-hidden"
      aria-label={property.title || t('untitled')}
    >
      <div className="aspect-video w-full bg-muted relative">
        {property.images?.[0] ? (
          <img
            src={property.images[0]}
            alt={property.title || t('untitled')}
            className="w-full h-full object-cover"
          />
        ) : (
          <div className="absolute inset-0 flex items-center justify-center text-muted-foreground">
            {t('imagePlaceholder')}
          </div>
        )}

        {showFavoriteButton && property.id && (
          <div className="absolute top-2 right-2">
            <HeartButton propertyId={property.id} />
          </div>
        )}

        {/* Commute time badge on the card */}
        {showCommuteBadge && commuteData && commuteData.duration_seconds > 0 && (
          <div className="absolute bottom-2 left-2">
            <CommuteBadge
              duration={commuteData.duration_seconds}
              mode={commuteData.mode as CommuteMode}
              className="bg-white/95 dark:bg-gray-900/90 backdrop-blur-sm"
            />
          </div>
        )}
      </div>

      <div className="p-6 space-y-2">
        <div className="flex items-start justify-between gap-2">
          <h3 className="text-2xl font-semibold leading-none tracking-tight">
            {property.title || t('untitled')}
          </h3>
          {showMortgageEstimate && property.price ? (
            <MortgageEstimate
              price={property.price}
              currency={property.currency || 'USD'}
              className="shrink-0"
            />
          ) : null}
        </div>
        <p className="text-sm text-muted-foreground">
          {property.city}
          {property.country ? `, ${property.country}` : ''}
        </p>
        <div className="font-bold text-lg">
          {property.price ? `$${property.price.toLocaleString()}` : t('priceOnRequest')}
        </div>
        <p className="text-sm text-muted-foreground">
          {[
            property.rooms ? t('beds', { count: property.rooms }) : null,
            property.bathrooms ? t('baths', { count: property.bathrooms }) : null,
            property.area_sqm ? `${property.area_sqm} ${t('areaUnit')}` : null,
          ]
            .filter(Boolean)
            .join(' \u2022 ')}
        </p>
      </div>
    </article>
  );
}
