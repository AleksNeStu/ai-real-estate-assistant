'use client';

import Link from 'next/link';
import { useLocale, useTranslations } from 'next-intl';

import { HeartButton, ListingGenerator } from '@/components/property';
import { RelevanceRating } from '@/components/search/relevance-rating';
import { EmptyState } from '@/components/ui/states';
import { formatPrice, resolveLocale } from '@/lib/format';
import { formatMonthlyPayment } from '@/lib/mortgage';
import type { SearchResultItem } from '@/lib/types';

/**
 * The results as a ledger of prices.
 *
 * A list of listings is a list, not a set of objects: the design draws it as
 * rows under a rule, the price in mono on the right and the listing on the
 * left. The card that used to draw them is still the card of the drawer, the
 * map popup and the listing generator - this row is the list.
 *
 * Every row keeps `data-testid="property-card"`: the end-to-end suite counts
 * the listings through it, and the meaning of the handle - "one rendered
 * listing" - did not change.
 */

export interface ResultsLedgerProps {
  results: SearchResultItem[];
  /** The sentence the results answered. */
  query: string;
  className?: string;
}

export function ResultsLedger({ results, query, className }: ResultsLedgerProps) {
  const t = useTranslations('property.card');
  const tSearch = useTranslations('search');
  const tLanding = useTranslations('landing.hero');
  const locale = useLocale();

  // A list that knows how to say it is empty. The route hands the whole
  // result set over, so the case of nothing to show is handled here.
  if (results.length === 0) {
    return (
      <div className={className}>
        <EmptyState
          title={tSearch('results.noResults')}
          description={tSearch('results.noResultsHint')}
        />
      </div>
    );
  }

  return (
    <div className={className}>
      {results.map((item, index) => {
        const property = item.property;
        const currency = property.currency || 'USD';
        const price = formatPrice(property.price, currency, locale);
        const title = property.title || t('untitled');
        const location =
          property.address ||
          [property.city, property.country].filter(Boolean).join(', ') ||
          t('locationUnavailable');

        const facts = [
          property.rooms ? t('beds', { count: property.rooms }) : null,
          property.area_sqm ? `${property.area_sqm} ${t('areaUnit')}` : null,
        ].filter(Boolean);

        const perSqm =
          property.price && property.area_sqm
            ? tLanding('instrumentPerSqm', {
                amount: Math.round(property.price / property.area_sqm).toLocaleString(
                  resolveLocale(locale)
                ),
                currency,
              })
            : null;

        // A rented flat is priced per month already; a sold one is priced
        // once, and the estimate says what that price costs per month.
        const isRent = property.listing_type === 'rent';
        const monthly =
          !isRent && property.price
            ? formatMonthlyPayment(property.price, {
                currency,
                locale: resolveLocale(locale),
                interestRate: 6.5,
                downPaymentPercent: 20,
                loanYears: 30,
              })
            : null;
        const monthlyLabel = monthly
          ? tLanding('instrumentPerMonth', {
              amount: formatPrice(Math.round(monthly.raw), currency, locale),
            })
          : null;

        return (
          <article
            key={`${property.id ?? 'unknown'}-${index}`}
            data-testid="property-card"
            role="article"
            aria-label={title}
            className="grid grid-cols-[minmax(0,1fr)_auto] items-baseline gap-x-4 gap-y-2 border-b border-border px-6 py-4"
          >
            <div className="min-w-0">
              {property.id ? (
                <Link
                  href={`/${locale}/property/${property.id}`}
                  className="block truncate text-[15px] font-medium leading-5 text-foreground underline-offset-4 hover:underline"
                >
                  {title}
                </Link>
              ) : (
                <p className="truncate text-[15px] font-medium leading-5 text-foreground">
                  {title}
                </p>
              )}
              <p className="mt-1 truncate text-[12px] leading-4 text-muted-foreground">
                {location}
              </p>
              {facts.length ? (
                <p className="mt-1 text-[12px] leading-4 text-muted-foreground">
                  {facts.join(' • ')}
                </p>
              ) : null}
            </div>

            <div className="flex flex-col items-end gap-1 text-right">
              <span className="font-mono text-[16px] font-semibold leading-5 text-foreground">
                {price || t('priceOnRequest')}
              </span>
              {monthlyLabel ? (
                <span className="font-mono text-[12px] leading-4 text-success">{monthlyLabel}</span>
              ) : null}
              {perSqm ? (
                <span className="font-mono text-[12px] leading-4 text-muted-foreground">
                  {perSqm}
                </span>
              ) : null}
            </div>

            {property.id ? (
              <div className="col-span-2 mt-1 flex items-center gap-2">
                <HeartButton propertyId={property.id} size="sm" />
                <ListingGenerator propertyId={property.id} compact />
                <RelevanceRating query={query} propertyId={property.id} />
              </div>
            ) : null}
          </article>
        );
      })}
    </div>
  );
}
