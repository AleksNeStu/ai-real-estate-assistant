'use client';

import { useEffect, useState, use } from 'react';
import Link from 'next/link';
import { useLocale, useTranslations } from 'next-intl';

import { ArrowLeft, MapPin } from 'lucide-react';

import { Ledger, LedgerRow, MutedText, MonoAnnotation } from '@/components/ui/ledger';
import { StatTile } from '@/components/ui/stat-tile';
import { ErrorState, LoadingState } from '@/components/ui/states';

import { HeartButton } from '@/components/property/heart-button';
import { MortgageEstimate } from '@/components/property/MortgageEstimate';
import { NeighborhoodSummary } from '@/components/property/NeighborhoodSummary';
import { PropertyCard } from '@/components/property/property-card';

import { getProperty, getRelatedProperties } from '@/lib/api';
import { formatPrice } from '@/lib/format';
import type { Property } from '@/lib/types';

interface PropertyPageProps {
  params: Promise<{ locale: string; id: string }>;
}

/**
 * One property.
 *
 * The search answers with listings and the card shows them, but a reader who
 * picks one needs more than a card: the price, the numbers of the listing, the
 * neighbourhood in words, and the other listings it competes with. That is
 * this page.
 *
 * The data is public - a visitor who clicks a listing is nobody until they
 * sign in - so the page reads without a session and asks for nothing.
 */
