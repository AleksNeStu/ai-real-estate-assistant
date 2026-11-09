'use client';

import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react';
import { divIcon, type LatLngBoundsExpression } from 'leaflet';
import { MapContainer, Marker, Popup, TileLayer, useMap, useMapEvents } from 'react-leaflet';
import { useLocale, useTranslations } from 'next-intl';

import { MapTileTheme } from '@/components/ui/map-tile-theme';
import { formatPrice } from '@/lib/format';
import { cn } from '@/lib/utils';

import { computeBounds, computeCenter, type PropertyMapPoint } from './property-map-utils';
import {
  clusterMapPoints,
  getClusterColor,
  type ClusteredMapItem,
} from './property-map-clustering';

/**
 * The tiles in the two themes.
 *
 * The prototype paints the map through one filter: the tiles are grey, and
 * in the dark theme they are inverted as well, so the map belongs to the
 * page instead of shouting over it. The filter is set on the tile pane
 * itself, because that is the only place Leaflet keeps the raster layer.
 * Every map in the application uses the same primitive: `MapTileTheme`.
 */

function FitBounds({ bounds }: { bounds: LatLngBoundsExpression | null }) {
  const map = useMap();
  useEffect(() => {
    if (!bounds) return;
    map.fitBounds(bounds, { padding: [24, 24] });
  }, [bounds, map]);
  return null;
}

function ZoomTracker({ onZoomChange }: { onZoomChange: (zoom: number) => void }) {
  const map = useMapEvents({
    zoomend: () => onZoomChange(map.getZoom()),
    moveend: () => onZoomChange(map.getZoom()),
  });
  useEffect(() => {
    onZoomChange(map.getZoom());
  }, [map, onZoomChange]);
  return null;
}

function ClusterMarker({
  cluster,
  zoom,
  icon,
  children,
}: {
  cluster: Extract<ClusteredMapItem, { kind: 'cluster' }>;
  zoom: number;
  icon: ReturnType<typeof divIcon>;
  children: ReactNode;
}) {
  const map = useMap();
  const onClick = useCallback(() => {
    const bounds = computeBounds(cluster.points);
    if (!bounds) {
      const nextZoom = Math.min(zoom + 2, 18);
      map.setView([cluster.lat, cluster.lon], nextZoom);
      return;
    }

    const maxZoom = Math.min(zoom + 2, 18);
    map.fitBounds(bounds, { padding: [24, 24], maxZoom });
  }, [cluster.lat, cluster.lon, cluster.points, map, zoom]);

  return (
    <Marker position={[cluster.lat, cluster.lon]} icon={icon} eventHandlers={{ click: onClick }}>
      {children}
    </Marker>
  );
}

export default function PropertyMap({
  points,
  className,
}: {
  points: PropertyMapPoint[];
  className?: string;
}) {
  const t = useTranslations('property');
  const tSearch = useTranslations('search');
  const locale = useLocale();
  const center = useMemo(() => computeCenter(points) ?? { lat: 52.2297, lon: 21.0122 }, [points]);
  const bounds = useMemo(() => computeBounds(points), [points]);
  const [zoom, setZoom] = useState(12);
  const onZoomChange = useCallback((nextZoom: number) => setZoom(nextZoom), []);
  const items = useMemo(() => clusterMapPoints(points, zoom), [points, zoom]);

  const markerIcon = useMemo(
    () =>
      divIcon({
        className: '',
        html: `<div style="width:14px;height:14px;background:hsl(var(--chart-1));border-radius:9999px;border:2px solid hsl(var(--background));box-shadow:0 1px 2px hsl(var(--foreground) / 0.3)"></div>`,
        iconSize: [14, 14],
        iconAnchor: [7, 7],
      }),
    []
  );

  const getClusterIcon = useCallback(
    (count: number, color: string) =>
      divIcon({
        className: '',
        html: `<div style="min-width:30px;height:30px;padding:0 8px;background:${color};color:hsl(var(--background));border-radius:9999px;border:2px solid hsl(var(--background));box-shadow:0 1px 2px hsl(var(--foreground) / 0.35);display:flex;align-items:center;justify-content:center;font-weight:700;font-size:12px;line-height:1">${count}</div>`,
        iconSize: [30, 30],
        iconAnchor: [15, 15],
      }),
    []
  );

  return (
    <div
      className={cn(
        'relative h-[420px] w-full overflow-hidden border-b border-border bg-muted/40 text-card-foreground',
        className
      )}
    >
      <div className="h-full w-full" aria-label={tSearch('propertyMap')} role="application">
        <MapContainer
          center={[center.lat, center.lon]}
          zoom={12}
          scrollWheelZoom={false}
          className="h-full w-full"
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          <FitBounds bounds={bounds as LatLngBoundsExpression | null} />
          <ZoomTracker onZoomChange={onZoomChange} />
          <MapTileTheme />
          {items.map((item) => {
            if (item.kind === 'point') {
              const p = item.point;
              return (
                <Marker key={p.id} position={[p.lat, p.lon]} icon={markerIcon}>
                  <Popup>
                    <div className="space-y-1">
                      <div className="font-semibold">{p.title ?? t('card.untitled')}</div>
                      <div className="text-sm">
                        {[p.city, p.country].filter(Boolean).join(', ') ||
                          t('card.locationUnavailable')}
                      </div>
                      <div className="text-sm font-medium">
                        {typeof p.price === 'number'
                          ? formatPrice(p.price, p.currency, locale)
                          : t('card.priceOnRequest')}
                      </div>
                    </div>
                  </Popup>
                </Marker>
              );
            }

            const titles = item.points
              .map((p) => p.title ?? t('card.untitled'))
              .filter(Boolean)
              .slice(0, 5);

            return (
              <ClusterMarker
                key={item.id}
                cluster={item}
                zoom={zoom}
                icon={getClusterIcon(
                  item.count,
                  getClusterColor(item.dominantType, item.isMixed)
                )}
              >
                <Popup>
                  <div className="space-y-2">
                    <div className="font-semibold">
                      {t('map.propertiesInArea', { count: item.count })}
                    </div>
                    {titles.length ? (
                      <ul className="list-disc pl-4 text-sm space-y-1">
                        {titles.map((t, idx) => (
                          <li key={`${item.id}-t-${idx}`}>{t}</li>
                        ))}
                      </ul>
                    ) : (
                      <div className="text-sm">{tSearch('mapZoomHint')}</div>
                    )}
                  </div>
                </Popup>
              </ClusterMarker>
            );
          })}
        </MapContainer>
      </div>
    </div>
  );
}
