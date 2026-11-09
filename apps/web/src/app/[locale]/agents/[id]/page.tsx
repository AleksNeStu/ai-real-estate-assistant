'use client';

import { useEffect, useMemo, useState, use } from 'react';
import dynamic from 'next/dynamic';
import Link from 'next/link';
import { useLocale, useTranslations } from 'next-intl';

import { MonoAnnotation } from '@/components/ui/mono-annotation';
import { StatTile } from '@/components/ui/stat-tile';
import { EmptyState, ErrorState, LoadingState } from '@/components/ui/states';

import { ContactAgentForm } from '@/components/agents/contact-agent-form';
import { ScheduleViewingDialog } from '@/components/agents/schedule-viewing-dialog';
import { AgentListingsLedger } from '@/components/agents/agent-listings-ledger';

import { getAgent, getAgentListings } from '@/lib/api';
import { formatPrice } from '@/lib/format';
import type { AgentListing, AgentProfile } from '@/lib/types';
import type { PropertyMapPoint } from '@/components/search/property-map-utils';

/**
 * The agent profile.
 *
 * The prototype draws it as a header over two columns: the agent's listings
 * and a short biography on the left, the way to reach the agent on the
 * right - a contact form that stays where it is put, and the details that
 * do not change. The listing the reader picks is the one the form is about,
 * so the request never arrives without a subject.
 *
 * The map is the same map the search route draws: it filters its tiles in
 * the dark theme, and it is loaded on demand so it never reaches the first
 * chunk.
 */

const PropertyMap = dynamic(() => import('@/components/search/property-map'), {
  ssr: false,
  loading: () => <div className="h-[300px] w-full animate-pulse rounded-lg bg-muted" />,
});

interface AgentProfilePageProps {
  params: Promise<{ locale: string; id: string }>;
}

/** The phone, with the digits a reader does not need to see hidden. */
function maskPhone(phone?: string): string | null {
  if (!phone) return null;
  const visible = phone.slice(0, Math.max(0, phone.length - 6));
  return `${visible} •• •• ••`;
}

