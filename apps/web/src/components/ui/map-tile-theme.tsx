'use client';

import { useEffect } from 'react';
import { useMap } from 'react-leaflet';

/**
 * The tiles in the two themes.
 *
 * The prototype paints the map through one filter: the tiles are grey, and
 * in the dark theme they are inverted as well, so the map belongs to the
 * page instead of shouting over it. The filter is set on the tile pane
 * itself, because that is the only place Leaflet keeps the raster layer.
 *
 * The theme follows the page: the observer watches the `dark` class on the
 * document element, so the map re-themes itself when the visitor switches -
 * without a re-mount, which would drop the tiles and the markers.
 */
export const LIGHT_TILE_FILTER = 'grayscale(1)';
export const DARK_TILE_FILTER = 'grayscale(1) invert(1) brightness(.9) contrast(.9)';

/**
 * The dark tile filter, applied to the map's tile pane.
 *
 * It renders nothing: it is a child of Leaflet's MapContainer, because that
 * is where the map instance lives.
 */
export function MapTileTheme() {
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
