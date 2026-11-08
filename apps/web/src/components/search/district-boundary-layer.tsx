'use client';

import { useEffect, useRef } from 'react';
import type { Map as MapboxMap } from 'mapbox-gl';
import type { DistrictStats, DistrictBoundary } from '@/lib/district-aggregation';
import { getDistrictColor } from '@/lib/district-aggregation';
import { DISTRICT_LAYER } from '@/lib/palette';

interface DistrictBoundaryLayerProps {
  map: MapboxMap | null;
  districts: DistrictBoundary[];
  stats: DistrictStats[];
  visible?: boolean;
  showLabels?: boolean;
  onDistrictClick?: (districtId: string) => void;
}

const SOURCE_ID = 'districts-source';
const FILL_LAYER_ID = 'districts-fill';
const LINE_LAYER_ID = 'districts-line';
const LABELS_SOURCE_ID = 'districts-labels-source';
const LABELS_LAYER_ID = 'districts-labels';

export default function DistrictBoundaryLayer({
  map,
  districts,
  stats,
  visible = true,
  showLabels = true,
  onDistrictClick,
}: DistrictBoundaryLayerProps) {
  const clickHandlerRef = useRef<((e: unknown) => void) | null>(null);
  const mouseEnterHandlerRef = useRef<(() => void) | null>(null);
  const mouseLeaveHandlerRef = useRef<(() => void) | null>(null);

  // Calculate max price for color scaling
  const maxPrice = Math.max(...stats.map((s) => s.avgPrice ?? 0).filter((p) => p > 0), 1);

  // Create GeoJSON from districts
  useEffect(() => {
    if (!map || !map.isStyleLoaded()) return;

    // Remove existing layers and sources
    if (map.getLayer(LABELS_LAYER_ID)) {
      map.removeLayer(LABELS_LAYER_ID);
    }
    if (map.getLayer(LINE_LAYER_ID)) {
      map.removeLayer(LINE_LAYER_ID);
    }
    if (map.getLayer(FILL_LAYER_ID)) {
      map.removeLayer(FILL_LAYER_ID);
    }
    if (map.getSource(LABELS_SOURCE_ID)) {
      map.removeSource(LABELS_SOURCE_ID);
    }
    if (map.getSource(SOURCE_ID)) {
      map.removeSource(SOURCE_ID);
    }

    if (!visible || districts.length === 0) return;

    // Create GeoJSON FeatureCollection
    const geojson: GeoJSON.FeatureCollection = {
      type: 'FeatureCollection',
      features: districts.map((district) => {
        const districtStats = stats.find((s) => s.name === district.name);
        const color = getDistrictColor(districtStats?.avgPrice ?? null, maxPrice);

        return {
          type: 'Feature' as const,
          properties: {
            id: district.id,
            name: district.name,
            color,
            count: districtStats?.count ?? 0,
            avgPrice: districtStats?.avgPrice,
          },
          geometry: {
            type: 'Polygon' as const,
            coordinates: [district.polygon],
          },
        };
      }),
    };

    // Add source
    map.addSource(SOURCE_ID, {
      type: 'geojson',
      data: geojson,
    });

    // Add fill layer
    map.addLayer({
      id: FILL_LAYER_ID,
      type: 'fill',
      source: SOURCE_ID,
      paint: {
        'fill-color': ['get', 'color'],
        'fill-opacity': 0.6,
      },
    });

    // Add line layer
    map.addLayer({
      id: LINE_LAYER_ID,
      type: 'line',
      source: SOURCE_ID,
      paint: {
        'line-color': DISTRICT_LAYER.line,
        'line-width': 1.5,
      },
    });

    // Add labels if enabled
    if (showLabels) {
      const labelsGeojson: GeoJSON.FeatureCollection = {
        type: 'FeatureCollection',
        features: districts.map((district) => ({
          type: 'Feature' as const,
          properties: {
            name: district.name,
          },
          geometry: {
            type: 'Point' as const,
            coordinates: district.center,
          },
        })),
      };

      map.addSource(LABELS_SOURCE_ID, {
        type: 'geojson',
        data: labelsGeojson,
      });

      map.addLayer({
        id: LABELS_LAYER_ID,
        type: 'symbol',
        source: LABELS_SOURCE_ID,
        layout: {
          'text-field': ['get', 'name'],
          'text-font': ['Open Sans Semibold', 'Arial Unicode MS Bold'],
          'text-size': 11,
          'text-anchor': 'center',
        },
        paint: {
          'text-color': DISTRICT_LAYER.label,
          'text-halo-color': DISTRICT_LAYER.halo,
          'text-halo-width': 1.5,
        },
      });
    }

    // Add click handler
    clickHandlerRef.current = (e: unknown) => {
      const event = e as { features?: GeoJSON.Feature[]; lngLat?: { lng: number; lat: number } };
      if (!event.features || event.features.length === 0) return;

      const feature = event.features[0];
      const districtId = feature.properties?.id as string | undefined;

      if (districtId && onDistrictClick) {
        onDistrictClick(districtId);
      }
    };

    map.on('click', FILL_LAYER_ID, clickHandlerRef.current);

    // Change cursor on hover
    mouseEnterHandlerRef.current = () => {
      map.getCanvas().style.cursor = 'pointer';
    };
    map.on('mouseenter', FILL_LAYER_ID, mouseEnterHandlerRef.current);

    mouseLeaveHandlerRef.current = () => {
      map.getCanvas().style.cursor = '';
    };
    map.on('mouseleave', FILL_LAYER_ID, mouseLeaveHandlerRef.current);

    return () => {
      if (map) {
        if (clickHandlerRef.current) {
          map.off('click', FILL_LAYER_ID, clickHandlerRef.current as (e: unknown) => void);
        }
        if (mouseEnterHandlerRef.current) {
          map.off('mouseenter', FILL_LAYER_ID, mouseEnterHandlerRef.current);
        }
        if (mouseLeaveHandlerRef.current) {
          map.off('mouseleave', FILL_LAYER_ID, mouseLeaveHandlerRef.current);
        }

        try {
          if (map.getLayer(LABELS_LAYER_ID)) {
            map.removeLayer(LABELS_LAYER_ID);
          }
          if (map.getLayer(LINE_LAYER_ID)) {
            map.removeLayer(LINE_LAYER_ID);
          }
          if (map.getLayer(FILL_LAYER_ID)) {
            map.removeLayer(FILL_LAYER_ID);
          }
          if (map.getSource(LABELS_SOURCE_ID)) {
            map.removeSource(LABELS_SOURCE_ID);
          }
          if (map.getSource(SOURCE_ID)) {
            map.removeSource(SOURCE_ID);
          }
        } catch {
          // Layers may already be removed
        }
      }
    };
  }, [map, districts, stats, visible, showLabels, maxPrice, onDistrictClick]);

  return null;
}
