'use client';

import { useEffect, useState, useMemo } from 'react';
import { MapPin, Building2, DollarSign, AlertCircle, Loader2 } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { searchProperties } from '@/lib/api';
import {
  computeCenter,
  extractMapPoints,
  type PropertyMapPoint,
} from '@/components/search/property-map-utils';
import { PageHeader } from '@/components/ui/page-header';
import dynamic from 'next/dynamic';

const PropertyMapboxMap = dynamic(() => import('@/components/search/property-mapbox-map'), {
  ssr: false,
  loading: () => <div className="h-[600px] w-full bg-muted animate-pulse rounded-lg" />,
});

interface CityStats {
  city: string;
  country: string;
  propertyCount: number;
  avgPrice: number;
  minPrice: number;
  maxPrice: number;
  points: PropertyMapPoint[];
  center: { lat: number; lon: number };
}

const POPULAR_CITIES = [
  'Warsaw',
  'Krakow',
  'Gdansk',
  'Wroclaw',
  'Poznan',
  'Lodz',
  'Katowice',
  'Lublin',
];

export default function CityOverviewPage() {
  const t = useTranslations('pages.cityOverview');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [cityStats, setCityStats] = useState<CityStats[]>([]);
  const [selectedCity, setSelectedCity] = useState<string | null>(null);

  useEffect(() => {
    const loadCityData = async () => {
      setLoading(true);
      setError(null);

      const results = await Promise.allSettled(
        POPULAR_CITIES.map(async (city) => {
          const response = await searchProperties({
            query: `properties in ${city}`,
            limit: 100,
          });
          return { city, response };
        })
      );

      const stats: CityStats[] = [];

      for (const result of results) {
        if (result.status === 'rejected') continue;

        const { city, response } = result.value;
        if (response.results.length === 0) continue;

        const points = extractMapPoints(response.results);
        const prices = points.map((p) => p.price).filter((p): p is number => typeof p === 'number');

        const center = computeCenter(points) ?? { lat: 52.2297, lon: 21.0122 };

        stats.push({
          city,
          country: response.results[0].property.country || 'Poland',
          propertyCount: response.results.length,
          avgPrice:
            prices.length > 0 ? Math.round(prices.reduce((a, b) => a + b, 0) / prices.length) : 0,
          minPrice: prices.length > 0 ? prices.reduce((a, b) => Math.min(a, b)) : 0,
          maxPrice: prices.length > 0 ? prices.reduce((a, b) => Math.max(a, b)) : 0,
          points,
          center,
        });
      }

      setCityStats(stats.sort((a, b) => b.propertyCount - a.propertyCount));
      if (stats.length === 0) {
        setError(
          'No city data available. The property database may be empty or the API is unreachable.'
        );
      }
      setLoading(false);
    };

    loadCityData();
  }, []);

  const selectedCityData = useMemo(() => {
    return selectedCity ? cityStats.find((c) => c.city === selectedCity) : null;
  }, [selectedCity, cityStats]);

  const allPoints = useMemo(() => {
    return cityStats.flatMap((stat) => stat.points);
  }, [cityStats]);

  const handleMarkerClick = (point: PropertyMapPoint) => {
    const city = cityStats.find((c) => c.points.some((p) => p.id === point.id));
    if (city) {
      setSelectedCity(city.city);
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  };

  return (
    <div className="container mx-auto px-4 py-8" aria-live="polite">
      <div className="flex flex-col space-y-8">
        {/* Header */}
        <PageHeader title={t('title')} description={t('description')} />

        {/* Loading state */}
        {loading && (
          <div
            className="flex flex-col items-center justify-center h-96 text-center"
            role="status"
            aria-live="polite"
          >
            <Loader2 className="h-12 w-12 animate-spin text-primary mb-4" aria-hidden="true" />
            <p className="text-lg font-medium">Loading city data...</p>
            <p className="text-sm text-muted-foreground">This may take a moment</p>
          </div>
        )}

        {/* Error state */}
        {error && !loading && cityStats.length === 0 && (
          <div
            className="flex flex-col items-center justify-center h-96 text-center border rounded-lg bg-muted/50"
            role="alert"
            aria-live="assertive"
          >
            <div className="p-4 rounded-full bg-muted mb-4">
              <AlertCircle className="h-12 w-12 text-muted-foreground" aria-hidden="true" />
            </div>
            <h2 className="text-2xl font-bold mb-2">No City Data Available</h2>
            <p className="text-muted-foreground max-w-md mb-4">{error}</p>
            <button
              type="button"
              onClick={() => window.location.reload()}
              className="px-4 py-2 rounded-md bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
            >
              Retry
            </button>
          </div>
        )}

        {/* Main content */}
        {!loading && cityStats.length > 0 && (
          <>
            {/* Map with all cities */}
            {allPoints.length > 0 && (
              <div className="space-y-4">
                <h2 className="text-2xl font-semibold">All Properties Map</h2>
                <div className="relative">
                  <PropertyMapboxMap
                    points={allPoints}
                    mapboxToken={process.env.NEXT_PUBLIC_MAPBOX_TOKEN}
                    showHeatmap={true}
                    heatmapIntensity={1.5}
                    showClusters={true}
                    onMarkerClick={handleMarkerClick}
                    className="h-[600px]"
                  />
                  <div className="absolute top-4 left-4 z-10 bg-background/90 backdrop-blur rounded-lg border p-3 shadow-sm">
                    <p className="text-sm font-medium">Click a marker to view city details</p>
                    <p className="text-xs text-muted-foreground">
                      {allPoints.length} properties across {cityStats.length} cities
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* City cards grid */}
            <div className="space-y-4">
              <h2 className="text-2xl font-semibold">Market Statistics by City</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                {cityStats.map((stat) => (
                  <div
                    key={`${stat.city}-${stat.country}`}
                    className={`rounded-lg border bg-card text-card-foreground shadow-sm overflow-hidden cursor-pointer transition-all hover:shadow-md ${
                      selectedCity === stat.city ? 'ring-2 ring-primary' : ''
                    }`}
                    onClick={() => setSelectedCity(stat.city)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault();
                        setSelectedCity(stat.city);
                      }
                    }}
                    role="button"
                    tabIndex={0}
                    aria-pressed={selectedCity === stat.city}
                  >
                    <div className="p-6 space-y-4">
                      <div className="flex items-start justify-between">
                        <div>
                          <h3 className="text-xl font-bold">{stat.city}</h3>
                          <p className="text-sm text-muted-foreground">{stat.country}</p>
                        </div>
                        <div className="p-2 rounded-full bg-primary/10">
                          <MapPin className="h-4 w-4 text-primary" aria-hidden="true" />
                        </div>
                      </div>

                      <div className="space-y-3">
                        <div className="flex items-center gap-2">
                          <Building2 className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
                          <span className="text-sm">{stat.propertyCount} properties</span>
                        </div>

                        <div className="flex items-center gap-2">
                          <DollarSign
                            className="h-4 w-4 text-muted-foreground"
                            aria-hidden="true"
                          />
                          <div className="text-sm">
                            <span className="font-medium">${stat.avgPrice.toLocaleString()}</span>
                            <span className="text-muted-foreground"> avg</span>
                          </div>
                        </div>

                        <div className="text-xs text-muted-foreground">
                          ${stat.minPrice.toLocaleString()} - ${stat.maxPrice.toLocaleString()}
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Selected city details */}
            {selectedCityData && (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h2 className="text-2xl font-semibold">{selectedCityData.city} Properties</h2>
                  <button
                    type="button"
                    onClick={() => setSelectedCity(null)}
                    className="text-sm text-muted-foreground hover:text-foreground"
                  >
                    Close
                  </button>
                </div>

                <div className="relative">
                  <PropertyMapboxMap
                    points={selectedCityData.points}
                    mapboxToken={process.env.NEXT_PUBLIC_MAPBOX_TOKEN}
                    showHeatmap={true}
                    heatmapIntensity={2}
                    showClusters={false}
                    className="h-[500px]"
                  />
                  <div className="absolute top-4 left-4 z-10 bg-background/90 backdrop-blur rounded-lg border p-3 shadow-sm">
                    <p className="text-sm font-medium">{selectedCityData.city}</p>
                    <p className="text-xs text-muted-foreground">
                      {selectedCityData.points.length} properties shown
                    </p>
                  </div>
                </div>

                {/* Property list */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  {selectedCityData.points.slice(0, 9).map((point) => (
                    <div
                      key={point.id}
                      className="rounded-lg border bg-card text-card-foreground shadow-sm overflow-hidden"
                    >
                      <div className="aspect-video w-full bg-muted flex items-center justify-center">
                        <MapPin className="h-8 w-8 text-muted-foreground" aria-hidden="true" />
                      </div>
                      <div className="p-4 space-y-2">
                        <h3 className="font-semibold">{point.title ?? 'Untitled Property'}</h3>
                        <p className="text-sm text-muted-foreground">
                          {point.city}, {point.country}
                        </p>
                        <div className="font-bold text-lg">
                          {point.price ? `$${point.price.toLocaleString()}` : 'Price on request'}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
