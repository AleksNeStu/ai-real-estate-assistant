'use client';

import { useEffect, useRef, useCallback } from 'react';
import { type Map as MapboxMap } from 'mapbox-gl';
import MapboxDraw from '@mapbox/mapbox-gl-draw';
import '@mapbox/mapbox-gl-draw/dist/mapbox-gl-draw.css';

export type PolygonCoordinates = [number, number][]; // [lon, lat] pairs

interface GeoDrawControlProps {
  map: MapboxMap | null;
  enabled?: boolean;
  onPolygonComplete?: (coordinates: PolygonCoordinates[]) => void;
  onDrawDelete?: () => void;
}

// Custom draw styles
const drawStyles = [
  // Polygon fill
  {
    id: 'gl-draw-polygon-fill',
    type: 'fill',
    filter: ['all', ['==', '$type', 'Polygon']],
    paint: {
      'fill-color': 'hsl(var(--chart-1))',
      'fill-outline-color': 'hsl(var(--chart-1))',
      'fill-opacity': 0.15,
    },
  },
  // Polygon outline stroke
  {
    id: 'gl-draw-polygon-stroke',
    type: 'line',
    filter: ['all', ['==', '$type', 'Polygon']],
    layout: {
      'line-cap': 'round',
      'line-join': 'round',
    },
    paint: {
      'line-color': 'hsl(var(--chart-1))',
      'line-width': 2,
    },
  },
  // Vertex points
  {
    id: 'gl-draw-polygon-and-line-vertex-halo-active',
    type: 'circle',
    filter: ['all', ['==', 'meta', 'vertex'], ['==', '$type', 'Point']],
    paint: {
      'circle-radius': 6,
      'circle-color': 'hsl(var(--background))',
    },
  },
  {
    id: 'gl-draw-polygon-and-line-vertex-active',
    type: 'circle',
    filter: ['all', ['==', 'meta', 'vertex'], ['==', '$type', 'Point']],
    paint: {
      'circle-radius': 4,
      'circle-color': 'hsl(var(--chart-1))',
    },
  },
];

export default function GeoDrawControl({
  map,
  enabled = false,
  onPolygonComplete,
  onDrawDelete,
}: GeoDrawControlProps) {
  const drawRef = useRef<MapboxDraw | null>(null);

  const handleDrawCreate = useCallback(
    (e: { features: GeoJSON.Feature[] }) => {
      const feature = e.features[0];
      if (feature && feature.geometry.type === 'Polygon') {
        const coordinates = feature.geometry.coordinates as PolygonCoordinates[];
        onPolygonComplete?.(coordinates);
      }
    },
    [onPolygonComplete]
  );

  const handleDrawDelete = useCallback(() => {
    onDrawDelete?.();
  }, [onDrawDelete]);

  // Initialize draw control
  useEffect(() => {
    if (!map || drawRef.current) return;

    const draw = new MapboxDraw({
      displayControlsDefault: false,
      controls: {
        polygon: true,
        trash: true,
      },
      styles: drawStyles as object[],
    });

    drawRef.current = draw;

    // Add event listeners
    map.on('draw.create', handleDrawCreate);
    map.on('draw.delete', handleDrawDelete);

    return () => {
      if (map && drawRef.current) {
        map.off('draw.create', handleDrawCreate);
        map.off('draw.delete', handleDrawDelete);
        try {
          map.removeControl(drawRef.current);
        } catch {
          // Control may already be removed
        }
        drawRef.current = null;
      }
    };
  }, [map, handleDrawCreate, handleDrawDelete]);

  // Toggle draw control visibility
  useEffect(() => {
    if (!map || !drawRef.current) return;

    if (enabled) {
      try {
        map.addControl(drawRef.current, 'top-left');
      } catch {
        // May already be added
      }
    } else {
      try {
        map.removeControl(drawRef.current);
        // Clear any drawn features
        drawRef.current.deleteAll();
      } catch {
        // May already be removed
      }
    }
  }, [map, enabled]);

  // Expose method to clear drawings
  const clearDrawings = useCallback(() => {
    if (drawRef.current) {
      drawRef.current.deleteAll();
    }
  }, []);

  // Expose via window for external access (optional)
  useEffect(() => {
    if (typeof window !== 'undefined') {
      (window as unknown as { clearMapDrawings: () => void }).clearMapDrawings = clearDrawings;
    }
  }, [clearDrawings]);

  return null; // This component doesn't render anything
}

// Export utility function to check if a point is in a polygon
export function pointInPolygon(lat: number, lon: number, polygon: PolygonCoordinates[]): boolean {
  // Use the first ring of the polygon
  const coords = polygon[0];
  if (!coords || coords.length < 3) return false;

  let inside = false;
  for (let i = 0, j = coords.length - 1; i < coords.length; j = i++) {
    const xi = coords[i][0];
    const yi = coords[i][1];
    const xj = coords[j][0];
    const yj = coords[j][1];

    const intersect = yi > lat !== yj > lat && lon < ((xj - xi) * (lat - yi)) / (yj - yi) + xi;

    if (intersect) inside = !inside;
  }

  return inside;
}
