'use client';

import { useEffect, useMemo } from 'react';
import { type LatLngBoundsExpression } from 'leaflet';
import { MapContainer, Marker, TileLayer, useMap } from 'react-leaflet';

import { MapTileTheme } from '@/components/ui/map-tile-theme';
import { pinLabel, pricePin } from '@/lib/map-pin';

/**
 * The map of the hero instrument: the matches, on the map they sit on.
 *
 * It is the same primitive the search page uses - Leaflet, the OpenStreetMap
 * raster tiles, the house tile theme - so the landing shows the product
 * rather than a picture of it. The README promises a map on the landing
 * ("a parsed query, a map and three priced rows"), and until now the panel
 * was a hand-drawn grid: the claim and the rendering disagreed.
 *
 * The tiles need no key and no account, so a self-hoster gets a working map
 * out of the box, exactly as the search page already does.
 */

export type HeroMapPoint = {
  id: string;
  lat: number;
  lon: number;
  price?: number;
  currency?: string;
};

function FitBounds({ bounds }: { bounds: LatLngBoundsExpression | null }) {
  const map = useMap();
  useEffect(() => {
    if (!bounds) return;
    map.fitBounds(bounds, { padding: [28, 28] });
  }, [bounds, map]);
  return null;
}

/**
 * The pin is the price, and the price is the price the row below shows.
 *
 * The pin itself lives in `@/lib/map-pin`, because the search map draws the
 * same pin: one map, one pin, one spelling of a price.
 */

export default function HeroMap({
  points,
  className,
}: {
  points: HeroMapPoint[];
  className?: string;
}) {
  const center = useMemo<[number, number]>(() => {
    if (points.length === 0) return [50.0614, 19.9366]; // Kraków, the demo's city
    const lat = points.reduce((sum, p) => sum + p.lat, 0) / points.length;
    const lon = points.reduce((sum, p) => sum + p.lon, 0) / points.length;
    return [lat, lon];
  }, [points]);

  const bounds = useMemo<LatLngBoundsExpression | null>(() => {
    if (points.length === 0) return null;
    const lats = points.map((p) => p.lat);
    const lons = points.map((p) => p.lon);
    return [
      [Math.min(...lats), Math.min(...lons)],
      [Math.max(...lats), Math.max(...lons)],
    ];
  }, [points]);

  const icons = useMemo(
    () =>
      points.map((point, index) =>
        pricePin(pinLabel(point.price, point.currency ?? 'PLN'), index === 0)
      ),
    [points]
  );

  return (
    <MapContainer
      center={center}
      zoom={12}
      scrollWheelZoom={false}
      zoomControl={false}
      attributionControl={false}
      className={className}
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <FitBounds bounds={bounds} />
      <MapTileTheme />
      {points.map((point, index) => (
        <Marker key={point.id} position={[point.lat, point.lon]} icon={icons[index]} />
      ))}
    </MapContainer>
  );
}
