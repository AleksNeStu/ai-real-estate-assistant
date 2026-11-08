'use client';

import { Heart, ExternalLink, BedDouble, Maximize, MapPin } from 'lucide-react';
import { useTranslations } from 'next-intl';
import type { PropertyMapPoint } from './property-map-utils';

interface PropertyMapPopupProps {
  point: PropertyMapPoint;
  onViewDetails?: (id: string) => void;
  onToggleFavorite?: (id: string) => void;
  isFavorited?: boolean;
}

function formatPrice(price: number | undefined, priceOnRequest: string): string {
  if (price === undefined) return priceOnRequest;
  if (price >= 1000000) {
    return `$${(price / 1000000).toFixed(1)}M`;
  }
  return `$${price.toLocaleString()}`;
}

export function PropertyMapPopup({
  point,
  onViewDetails,
  onToggleFavorite,
  isFavorited = false,
}: PropertyMapPopupProps) {
  const t = useTranslations('property');
  const tSearch = useTranslations('search');
  const handleViewDetails = () => {
    onViewDetails?.(point.id);
  };

  const handleToggleFavorite = (e: React.MouseEvent) => {
    e.stopPropagation();
    onToggleFavorite?.(point.id);
  };

  return (
    <div
      className="min-w-[220px] max-w-[280px]"
      role="dialog"
      aria-label={point.title || t('details.title')}
    >
      {/* Image placeholder */}
      <div
        className="w-full h-24 bg-muted rounded-t-md flex items-center justify-center"
        aria-hidden="true"
      >
        <span className="text-xs text-muted-foreground">{t('card.imagePlaceholder')}</span>
      </div>

      {/* Content */}
      <div className="p-3 space-y-2">
        {/* Title */}
        <h4 className="font-semibold text-sm line-clamp-1">{point.title || t('card.untitled')}</h4>

        {/* Location */}
        <div className="flex items-center gap-1 text-xs text-muted-foreground">
          <MapPin className="h-3 w-3" />
          <span className="line-clamp-1">
            {[point.city, point.country].filter(Boolean).join(', ') ||
              t('card.locationUnavailable')}
          </span>
        </div>

        {/* Price */}
        <div className="text-lg font-bold text-primary">
          {formatPrice(point.price, t('card.priceOnRequest'))}
        </div>

        {/* Specs */}
        <div className="flex items-center gap-3 text-xs text-muted-foreground">
          {point.rooms !== undefined && (
            <div className="flex items-center gap-1">
              <BedDouble className="h-3 w-3" />
              <span>{t('card.beds', { count: point.rooms })}</span>
            </div>
          )}
          {point.area_sqm !== undefined && (
            <div className="flex items-center gap-1">
              <Maximize className="h-3 w-3" />
              <span>{point.area_sqm} m²</span>
            </div>
          )}
          {point.property_type && <span className="capitalize">{point.property_type}</span>}
        </div>

        {/* Price per sqm */}
        {point.price_per_sqm !== undefined && (
          <div className="text-xs text-muted-foreground">
            {formatPrice(point.price_per_sqm, t('card.priceOnRequest'))}/m²
          </div>
        )}

        {/* Actions */}
        <div className="flex items-center gap-2 pt-2 border-t">
          {onViewDetails && (
            <button type="button"
              onClick={handleViewDetails}
              className="flex-1 flex items-center justify-center gap-1 px-2 py-1.5 text-xs font-medium rounded-md bg-primary text-primary-foreground hover:bg-primary/90 transition-colors focus-visible:outline-none focus-visible:outline-2 focus-visible:outline-ring/50"
            >
              <ExternalLink className="h-3 w-3" />
              {t('card.viewDetails')}
            </button>
          )}
          {onToggleFavorite && (
            <button type="button"
              onClick={handleToggleFavorite}
              className={[
                'p-1.5 rounded-md border transition-colors',
                isFavorited ? 'bg-destructive/10 border-destructive/30 text-destructive' : 'hover:bg-muted',
              ].join(' ')}
              aria-label={
                isFavorited ? t('card.removeFromFavorites') : t('card.addToFavorites')
              }
            >
              <Heart className={['h-4 w-4', isFavorited ? 'fill-current' : ''].join(' ')} />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

// Export a function to generate HTML for Mapbox popup (since Mapbox uses HTML strings).
// The copy is passed in because this function is not a component and cannot call
// useTranslations itself.
export function generatePopupHTML(
  point: PropertyMapPoint,
  copy: { priceOnRequest: string; untitled: string; locationUnavailable: string; beds: string }
): string {
  const formatPrice = (price: number | undefined): string => {
    if (price === undefined) return copy.priceOnRequest;
    if (price >= 1000000) {
      return `$${(price / 1000000).toFixed(1)}M`;
    }
    return `$${price.toLocaleString()}`;
  };

  const specs = [
    point.rooms !== undefined ? `${point.rooms} ${copy.beds}` : null,
    point.area_sqm !== undefined ? `${point.area_sqm} m²` : null,
    point.property_type ? point.property_type : null,
  ]
    .filter(Boolean)
    .join(' • ');

  return `
    <div style="min-width:180px;max-width:240px;font-family:inherit;">
      <div style="padding:8px;">
        <div style="font-weight:600;font-size:14px;margin-bottom:4px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">
          ${point.title || copy.untitled}
        </div>
        <div style="font-size:12px;color:hsl(var(--muted-foreground));margin-bottom:4px;">
          ${[point.city, point.country].filter(Boolean).join(', ') || copy.locationUnavailable}
        </div>
        <div style="font-size:18px;font-weight:700;color:hsl(var(--chart-1));margin-bottom:4px;">
          ${formatPrice(point.price)}
        </div>
        ${specs ? `<div style="font-size:12px;color:hsl(var(--muted-foreground));margin-bottom:4px;">${specs}</div>` : ''}
        ${point.price_per_sqm !== undefined ? `<div style="font-size:11px;color:hsl(var(--muted-foreground));">${formatPrice(point.price_per_sqm)}/m²</div>` : ''}
      </div>
    </div>
  `;
}
