'use client';

import React, { useEffect, useRef } from 'react';
import { useLocale, useTranslations } from 'next-intl';

import { HeartButton } from './heart-button';
import { MortgageEstimate } from './MortgageEstimate';
import { CommuteBadge } from '@/components/commute';
import { Card, CardContent } from '@/components/ui/card';
import { useLeadTracking } from '@/hooks/useLeadTracking';
import { formatPrice } from '@/lib/format';
import { cn } from '@/lib/utils';
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
  /** Optional: extra content under the card body (listing generator, rating). */
  footer?: React.ReactNode;
  className?: string;
}

/**
 * The one property card in the product.
 *
 * Search results, the favourites list and the city overview used to draw
 * their own card, each with its own price format, its own title size and
 * its own copy — the search card even ignored the property's currency and
 * never rendered the photo. This card is the single implementation all
 * three surfaces use.
 */
export function PropertyCard({
  property,
  showFavoriteButton = true,
  commuteData,
  showCommuteBadge = false,
  showMortgageEstimate = true,
  footer,
  className,
}: PropertyCardProps) {
  const t = useTranslations('property.card');
  const locale = useLocale();
  const { trackPropertyView } = useLeadTracking();
  const cardRef = useRef<HTMLDivElement | null>(null);
  const stopTrackingRef = useRef<(() => void) | null>(null);

  const title = property.title || t('untitled');
  const price = formatPrice(property.price, property.currency || 'USD', locale);

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
    <Card
      ref={cardRef}
      data-testid="property-card"
      role="article"
      aria-label={title}
      className={cn('group flex flex-col overflow-hidden', className)}
    >
      <div className="aspect-video w-full bg-muted relative">
        {property.images?.[0] ? (
          <img
            src={property.images[0]}
            alt={title}
            className="size-full object-cover"
            loading="lazy"
          />
        ) : (
          <div className="absolute inset-0 flex items-center justify-center text-sm text-muted-foreground">
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
              className="bg-background/95 backdrop-blur-sm"
            />
          </div>
        )}
      </div>

      <CardContent className="flex flex-1 flex-col gap-2 p-6">
        <div className="flex items-start justify-between gap-3">
          <h3 className="font-sans text-lg font-semibold leading-snug tracking-tight line-clamp-2">
            {title}
          </h3>
          {showMortgageEstimate && property.price ? (
            <MortgageEstimate
              price={property.price}
              currency={property.currency || 'USD'}
              locale={locale}
              className="shrink-0"
            />
          ) : null}
        </div>

        <p className="text-sm text-muted-foreground">
          {property.address ||
            [property.city, property.country].filter(Boolean).join(', ')}
        </p>

        <p className="font-mono text-lg font-semibold tabular-nums tracking-tight">
          {price || t('priceOnRequest')}
        </p>

        <p className="text-sm text-muted-foreground">
          {[
            property.rooms ? t('beds', { count: property.rooms }) : null,
            property.bathrooms ? t('baths', { count: property.bathrooms }) : null,
            property.area_sqm ? `${property.area_sqm} ${t('areaUnit')}` : null,
          ]
            .filter(Boolean)
            .join(' • ')}
        </p>

        {footer ? <div className="mt-auto space-y-1 pt-2">{footer}</div> : null}
      </CardContent>
    </Card>
  );
}

export default PropertyCard;
