'use client';

import { useEffect, useMemo } from 'react';
import { divIcon } from 'leaflet';
import { MapContainer, Marker, TileLayer, useMap } from 'react-leaflet';
import { useTranslations } from 'next-intl';

import { cn } from '@/lib/utils';
import type { CityMarketSummary } from './city-market-stats';

/**
 * The catalogue on the map of Poland.
 *
 * One marker per city: a filled disc with the number of listings in it, or a
 * dashed ring for a city the catalogue holds nothing for. The legend says
 * which is which - a city that is not covered is a fact about the catalogue,
 * not an absence.
 *
 * The tiles are raster OSM tiles, and they are light by nature. The dark
 * theme therefore filters the tile pane itself, the same way the search
 * route does: a filter on the pane follows the theme toggle without a
 * re-mount of the map.
 */

const LIGHT_TILE_FILTER = 'grayscale(1)';
const DARK_TILE_FILTER = 'grayscale(1) invert(1) brightness(.9) contrast(.9)';

function TileTheme() {
  const map = useMap();

  useEffect(() => {
    const root = document.documentElement;

    const apply = () => {
      const dark = root.classList.contains('dark');
      const pane = map.getPane('tilePane');
      if (pane) pane.style.filter = dark ? DARK_TILE_FILTER : LIGHT_TILE_FILTER;
    };

    apply();

    const observer = new MutationObserver(apply);
    observer.observe(root, { attributes: true, attributeFilter: ['class'] });
    return () => observer.disconnect();
  }, [map]);

  return null;
}

/** The marker of one city: a disc with the count, or a dashed empty ring. */
function cityIcon(count: number, isSelected: boolean) {
  const size = count >= 50 ? 40 : count >= 10 ? 34 : 28;
  if (count === 0) {
    return divIcon({
      className: '',
      html: `<div style="width:${size}px;height:${size}px;border-radius:9999px;border:1px dashed hsl(var(--muted-foreground));background:hsl(var(--background))"></div>`,
      iconSize: [size, size],
      iconAnchor: [size / 2, size / 2],
    });
  }
  const background = isSelected ? 'hsl(var(--foreground))' : 'hsl(var(--chart-1))';
  const colour = isSelected ? 'hsl(var(--background))' : 'hsl(var(--background))';
  return divIcon({
    className: '',
    html: `<div style="min-width:${size}px;height:${size}px;padding:0 8px;box-sizing:border-box;background:${background};color:${colour};border-radius:9999px;border:2px solid hsl(var(--background));box-shadow:0 1px 2px hsl(var(--foreground) / 0.3);display:flex;align-items:center;justify-content:center;font:600 12px Geist,system-ui,sans-serif">${count}</div>`,
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
  });
}

export interface CityMarketMapProps {
  cities: CityMarketSummary[];
  /** The city the ledger and the detail panel are showing. */
  selected: string | null;
  onSelect: (city: string) => void;
  className?: string;
}

export function CityMarketMap({ cities, selected, onSelect, className }: CityMarketMapProps) {
  const t = useTranslations('pages.cityOverview');

  const icons = useMemo(
    () =>
      new Map(
        cities.map((city) => [
          city.city,
          cityIcon(city.listingCount, city.city === selected),
        ])
      ),
    [cities, selected]
  );

  return (
    <div className={cn('relative h-full w-full bg-muted/40', className)}>
      <div className="h-full w-full" role="application" aria-label={t('map.aria')}>
        <MapContainer
          center={[51.9, 19.2]}
          zoom={6}
          scrollWheelZoom={false}
          className="h-full w-full"
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          <TileTheme />
          {cities.map((city) => (
            <Marker
              key={city.city}
              position={[city.lat, city.lon]}
              icon={icons.get(city.city)}
              eventHandlers={{ click: () => onSelect(city.city) }}
            />
          ))}
        </MapContainer>
      </div>

      <div className="absolute bottom-6 left-4 z-[500] flex flex-wrap items-center gap-3 rounded-md border border-border bg-background px-2.5 py-1.5 text-[11px] leading-4 text-muted-foreground">
        <span className="flex items-center gap-1.5">
          <span className="size-2.5 rounded-full bg-chart-1" aria-hidden="true" />
          {t('map.legend.listings')}
        </span>
        <span className="flex items-center gap-1.5">
          <span
            className="size-2.5 rounded-full border border-dashed border-muted-foreground"
            aria-hidden="true"
          />
          {t('map.legend.empty')}
        </span>
      </div>
    </div>
  );
}

export default CityMarketMap;
