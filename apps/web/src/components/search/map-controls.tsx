'use client';

import { useState } from 'react';
import { Layers, Thermometer, MapPin, ZoomIn, ZoomOut, Filter, X } from 'lucide-react';
import type { HeatmapMode } from './property-map-utils';

export interface ClusterOptions {
  cellSizePx: number;
  maxZoomForClustering: number;
}

export const DEFAULT_CLUSTER_OPTIONS: ClusterOptions = {
  cellSizePx: 60,
  maxZoomForClustering: 15,
};

export interface MapFilterOptions {
  showHeatmap: boolean;
  heatmapIntensity: number;
  heatmapMode: HeatmapMode;
  showClusters: boolean;
  clusterOptions: ClusterOptions;
  priceRange?: [number, number];
  propertyType?: string;
}

interface MapControlsProps {
  options: MapFilterOptions;
  onChange: (options: MapFilterOptions) => void;
  onZoomIn: () => void;
  onZoomOut: () => void;
  onFitBounds: () => void;
  className?: string;
}

export default function MapControls({
  options,
  onChange,
  onZoomIn,
  onZoomOut,
  onFitBounds,
  className = '',
}: MapControlsProps) {
  const [showAdvanced, setShowAdvanced] = useState(false);

  return (
    <div
      className={`absolute top-4 right-4 z-10 flex flex-col gap-2 ${className}`}
      role="group"
      aria-label="Map controls"
    >
      {/* Basic zoom controls */}
      <div className="flex flex-col gap-1 rounded-lg border bg-background shadow-sm">
        <button
          type="button"
          onClick={onZoomIn}
          className="p-2 hover:bg-muted rounded-t-lg transition-colors focus-visible:outline-none focus-visible:outline-2 focus-visible:outline-ring/50"
          aria-label="Zoom in"
          title="Zoom in"
        >
          <ZoomIn className="h-4 w-4" aria-hidden="true" />
        </button>
        <button
          type="button"
          onClick={onZoomOut}
          className="p-2 hover:bg-muted rounded-b-lg transition-colors focus-visible:outline-none focus-visible:outline-2 focus-visible:outline-ring/50"
          aria-label="Zoom out"
          title="Zoom out"
        >
          <ZoomOut className="h-4 w-4" aria-hidden="true" />
        </button>
      </div>

      {/* Fit bounds */}
      <button
        type="button"
        onClick={onFitBounds}
        className="p-2 rounded-lg border bg-background shadow-sm hover:bg-muted transition-colors focus-visible:outline-none focus-visible:outline-2 focus-visible:outline-ring/50"
        aria-label="Fit bounds"
        title="Fit all properties"
      >
        <MapPin className="h-4 w-4" aria-hidden="true" />
      </button>

      {/* Advanced filters toggle */}
      <button
        type="button"
        onClick={() => setShowAdvanced(!showAdvanced)}
        className="p-2 rounded-lg border bg-background shadow-sm hover:bg-muted transition-colors"
        aria-label="Toggle map filters"
        aria-pressed={showAdvanced}
        title="Map filters"
      >
        {showAdvanced ? (
          <X className="h-4 w-4" aria-hidden="true" />
        ) : (
          <Filter className="h-4 w-4" aria-hidden="true" />
        )}
      </button>

      {/* Advanced controls panel */}
      {showAdvanced && (
        <div
          className="rounded-lg border bg-background shadow-sm p-3 w-56 space-y-3"
          role="dialog"
          aria-label="Map filters"
        >
          <div className="flex items-center gap-2 font-semibold text-sm">
            <Layers className="h-4 w-4" aria-hidden="true" />
            Map Options
          </div>

          {/* Heatmap toggle */}
          <label className="flex items-center justify-between cursor-pointer">
            <span className="text-sm flex items-center gap-2">
              <Thermometer className="h-4 w-4" aria-hidden="true" />
              Heatmap
            </span>
            <input
              type="checkbox"
              checked={options.showHeatmap}
              onChange={(e) => onChange({ ...options, showHeatmap: e.target.checked })}
              className="w-4 h-4 rounded border-border"
              aria-label="Toggle heatmap"
            />
          </label>

          {/* Heatmap mode selector */}
          {options.showHeatmap && (
            <div className="space-y-1 pl-6">
              <label htmlFor="heatmap-mode" className="text-xs text-muted-foreground">
                Mode
              </label>
              <select
                id="heatmap-mode"
                value={options.heatmapMode || 'density'}
                onChange={(e) =>
                  onChange({ ...options, heatmapMode: e.target.value as HeatmapMode })
                }
                className="w-full text-sm rounded border border-input bg-background px-2 py-1"
                aria-label="Heatmap mode"
              >
                <option value="density">Density</option>
                <option value="price">Price</option>
                <option value="price_per_sqm">Price/m²</option>
                <option value="yield">Yield</option>
              </select>
            </div>
          )}

          {/* Heatmap intensity */}
          {options.showHeatmap && (
            <div className="space-y-1 pl-6">
              <label htmlFor="heatmap-intensity" className="text-xs text-muted-foreground">
                Intensity: {options.heatmapIntensity}
              </label>
              <input
                id="heatmap-intensity"
                type="range"
                min="0.1"
                max="3"
                step="0.1"
                value={options.heatmapIntensity}
                onChange={(e) =>
                  onChange({ ...options, heatmapIntensity: parseFloat(e.target.value) })
                }
                className="w-full h-2 bg-muted rounded-lg appearance-none cursor-pointer"
                aria-label="Heatmap intensity"
              />
            </div>
          )}

          {/* Clusters toggle */}
          <label className="flex items-center justify-between cursor-pointer">
            <span className="text-sm">Clusters</span>
            <input
              type="checkbox"
              checked={options.showClusters}
              onChange={(e) => onChange({ ...options, showClusters: e.target.checked })}
              className="w-4 h-4 rounded border-border"
              aria-label="Toggle clusters"
            />
          </label>

          {/* Cluster settings - shown when clusters enabled */}
          {options.showClusters && (
            <div className="space-y-2 pl-6">
              {/* Cluster size slider */}
              <div className="space-y-1">
                <label htmlFor="cluster-size" className="text-xs text-muted-foreground">
                  Cluster Size:{' '}
                  {options.clusterOptions?.cellSizePx ?? DEFAULT_CLUSTER_OPTIONS.cellSizePx}px
                </label>
                <input
                  id="cluster-size"
                  type="range"
                  min="20"
                  max="100"
                  step="5"
                  value={options.clusterOptions?.cellSizePx ?? DEFAULT_CLUSTER_OPTIONS.cellSizePx}
                  onChange={(e) =>
                    onChange({
                      ...options,
                      clusterOptions: {
                        ...(options.clusterOptions ?? DEFAULT_CLUSTER_OPTIONS),
                        cellSizePx: parseInt(e.target.value),
                      },
                    })
                  }
                  className="w-full h-2 bg-muted rounded-lg appearance-none cursor-pointer"
                  aria-label="Cluster size"
                />
              </div>

              {/* Max zoom for clustering slider */}
              <div className="space-y-1">
                <label htmlFor="cluster-max-zoom" className="text-xs text-muted-foreground">
                  Max Zoom:{' '}
                  {options.clusterOptions?.maxZoomForClustering ??
                    DEFAULT_CLUSTER_OPTIONS.maxZoomForClustering}
                </label>
                <input
                  id="cluster-max-zoom"
                  type="range"
                  min="12"
                  max="18"
                  step="1"
                  value={
                    options.clusterOptions?.maxZoomForClustering ??
                    DEFAULT_CLUSTER_OPTIONS.maxZoomForClustering
                  }
                  onChange={(e) =>
                    onChange({
                      ...options,
                      clusterOptions: {
                        ...(options.clusterOptions ?? DEFAULT_CLUSTER_OPTIONS),
                        maxZoomForClustering: parseInt(e.target.value),
                      },
                    })
                  }
                  className="w-full h-2 bg-muted rounded-lg appearance-none cursor-pointer"
                  aria-label="Max zoom for clustering"
                />
              </div>
            </div>
          )}

          {/* Quick filters */}
          <div className="space-y-2 pt-2 border-t">
            <div className="text-xs font-medium text-muted-foreground">Price Filter</div>
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => onChange({ ...options, priceRange: [0, 300000] })}
                className="text-xs px-2 py-1 rounded border hover:bg-muted transition-colors"
                aria-label="Filter under 300k"
              >
                Under $300k
              </button>
              <button
                type="button"
                onClick={() => onChange({ ...options, priceRange: [300000, 600000] })}
                className="text-xs px-2 py-1 rounded border hover:bg-muted transition-colors"
                aria-label="Filter 300k-600k"
              >
                $300k-$600k
              </button>
              <button
                type="button"
                onClick={() => onChange({ ...options, priceRange: [600000, 1000000] })}
                className="text-xs px-2 py-1 rounded border hover:bg-muted transition-colors"
                aria-label="Filter 600k-1M"
              >
                $600k-$1M
              </button>
              <button
                type="button"
                onClick={() => onChange({ ...options, priceRange: undefined })}
                className="text-xs px-2 py-1 rounded border hover:bg-muted transition-colors"
                aria-label="Clear price filter"
              >
                All Prices
              </button>
            </div>
          </div>

          {/* Property type filter */}
          <div className="space-y-2 pt-2 border-t">
            <div className="text-xs font-medium text-muted-foreground">Property Type</div>
            <select
              value={options.propertyType || ''}
              onChange={(e) => onChange({ ...options, propertyType: e.target.value || undefined })}
              className="w-full text-sm rounded border border-input bg-background px-2 py-1"
              aria-label="Filter by property type"
            >
              <option value="">All Types</option>
              <option value="apartment">Apartment</option>
              <option value="house">House</option>
              <option value="studio">Studio</option>
              <option value="loft">Loft</option>
              <option value="townhouse">Townhouse</option>
            </select>
          </div>

          {/* Reset button */}
          <button
            type="button"
            onClick={() =>
              onChange({
                showHeatmap: false,
                heatmapIntensity: 1,
                heatmapMode: 'density',
                showClusters: true,
                clusterOptions: DEFAULT_CLUSTER_OPTIONS,
                priceRange: undefined,
                propertyType: undefined,
              })
            }
            className="w-full text-xs px-2 py-1 rounded border border-destructive text-destructive hover:bg-destructive/10 transition-colors"
            aria-label="Reset all filters"
          >
            Reset All
          </button>
        </div>
      )}
    </div>
  );
}