export default function AgentProfilePage({ params }: AgentProfilePageProps) {
  const t = useTranslations();
  const tAgents = useTranslations('agents');
  const locale = useLocale();

  const resolvedParams = use(params);
  const agentId = resolvedParams.id;

  const [agent, setAgent] = useState<AgentProfile | null>(null);
  const [listings, setListings] = useState<AgentListing[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedPropertyId, setSelectedPropertyId] = useState<string | null>(null);
  const [viewingOpen, setViewingOpen] = useState(false);

  useEffect(() => {
    const loadAgent = async () => {
      try {
        setLoading(true);
        setError(null);

        const [agentData, listingsData] = await Promise.all([
          getAgent(agentId),
          getAgentListings(agentId),
        ]);

        setAgent(agentData);
        setListings(listingsData.items || []);
        if (listingsData.items?.length) {
          setSelectedPropertyId(listingsData.items[0].property_id);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : tAgents('profile.loadError'));
      } finally {
        setLoading(false);
      }
    };

    if (agentId) {
      void loadAgent();
    }
  }, [agentId, tAgents]);

  /** The listings that can be drawn on a map. */
  const mapPoints = useMemo<PropertyMapPoint[]>(() => {
    const points: PropertyMapPoint[] = [];
    listings.forEach((listing, index) => {
      const property = listing.property;
      if (!property) return;
      const { latitude, longitude } = property;
      if (typeof latitude !== 'number' || typeof longitude !== 'number') return;
      points.push({
        id: property.id ?? `${listing.id}-${index}`,
        lat: latitude,
        lon: longitude,
        title: property.title,
        city: property.city,
        country: property.country,
        price: property.price,
        currency: property.currency,
        area_sqm: property.area_sqm,
        rooms: property.rooms,
        property_type: property.property_type,
      });
    });
    return points;
  }, [listings]);

  /** The listing the contact form is about, in one line. */
  const about = useMemo(() => {
    const listing = listings.find((item) => item.property_id === selectedPropertyId);
    const property = listing?.property;
    if (!property) return undefined;
    const facts = [
      property.rooms ? t('profile.roomsLabel', { count: property.rooms }) : null,
      property.area_sqm ? `${property.area_sqm} m²` : null,
      property.district || property.neighborhood || null,
    ].filter(Boolean);
    const price = formatPrice(property.price, property.currency || 'USD', locale);
    return [...facts, property.address, price].filter(Boolean).join(' · ');
  }, [listings, selectedPropertyId, locale, t]);

  if (loading) {
    return (
      <div className="flex min-h-full flex-col bg-background">
        <div className="px-6 pt-4">
          <LoadingState rows={1} />
        </div>
        <div className="px-6 py-5">
          <LoadingState rows={6} />
        </div>
      </div>
    );
  }

  if (error || !agent) {
    return (
      <div className="flex min-h-full flex-col bg-background px-6 py-5">
        <Link
          href={`/${locale}/agents`}
          className="mb-5 text-[13px] text-muted-foreground hover:text-foreground"
        >
          &larr; {tAgents('profile.backToAgents')}
        </Link>
        <ErrorState
          title={error || tAgents('profile.notFound')}
          action={
            <Link
              href={`/${locale}/agents`}
              className="text-[14px] font-medium text-foreground hover:underline"
            >
              {tAgents('profile.browseAgents')}
            </Link>
          }
        />
      </div>
    );
  }

  const displayName =
    agent.name || agent.professional_email?.split('@')[0] || tAgents('profile.defaultName');
  const initials = displayName
    .split(/\s+/)
    .filter(Boolean)
    .map((part) => part[0])
    .join('')
    .toUpperCase()
    .slice(0, 2);
  const rating = agent.average_rating > 0 ? agent.average_rating.toFixed(1) : '—';
  const maskedPhone = maskPhone(agent.professional_phone);

  const meta = [
    agent.agency_name,
    agent.service_areas?.length ? agent.service_areas.join(', ') : null,
    agent.specialties?.length ? agent.specialties.join(', ') : null,
    agent.languages?.length ? agent.languages.join(', ') : null,
    agent.license_number
      ? `${tAgents('profile.license')} ${agent.license_number}${
          agent.license_state ? ` (${agent.license_state})` : ''
        }`
      : null,
  ]
    .filter(Boolean)
    .join(' · ');

  return (
    <div className="flex min-h-full flex-col bg-background">
      <div className="px-6 pt-4">
        <Link
          href={`/${locale}/agents`}
          className="text-[13px] text-muted-foreground hover:text-foreground"
        >
          &larr; {tAgents('profile.backToAgents')}
        </Link>
      </div>

      <div className="grid grid-cols-[72px_minmax(0,1fr)] items-center gap-5 border-b border-border px-6 py-5 sm:grid-cols-[72px_minmax(0,1fr)_auto]">
        {agent.profile_image_url ? (
          <img
            src={agent.profile_image_url}
            alt={displayName}
            className="size-[72px] rounded-full border border-border object-cover"
          />
        ) : (
          <span
            aria-hidden="true"
            className="grid size-[72px] place-items-center rounded-full border border-border bg-muted text-[22px] font-semibold text-foreground"
          >
            {initials}
          </span>
        )}

        <div className="flex min-w-0 flex-col gap-1">
          <div className="flex flex-wrap items-center gap-2.5">
            <h1 className="text-3xl font-semibold tracking-tight text-foreground">
              {displayName}
            </h1>
            {agent.is_verified ? (
              <span className="rounded-sm border border-border px-1.5 py-px font-mono text-[11px] font-medium text-success">
                {tAgents('verified')}
              </span>
            ) : null}
          </div>
          {meta ? (
            <span className="text-[14px] text-muted-foreground">{meta}</span>
          ) : null}
        </div>

        <div className="col-span-2 flex flex-wrap items-start gap-7 sm:col-span-1">
          <StatTile value={`★ ${rating}`} label={tAgents('reviews', { count: agent.total_reviews })} />
          <StatTile value={listings.length} label={tAgents('profile.activeListings')} />
          <StatTile value={agent.total_sales} label={tAgents('profile.statSales')} />
          <StatTile value={agent.total_rentals} label={tAgents('profile.statRentals')} />
        </div>
      </div>

      <div className="grid flex-1 grid-cols-1 lg:grid-cols-[minmax(0,1fr)_440px]">
        <main className="flex flex-col gap-5 border-b border-border px-6 py-5 lg:border-b-0 lg:border-r">
          {agent.bio ? (
            <p className="max-w-[720px] text-[14px] leading-[22px] text-foreground">{agent.bio}</p>
          ) : (
            <p className="text-[14px] italic text-muted-foreground">
              {tAgents('profile.noBio')}
            </p>
          )}

          {mapPoints.length ? (
            <div className="h-[300px] overflow-hidden rounded-lg border border-border">
              <PropertyMap points={mapPoints} className="size-full" />
            </div>
          ) : null}

          <div className="flex flex-col gap-1.5">
            <div className="flex flex-wrap items-baseline justify-between gap-3">
              <h2 className="text-[14px] font-semibold text-foreground">
                {tAgents('profile.listings')} ({listings.length})
              </h2>
              <MonoAnnotation>
                {tAgents('profile.listingsNote', { shown: listings.length })}
              </MonoAnnotation>
            </div>

            {listings.length === 0 ? (
              <EmptyState title={tAgents('profile.noListings')} />
            ) : (
              <AgentListingsLedger
                listings={listings}
                selectedPropertyId={selectedPropertyId}
                onSelect={setSelectedPropertyId}
                onSchedule={() => setViewingOpen(true)}
              />
            )}
          </div>
        </main>

        <aside className="px-6 py-5">
          <div className="sticky top-4 flex flex-col gap-3">
            <ContactAgentForm
              agent={agent}
              propertyId={selectedPropertyId ?? undefined}
              about={about}
            />

            <button
              type="button"
              onClick={() => setViewingOpen(true)}
              disabled={!selectedPropertyId}
              className="h-10 rounded-md border border-border px-4 text-[14px] font-medium text-foreground transition-colors hover:bg-muted disabled:opacity-50"
            >
              {tAgents('profile.scheduleViewingCta')}
            </button>

            <div className="grid grid-cols-[80px_minmax(0,1fr)] gap-x-3 gap-y-1.5 border-t border-border pt-3 text-[13px]">
              <span className="text-muted-foreground">{tAgents('profile.office')}</span>
              <span className="text-foreground">{agent.office_address || '—'}</span>

              <span className="text-muted-foreground">{tAgents('profile.phone')}</span>
              <span className="font-mono text-foreground">{maskedPhone || '—'}</span>

              <span className="text-muted-foreground">{tAgents('profile.email')}</span>
              <span className="text-foreground">{tAgents('profile.emailAfterContact')}</span>
            </div>
          </div>
        </aside>
      </div>

      {viewingOpen && selectedPropertyId ? (
        <ScheduleViewingDialog
          agent={agent}
          propertyId={selectedPropertyId}
          about={about}
          onSuccess={() => setViewingOpen(false)}
          onCancel={() => setViewingOpen(false)}
        />
      ) : null}
    </div>
  );
}
