'use client';

import { useEffect, useMemo, useState } from 'react';
import dynamic from 'next/dynamic';
import { useTranslations } from 'next-intl';

import { buildHeaders, getApiUrl } from '@/lib/api/client';
import { formatPrice } from '@/lib/format';
import type { Property, SearchResponse } from '@/lib/types';
import { LANDING_SLOTS, withSlot } from '@/lib/utm';

/**
 * The map is Leaflet, and Leaflet is a browser library: it is loaded only in
 * the browser, after the page has painted. Until it arrives the lattice
 * below is what the panel shows, so the panel is never empty.
 */
const HeroMap = dynamic(() => import('@/components/landing/hero-map'), {
  ssr: false,
  loading: () => null,
});


/**
 * The instrument of the hero: the demo, running.
 *
 * It asks the live catalogue the demo question and shows what came back -
 * the count, the pins on the map, three priced rows. Nothing here is a
 * picture of the product; it is the product, with the demo catalogue and no
 * keys.
 */

interface InstrumentState {
  count: number;
  results: Property[];
}

const FALLBACK: InstrumentState = { count: 0, results: [] };

export function HeroInstrument({ query, locale }: { query: string; locale: string }) {
  const t = useTranslations('landing');
  const [state, setState] = useState<InstrumentState>(FALLBACK);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const response = await fetch(`${getApiUrl()}/search`, {
          method: 'POST',
          headers: buildHeaders(),
          body: JSON.stringify({
            query,
            limit: 6,
            filters: { city: 'Kraków', max_price: 500000 },
          }),
        });
        if (!response.ok) throw new Error(`search failed: ${response.status}`);
        const data = (await response.json()) as SearchResponse;
        if (cancelled) return;
        setState({
          count: data.count ?? data.results?.length ?? 0,
          results: (data.results ?? []).slice(0, 3).map((item) => item.property),
        });
      } catch {
        if (!cancelled) setFailed(true);
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, [query]);

  const chips = useMemo(
    () => [
      'city = Kraków',
      'price ≤ 500 000 zł',
      'rooms = 2',
      'type = apartment',
    ],
    []
  );

  const points = useMemo(
    () =>
      state.results
        .filter((property) => property.latitude && property.longitude)
        .map((property) => ({
          id: property.id ?? `${property.city}-${property.price}`,
          lat: property.latitude as number,
          lon: property.longitude as number,
          price: property.price,
          currency: property.currency ?? 'PLN',
        })),
    [state.results]
  );

  return (
    <div className="flex flex-col overflow-hidden rounded-[10px] border border-border">
      <div className="flex flex-wrap items-center gap-1.5 border-b border-border px-3.5 py-2.5 text-[12px]">
        <span className="mr-0.5 font-mono text-muted-foreground">{t('hero.instrumentParsed')}</span>
        {chips.map((chip) => (
          <span key={chip} className="rounded-[4px] bg-muted px-[7px] py-px">
            {chip}
          </span>
        ))}
        <span className="ml-auto font-mono text-muted-foreground">
          {state.count > 0 ? t('hero.matches', { count: state.count }) : '—'}
        </span>
      </div>

      <div className="relative h-[290px] border-b border-border bg-muted/40">
        <svg className="absolute inset-0 h-full w-full" aria-hidden="true">
          <defs>
            <pattern id="hero-grid" width="40" height="40" patternUnits="userSpaceOnUse">
              <path d="M 40 0 L 0 0 0 40" fill="none" stroke="currentColor" strokeWidth="1" className="text-border" />
            </pattern>
          </defs>
          <rect width="100%" height="100%" fill="url(#hero-grid)" />
        </svg>

        {points.length > 0 && (
          <HeroMap
            points={points}
            className="absolute inset-0 z-10 h-full w-full"
          />
        )}

        {state.results.length === 0 && (
          <span className="absolute inset-0 flex items-center justify-center text-[12px] text-muted-foreground">
            {failed ? '—' : '…'}
          </span>
        )}
      </div>

      <div>
        {state.results.map((property) => (
          <div
            key={property.id ?? `${property.city}-${property.price}`}
            data-testid="instrument-row"
            className="grid grid-cols-[96px_minmax(0,1fr)] items-baseline gap-3 border-b border-border px-3.5 py-2.5 text-left sm:grid-cols-[96px_minmax(0,1fr)_92px_92px]"
          >
            <span className="font-mono text-[14px] font-semibold">
              {formatPrice(property.price, property.currency ?? 'PLN', 'pl-PL')}
            </span>
            <span className="text-[14px]">
              {property.rooms} rooms, {property.area_sqm} m² in {property.district ?? property.city}
            </span>
            {/* The two derived numbers sit on their own row at the phone
                width: the four-column grid needs 344px and the row has 340px
                there, and the instrument clips what does not fit - a price cut
                in half. From `sm` up the wrapper dissolves and the numbers
                take their two columns. */}
            <span className="col-span-2 flex items-baseline justify-end gap-4 sm:contents">
              <span className="text-right font-mono text-[12px] text-muted-foreground">
                {property.price && property.area_sqm
                  ? t('hero.instrumentPerSqm', {
                      amount: Math.round(property.price / property.area_sqm).toLocaleString('en-US'),
                      currency: property.currency ?? 'PLN',
                    })
                  : '—'}
              </span>
              <span className="text-right font-mono text-[12px] text-success">
                {property.price ? t('hero.instrumentPerMonth', { amount: '2 473' }) : '—'}
              </span>
            </span>
          </div>
        ))}
      </div>

      <div className="mt-auto flex items-center justify-between px-3.5 py-2 text-[12px] text-muted-foreground">
        <span>{t('hero.instrumentNote')}</span>
        <a
          href={withSlot(`/${locale}/search`, LANDING_SLOTS.instrument)}
          className="text-foreground hover:underline"
        >
          {t('hero.instrumentOpenAll', { count: state.count })}
        </a>
      </div>
    </div>
  );
}
