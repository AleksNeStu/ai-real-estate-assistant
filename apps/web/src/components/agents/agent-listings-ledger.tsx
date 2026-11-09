'use client';

import { useLocale, useTranslations } from 'next-intl';

import { formatPrice, resolveLocale } from '@/lib/format';
import type { AgentListing } from '@/lib/types';

/**
 * The listings of an agent, as a ledger.
 *
 * The prototype draws them as rows: the picture on the left, the price in
 * mono, the listing and its street, the price per m² in mono, and the way
 * to book a viewing at the end of the row. A row is a listing, so the row
 * carries `data-testid="property-card"` - the handle means the same thing
 * it means on the search route: one rendered listing.
 *
 * The selected row is the one the contact form is about, so the page and
 * this ledger share the selection.
 */

export interface AgentListingsLedgerProps {
  listings: AgentListing[];
  /** The listing the contact form is about. */
  selectedPropertyId: string | null;
  /** Called when a row is picked. */
  onSelect: (propertyId: string) => void;
  /** Called when the reader asks for a viewing of a row. */
  onSchedule: (propertyId: string) => void;
  className?: string;
}

export function AgentListingsLedger({
  listings,
  selectedPropertyId,
  onSelect,
  onSchedule,
  className,
}: AgentListingsLedgerProps) {
  const t = useTranslations('agents');
  const tCard = useTranslations('property.card');
  const locale = useLocale();

  return (
    <div className={className}>
      {listings.map((listing) => {
        const property = listing.property;
        const selected = listing.property_id === selectedPropertyId;
        const currency = property?.currency || 'USD';
        const price = formatPrice(property?.price, currency, locale);
        const title = property?.title || tCard('untitled');
        const location =
          property?.address ||
          [property?.city, property?.country].filter(Boolean).join(', ') ||
          tCard('locationUnavailable');
        const perSqm =
          property?.price && property?.area_sqm
            ? Math.round(property.price / property.area_sqm).toLocaleString(
                resolveLocale(locale)
              )
            : null;

        return (
          <div
            key={listing.id}
            data-testid="property-card"
            role="article"
            aria-label={title}
            onClick={() => onSelect(listing.property_id)}
            className={[
              'grid cursor-pointer grid-cols-[72px_minmax(0,1fr)_auto] items-center gap-x-3 gap-y-2',
              'border-b border-border py-2.5 transition-colors',
              'md:grid-cols-[100px_minmax(0,1fr)_minmax(0,1.6fr)_96px_150px]',
              selected ? 'bg-muted' : 'hover:bg-muted/60',
            ].join(' ')}
          >
            <span
              aria-hidden="true"
              className="h-14 w-full overflow-hidden rounded-md border border-border bg-muted"
            >
              {property?.images?.[0] ? (
                <img
                  src={property.images[0]}
                  alt=""
                  loading="lazy"
                  className="size-full object-cover"
                />
              ) : null}
            </span>

            <span className="font-mono text-[15px] font-semibold text-foreground">
              {price || tCard('priceOnRequest')}
            </span>

            <span className="col-span-2 flex min-w-0 flex-col md:col-span-1">
              <span className="truncate text-[14px] font-medium text-foreground">{title}</span>
              <span className="truncate text-[12px] text-muted-foreground">{location}</span>
            </span>

            <span className="hidden font-mono text-[12px] text-muted-foreground md:block">
              {perSqm ? `${perSqm} ${currency}/m²` : '—'}
            </span>

            <span className="col-span-2 flex justify-end md:col-span-1">
              <button
                type="button"
                onClick={(event) => {
                  event.stopPropagation();
                  onSelect(listing.property_id);
                  onSchedule(listing.property_id);
                }}
                className="h-8 rounded-md border border-border px-3 text-[13px] font-medium text-foreground transition-colors hover:bg-muted"
              >
                {t('scheduleViewing')}
              </button>
            </span>
          </div>
        );
      })}
    </div>
  );
}
