'use client';

import { useEffect, useMemo, useState } from 'react';
import dynamic from 'next/dynamic';
import { useTranslations } from 'next-intl';

import { searchProperties } from '@/lib/api';
import { buildHeaders, getApiUrl } from '@/lib/api/client';
import type { SearchResultItem } from '@/lib/types';
import { MonoAnnotation } from '@/components/ui/mono-annotation';
import { PageHeader } from '@/components/ui/page-header';
import { EmptyState, ErrorState, LoadingState } from '@/components/ui/states';
import { CityMarketLedger } from '@/components/market-trends/city-market-ledger';
import { CityMarketDetail } from '@/components/market-trends/city-market-detail';
import {
  CITY_CATALOGUE,
  listingsInCity,
  priceScale,
  summariseCities,
} from '@/components/market-trends/city-market-stats';

const CityMarketMap = dynamic(() => import('@/components/market-trends/city-market-map'), {
  ssr: false,
  loading: () => <div className="h-full w-full animate-pulse bg-muted/40" />,
});

/**
 * The market of a city, city by city.
 *
 * The route reads the catalogue once per city and says what it holds: how
 * many listings, what they cost, and where the city sits on the map. The
 * catalogue is the only source here - a city it holds nothing for is drawn
 * as a row with dashes, not hidden.
 */
export default function CityOverviewPage() {
  const t = useTranslations('pages.cityOverview');
  const tCommon = useTranslations('common');

  const [loading, setLoading] = useState(true);
  const [hasError, setHasError] = useState(false);
  const [listingsByCity, setListingsByCity] = useState<Record<string, SearchResultItem[]>>({});
  const [counts, setCounts] = useState<Record<string, number>>({});
  const [selectedCity, setSelectedCity] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    const loadCityData = async () => {
      setLoading(true);
      setHasError(false);

      // The catalogue says how many listings each city holds. The searches
      // below say what they cost - a search answers with what it found, so
      // the two are read from their own sources.
      const catalogue = fetch(`${getApiUrl()}/catalogue/stats`, {
        headers: buildHeaders(),
      })
        .then((response) => (response.ok ? response.json() : null))
        .then((data: { cities?: Array<{ name: string; count: number }> } | null) => {
          const byName: Record<string, number> = {};
          for (const city of data?.cities ?? []) {
            byName[city.name] = city.count;
          }
          return byName;
        })
        .catch(() => ({}) as Record<string, number>);

      const results = await Promise.allSettled(
        CITY_CATALOGUE.map(async (city) => {
          const response = await searchProperties({
            query: `properties in ${city.name}`,
            limit: 100,
          });
          return { city, results: response.results };
        })
      );

      const countsByName = await catalogue;

      if (cancelled) return;

      const byCity: Record<string, SearchResultItem[]> = {};
      let covered = 0;

      for (const result of results) {
        if (result.status === 'rejected') continue;
        // A search answers by meaning, so it can answer with the listings of
        // another city. Only the city's own listings are its listings.
        const own = listingsInCity(result.value.city, result.value.results);
        byCity[result.value.city.name] = own;
        const count = countsByName[result.value.city.label] ?? countsByName[result.value.city.name];
        if ((count ?? own.length) > 0) covered += 1;
      }

      setListingsByCity(byCity);
      setCounts(countsByName);
      // The first city the catalogue actually holds is the one that opens.
      const firstCovered = CITY_CATALOGUE.find((city) => {
        const count = countsByName[city.label] ?? countsByName[city.name];
        return (count ?? (byCity[city.name] ?? []).length) > 0;
      });
      setSelectedCity(firstCovered?.name ?? CITY_CATALOGUE[0].name);
      setHasError(covered === 0);
      setLoading(false);
    };

    loadCityData();
    return () => {
      cancelled = true;
    };
  }, []);

  const cities = useMemo(() => summariseCities(listingsByCity, counts), [listingsByCity, counts]);
  const scale = useMemo(() => priceScale(cities), [cities]);
  const selected = useMemo(
    () => cities.find((city) => city.city === selectedCity) ?? null,
    [cities, selectedCity]
  );

  const listingTotal = useMemo(
    () => cities.reduce((total, city) => total + city.listingCount, 0),
    [cities]
  );
  const covered = useMemo(() => cities.filter((city) => city.listingCount > 0).length, [cities]);

  return (
    <div className="flex min-h-[calc(100vh-56px)] flex-col" aria-live="polite">
      <div className="border-b border-border px-6 pb-5 pt-6">
        <PageHeader
          title={t('title')}
          description={t('description')}
          actions={
            <MonoAnnotation>
              {t('source', {
                listings: listingTotal,
                covered,
                total: CITY_CATALOGUE.length,
              })}
            </MonoAnnotation>
          }
        />
      </div>

      {loading ? (
        <div className="px-6 py-8">
          <LoadingState rows={8} />
        </div>
      ) : hasError && listingTotal === 0 ? (
        <div className="px-6 py-8">
          <ErrorState
            title={t('empty.title')}
            description={t('errors.noData')}
            onRetry={() => window.location.reload()}
            retryLabel={tCommon('retry')}
          />
        </div>
      ) : (
        <div className="grid flex-1 grid-cols-1 lg:grid-cols-[600px_minmax(0,1fr)]">
          <div className="flex flex-col border-b border-border lg:border-b-0 lg:border-r">
            <CityMarketLedger
              cities={cities}
              selected={selectedCity}
              onSelect={setSelectedCity}
            />
            <CityMarketDetail city={selected} scale={scale} />
          </div>

          <div className="relative min-h-[520px] lg:min-h-[720px]">
            {listingTotal > 0 ? (
              <CityMarketMap
                cities={cities}
                selected={selectedCity}
                onSelect={setSelectedCity}
              />
            ) : (
              <EmptyState
                title={t('empty.title')}
                description={t('errors.noData')}
                className="px-6"
              />
            )}
          </div>
        </div>
      )}
    </div>
  );
}
