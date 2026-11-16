'use client';

import { useEffect, useMemo } from 'react';
import { divIcon, type LatLngBoundsExpression } from 'leaflet';
import { MapContainer, Marker, TileLayer, useMap } from 'react-leaflet';

import { MapTileTheme } from '@/components/ui/map-tile-theme';
import { formatMapPinPrice } from '@/lib/format';

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
 * The pin's label: the price, in the same spelling the row below prints it.
 *
 * The rows format the price with the Polish locale (the market's own
 * spelling), so the chip does the same — a pin that reads "2 100 zł" next to
 * a row that reads "2 100 zł" is one price, one spelling.
 */
function pinLabel(price?: number, currency = 'PLN', locale = 'pl-PL'): string {
  return formatMapPinPrice(price, currency, locale);
}

/**
 * The pin is the price, and the price is the price the row below shows.
 *
 * The chip used to print the number in thousands with no magnitude check, so
 * 322 000 zł read as "322k" and 4 100 zł read as "4k" next to a row that
 * said "4 100 zł". Carrying the currency into the chip was not enough: a
 * 2 100 zł listing still read as "2.1K", which is a different price. The
 * chip prints the price the row prints, and only shortens it when the number
 * is genuinely too long — the same rule the search map's popup uses.
 */
function pricePin(
  label: string,
  highlighted: boolean
): ReturnType<typeof divIcon> {
  const background = highlighted ? 'hsl(var(--foreground))' : 'hsl(var(--background))';
  const color = highlighted ? 'hsl(var(--background))' : 'hsl(var(--foreground))';
  const border = highlighted ? 'hsl(var(--foreground))' : 'hsl(var(--border))';

  return divIcon({
    className: '',
    html: `<div style="transform:translate(-50%,-50%);display:inline-flex;align-items:center;height:22px;padding:0 9px;border-radius:9999px;border:1px solid ${border};background:${background};color:${color};font-family:var(--font-mono),ui-monospace,monospace;font-size:11px;line-height:1;white-space:nowrap;box-shadow:0 2px 8px hsl(var(--foreground) / 0.28)">${label}</div>`,
    iconSize: [0, 0],
    iconAnchor: [0, 0],
  });
}

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
