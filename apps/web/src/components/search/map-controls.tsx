'use client';

import { useState } from 'react';
import { useLocale, useTranslations } from 'next-intl';
import { Layers, Thermometer, MapPin, ZoomIn, ZoomOut, Filter, X } from 'lucide-react';

import { formatCompactPrice } from '@/lib/format';

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
  /** The currency the listings are priced in - the bands speak in it. */
  currency?: string;
  className?: string;
}

export default function MapControls({
  options,
  onChange,
  onZoomIn,
  onZoomOut,
  onFitBounds,
  currency,
  className = '',
}: MapControlsProps) {
  const [showAdvanced, setShowAdvanced] = useState(false);
  const t = useTranslations('search.mapControls');
  const tSearch = useTranslations('search');
  const tTypes = useTranslations('search.propertyTypes');
  const tFilters = useTranslations('search.filters');
  const locale = useLocale();

  /**
   * The bands used to print a dollar sign, so a Polish market was filtered
   * by dollars. The amounts are now the listing currency.
   */
  const amount = (value: number): string => formatCompactPrice(value, currency, locale);

  return (
    <div
      className={`absolute top-4 right-4 z-10 flex flex-col gap-2 ${className}`}
      role="group"
      aria-label={t('controls')}
    >
      {/* Basic zoom controls */}
      <div className="flex flex-col gap-1 rounded-lg border bg-background shadow-sm">
        <button
          type="button"
          onClick={onZoomIn}
          className="p-2 hover:bg-muted rounded-t-lg transition-colors focus-visible:outline-none focus-visible:outline-2 focus-visible:outline-ring/50"
          aria-label={t('zoomIn')}
          title={t('zoomIn')}
        >
          <ZoomIn className="h-4 w-4" aria-hidden="true" />
        </button>
        <button
          type="button"
          onClick={onZoomOut}
          className="p-2 hover:bg-muted rounded-b-lg transition-colors focus-visible:outline-none focus-visible:outline-2 focus-visible:outline-ring/50"
          aria-label={t('zoomOut')}
          title={t('zoomOut')}
        >
          <ZoomOut className="h-4 w-4" aria-hidden="true" />
        </button>
      </div>

      {/* Fit bounds */}
      <button
        type="button"
        onClick={onFitBounds}
        className="p-2 rounded-lg border bg-background shadow-sm hover:bg-muted transition-colors focus-visible:outline-none focus-visible:outline-2 focus-visible:outline-ring/50"
        aria-label={t('fitBounds')}
        title={t('fitAll')}
      >
        <MapPin className="h-4 w-4" aria-hidden="true" />
      </button>

      {/* Advanced filters toggle */}
      <button
        type="button"
        onClick={() => setShowAdvanced(!showAdvanced)}
        className="p-2 rounded-lg border bg-background shadow-sm hover:bg-muted transition-colors"
        aria-label={t('toggleFilters')}
        aria-pressed={showAdvanced}
        title={t('mapFilters')}
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
          aria-label={t('mapFilters')}
        >
          <div className="flex items-center gap-2 font-semibold text-sm">
            <Layers className="h-4 w-4" aria-hidden="true" />
            {t('mapOptions')}
          </div>

          {/* Heatmap toggle */}
          <label className="flex items-center justify-between cursor-pointer">
            <span className="text-sm flex items-center gap-2">
              <Thermometer className="h-4 w-4" aria-hidden="true" />
              {t('heatmap')}
            </span>
            <input
              type="checkbox"
              checked={options.showHeatmap}
              onChange={(e) => onChange({ ...options, showHeatmap: e.target.checked })}
              className="w-4 h-4 rounded border-border"
              aria-label={t('toggleHeatmap')}
            />
          </label>

          {/* Heatmap mode selector */}
          {options.showHeatmap && (
            <div className="space-y-1 pl-6">
              <label htmlFor="heatmap-mode" className="text-xs text-muted-foreground">
                {t('mode')}
              </label>
              <select
                id="heatmap-mode"
                value={options.heatmapMode || 'density'}
                onChange={(e) =>
                  onChange({ ...options, heatmapMode: e.target.value as HeatmapMode })
                }
                className="w-full text-sm rounded border border-input bg-background px-2 py-1"
                aria-label={t('heatmapMode')}
              >
                <option value="density">{t('density')}</option>
                <option value="price">{t('price')}</option>
                <option value="price_per_sqm">{t('pricePerSqm')}</option>
                <option value="yield">{t('yield')}</option>
              </select>
            </div>
          )}

          {/* Heatmap intensity */}
          {options.showHeatmap && (
            <div className="space-y-1 pl-6">
              <label htmlFor="heatmap-intensity" className="text-xs text-muted-foreground">
                {t('intensity', { value: options.heatmapIntensity })}
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
                aria-label={t('heatmapIntensity')}
              />
            </div>
          )}

          {/* Clusters toggle */}
          <label className="flex items-center justify-between cursor-pointer">
            <span className="text-sm">{t('clusters')}</span>
            <input
              type="checkbox"
              checked={options.showClusters}
              onChange={(e) => onChange({ ...options, showClusters: e.target.checked })}
              className="w-4 h-4 rounded border-border"
              aria-label={t('toggleClusters')}
            />
          </label>

          {/* Cluster settings - shown when clusters enabled */}
          {options.showClusters && (
            <div className="space-y-2 pl-6">
              {/* Cluster size slider */}
              <div className="space-y-1">
                <label htmlFor="cluster-size" className="text-xs text-muted-foreground">
                  {t('clusterSizeValue', {
                    size: options.clusterOptions?.cellSizePx ?? DEFAULT_CLUSTER_OPTIONS.cellSizePx,
                  })}
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
                  aria-label={t('clusterSize')}
                />
              </div>

              {/* Max zoom for clustering slider */}
              <div className="space-y-1">
                <label htmlFor="cluster-max-zoom" className="text-xs text-muted-foreground">
                  {t('maxZoomValue', {
                    zoom:
                      options.clusterOptions?.maxZoomForClustering ??
                      DEFAULT_CLUSTER_OPTIONS.maxZoomForClustering,
                  })}
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
                  aria-label={t('maxZoom')}
                />
              </div>
            </div>
          )}

          {/* Quick filters */}
          <div className="space-y-2 pt-2 border-t">
            <div className="text-xs font-medium text-muted-foreground">{t('priceFilter')}</div>
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => onChange({ ...options, priceRange: [0, 300000] })}
                className="text-xs px-2 py-1 rounded border hover:bg-muted transition-colors"
                aria-label={t('filterUnder300k', { amount: amount(300000) })}
              >
                {t('under300k', { amount: amount(300000) })}
              </button>
              <button
                type="button"
                onClick={() => onChange({ ...options, priceRange: [300000, 600000] })}
                className="text-xs px-2 py-1 rounded border hover:bg-muted transition-colors"
                aria-label={t('filter300k600k', {
                  from: amount(300000),
                  to: amount(600000),
                })}
              >
                {t('range300k600k', { from: amount(300000), to: amount(600000) })}
              </button>
              <button
                type="button"
                onClick={() => onChange({ ...options, priceRange: [600000, 1000000] })}
                className="text-xs px-2 py-1 rounded border hover:bg-muted transition-colors"
                aria-label={t('filter600k1M', {
                  from: amount(600000),
                  to: amount(1000000),
                })}
              >
                {t('range600k1M', { from: amount(600000), to: amount(1000000) })}
              </button>
              <button
                type="button"
                onClick={() => onChange({ ...options, priceRange: undefined })}
                className="text-xs px-2 py-1 rounded border hover:bg-muted transition-colors"
                aria-label={tSearch('clearPriceFilter')}
              >
                {t('allPrices')}
              </button>
            </div>
          </div>

          {/* Property type filter */}
          <div className="space-y-2 pt-2 border-t">
            <div className="text-xs font-medium text-muted-foreground">
              {tFilters('propertyType')}
            </div>
            <select
              value={options.propertyType || ''}
              onChange={(e) => onChange({ ...options, propertyType: e.target.value || undefined })}
              className="w-full text-sm rounded border border-input bg-background px-2 py-1"
              aria-label={tSearch('filterByPropertyType')}
            >
              <option value="">{t('allTypes')}</option>
              <option value="apartment">{tTypes('apartment')}</option>
              <option value="house">{tTypes('house')}</option>
              <option value="studio">{tTypes('studio')}</option>
              <option value="loft">{tTypes('loft')}</option>
              <option value="townhouse">{tTypes('townhouse')}</option>
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
            aria-label={t('resetFilters')}
          >
            {t('resetAll')}
          </button>
        </div>
      )}
    </div>
  );
}