export default function PropertyPage({ params }: PropertyPageProps) {
  const t = useTranslations();
  const tDetails = useTranslations('property.details');
  const tCard = useTranslations('property.card');
  const tFeatures = useTranslations('property.details');
  const locale = useLocale();

  const resolvedParams = use(params);
  const propertyId = resolvedParams.id;

  const [property, setProperty] = useState<Property | null>(null);
  const [related, setRelated] = useState<Property[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!propertyId) return;
    let cancelled = false;

    const load = async () => {
      try {
        setLoading(true);
        setError(null);

        const propertyData = await getProperty(propertyId);
        if (cancelled) return;
        setProperty(propertyData);

        // The comparables are a bonus: a failure there must not empty the
        // page, so it is swallowed and the section simply stays out.
        try {
          const relatedData = await getRelatedProperties(propertyId, 3);
          if (!cancelled) setRelated(relatedData.properties || []);
        } catch {
          if (!cancelled) setRelated([]);
        }
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : 'loadError');
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    void load();
    return () => {
      cancelled = true;
    };
  }, [propertyId]);

  if (loading) {
    return (
      <main className="container mx-auto px-4 py-10">
        <LoadingState />
      </main>
    );
  }

  if (error || !property) {
    return (
      <main className="container mx-auto px-4 py-10">
        <ErrorState
          title={tDetails('notFound')}
          description={error ?? tDetails('loadError')}
        />
        <div className="mt-6">
          <Link
            href={`/${locale}/search`}
            className="inline-flex items-center gap-2 text-sm text-muted-foreground underline underline-offset-4"
          >
            <ArrowLeft className="h-4 w-4" aria-hidden />
            {tDetails('backToSearch')}
          </Link>
        </div>
      </main>
    );
  }

  const title = property.title || tCard('untitled');
  const price = formatPrice(property.price, property.currency || 'USD', locale);
  const location = [
    property.address,
    property.neighborhood,
    property.district,
    property.city,
    property.country,
  ]
    .filter(Boolean)
    .join(', ');

  const facts = [
    property.property_type ? { label: tDetails('propertyType'), value: property.property_type } : null,
    property.listing_type ? { label: tDetails('listingType'), value: property.listing_type } : null,
    property.rooms ? { label: tDetails('rooms'), value: String(property.rooms) } : null,
    property.bathrooms ? { label: tDetails('bathrooms'), value: String(property.bathrooms) } : null,
    property.area_sqm ? { label: tDetails('area'), value: `${property.area_sqm} m²` } : null,
    property.floor !== undefined && property.floor !== null
      ? { label: tDetails('floor'), value: String(property.floor) }
      : null,
    property.total_floors
      ? { label: tDetails('totalFloors'), value: String(property.total_floors) }
      : null,
    property.year_built ? { label: tDetails('yearBuilt'), value: String(property.year_built) } : null,
    property.energy_rating
      ? { label: tDetails('heating'), value: property.energy_rating }
      : null,
  ].filter((fact): fact is { label: string; value: string } => fact !== null);

  const features = [
    property.has_parking ? tFeatures('parking') : null,
    property.has_garden ? tFeatures('garden') : null,
    property.has_pool ? tFeatures('pool') : null,
    property.has_garage ? tFeatures('garage') : null,
    property.has_bike_room ? tFeatures('bikeRoom') : null,
    property.has_elevator ? tFeatures('elevator') : null,
  ].filter((feature): feature is string => Boolean(feature));

  return (
    <main className="container mx-auto px-4 py-10">
      <div className="mb-6">
        <Link
          href={`/${locale}/search`}
          className="inline-flex items-center gap-2 text-sm text-muted-foreground underline underline-offset-4"
        >
          <ArrowLeft className="h-4 w-4" aria-hidden />
          {t('nav.search')}
        </Link>
      </div>

      <div className="grid gap-10 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
        <div className="space-y-8">
          <header className="space-y-3">
            <h1 className="font-sans text-3xl font-semibold tracking-tight">{title}</h1>
            {location ? (
              <p className="flex items-center gap-1.5 text-sm text-muted-foreground">
                <MapPin className="h-4 w-4 shrink-0" aria-hidden />
                {location}
              </p>
            ) : null}
            <div className="flex flex-wrap items-end gap-6 pt-2">
              <span className="font-mono text-3xl font-semibold tabular-nums tracking-tight">
                {price || tCard('priceOnRequest')}
              </span>
              {property.price ? (
                <MortgageEstimate
                  price={property.price}
                  currency={property.currency || 'USD'}
                  locale={locale}
                />
              ) : null}
              {property.id ? (
                <div className="ml-auto">
                  <HeartButton propertyId={property.id} />
                </div>
              ) : null}
            </div>
          </header>

          {property.images?.[0] ? (
            <div className="aspect-video w-full overflow-hidden rounded-lg bg-muted">
              <img
                src={property.images[0]}
                alt={title}
                className="size-full object-cover"
                loading="lazy"
              />
            </div>
          ) : null}

          <NeighborhoodSummary
            city={property.city}
            neighborhood={property.neighborhood ?? property.district}
            propertyType={property.property_type}
            rooms={property.rooms}
            area_sqm={property.area_sqm}
            language={locale}
          />

          {property.description ? (
            <section className="space-y-3">
              <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
                {tDetails('description')}
              </h2>
              <p className="text-sm leading-relaxed text-foreground">{property.description}</p>
            </section>
          ) : null}

          {facts.length > 0 ? (
            <section className="space-y-3">
              <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
                {tDetails('facts')}
              </h2>
              <Ledger>
                {facts.map((fact) => (
                  <LedgerRow key={fact.label}>
                    <MutedText>{fact.label}</MutedText>
                    <MonoAnnotation className="text-right">{fact.value}</MonoAnnotation>
                  </LedgerRow>
                ))}
              </Ledger>
            </section>
          ) : null}

          {features.length > 0 ? (
            <section className="space-y-3">
              <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
                {tDetails('amenities')}
              </h2>
              <div className="flex flex-wrap gap-2">
                {features.map((feature) => (
                  <span
                    key={feature}
                    className="rounded-md border border-border px-2.5 py-1 font-mono text-[12px] text-muted-foreground"
                  >
                    {feature}
                  </span>
                ))}
              </div>
            </section>
          ) : null}
        </div>

        <aside className="space-y-6">
          <div className="flex flex-wrap gap-6">
            {property.rooms ? (
              <StatTile value={String(property.rooms)} label={tCard('bedsUnit')} />
            ) : null}
            {property.area_sqm ? (
              <StatTile value={`${property.area_sqm} m²`} label={tDetails('area')} />
            ) : null}
            {property.price_per_sqm ? (
              <StatTile
                value={formatPrice(property.price_per_sqm, property.currency || 'USD', locale)}
                hint="/m²"
                label={tDetails('price')}
              />
            ) : null}
          </div>

          {property.source_url ? (
            <a
              href={property.source_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 text-sm underline underline-offset-4"
            >
              {property.source_platform || tDetails('location')}
              <span aria-hidden>↗</span>
            </a>
          ) : null}
        </aside>
      </div>

      {related.length > 0 ? (
        <section className="mt-12 space-y-4">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
            {tDetails('related')}
          </h2>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {related.map((item) => (
              <PropertyCard key={item.id} property={item} />
            ))}
          </div>
        </section>
      ) : null}
    </main>
  );
}
