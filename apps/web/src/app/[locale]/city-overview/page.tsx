'use client';

import { useEffect, useMemo, useState } from 'react';
import dynamic from 'next/dynamic';
import { useTranslations } from 'next-intl';

import { searchProperties } from '@/lib/api';
import type { SearchResultItem } from '@/lib/types';
import { MonoAnnotation } from '@/components/ui/mono-annotation';
import { PageHeader } from '@/components/ui/page-header';
import { EmptyState, ErrorState, LoadingState } from '@/components/ui/states';
import { CityMarketLedger } from '@/components/market-trends/city-market-ledger';
import { CityMarketDetail } from '@/components/market-trends/city-market-detail';
import {
  CITY_CATALOGUE,
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
  const [selectedCity, setSelectedCity] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    const loadCityData = async () => {
      setLoading(true);
      setHasError(false);

      const results = await Promise.allSettled(
        CITY_CATALOGUE.map(async (city) => {
          const response = await searchProperties({
            query: `properties in ${city.name}`,
            limit: 100,
          });
          return { city: city.name, results: response.results };
        })
      );

      if (cancelled) return;

      const byCity: Record<string, SearchResultItem[]> = {};
      let covered = 0;

      for (const result of results) {
        if (result.status === 'rejected') continue;
        byCity[result.value.city] = result.value.results;
        if (result.value.results.length > 0) covered += 1;
      }

      setListingsByCity(byCity);
      // The first city the catalogue actually holds is the one that opens.
      const firstCovered = CITY_CATALOGUE.find(
        (city) => (byCity[city.name] ?? []).length > 0
      );
      setSelectedCity(firstCovered?.name ?? CITY_CATALOGUE[0].name);
      setHasError(covered === 0);
      setLoading(false);
    };

    loadCityData();
    return () => {
      cancelled = true;
    };
  }, []);

  const cities = useMemo(() => summariseCities(listingsByCity), [listingsByCity]);
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
