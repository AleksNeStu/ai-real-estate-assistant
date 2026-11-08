'use client';

import { useState, useMemo, useCallback, useEffect, Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { useTranslations } from 'next-intl';
import {
  Search as SearchIcon,
  MapPin,
  Filter,
  Download,
  RefreshCw,
  AlertCircle,
  Pencil,
} from 'lucide-react';
import { searchProperties, exportPropertiesBySearch, ApiError } from '@/lib/api';
import { SearchResultItem } from '@/lib/types';
import { info, warn } from '@/lib/logger';
import { extractMapPoints, type PropertyMapPoint } from '@/components/search/property-map-utils';
import type { PolygonCoordinates } from '@/components/search/geo-draw-control';
import {
  validatePolygon,
  serializePolygonToUrl,
  deserializePolygonFromUrl,
} from '@/lib/geo-validation';
import { ListingGenerator, PropertyCard } from '@/components/property';
import { RelevanceRating } from '@/components/search/relevance-rating';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { PageHeader } from '@/components/ui/page-header';
import { EmptyState, ErrorState, LoadingState } from '@/components/ui/states';
import dynamic from 'next/dynamic';
import MapControls, {
  type MapFilterOptions,
  DEFAULT_CLUSTER_OPTIONS,
} from '@/components/search/map-controls';
import { SaveSearchButton } from '@/components/search/save-search-button';
import { PresetSelector } from '@/components/search/preset-selector';
import { useTrackSearchDebounced } from '@/hooks/useLeadTracking';
import type { FilterPreset } from '@/lib/types';

const PropertyMap = dynamic(() => import('@/components/search/property-map'), {
  ssr: false,
  loading: () => <div className="h-[420px] w-full bg-muted animate-pulse rounded-lg" />,
});

const PropertyMapboxMap = dynamic(() => import('@/components/search/property-mapbox-map'), {
  ssr: false,
  loading: () => <div className="h-[420px] w-full bg-muted animate-pulse rounded-lg" />,
});

// Example queries for empty state
const EXAMPLE_QUERIES = [
  '2-bedroom apartment under $500,000 in Madrid',
  'House with garden in Krakow',
  'Studio apartment near city center',
  'Luxury apartment with parking in Warsaw',
];

function SearchPageContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const t = useTranslations('search');
  const tCommon = useTranslations('common');
  const tPage = useTranslations('pages.search');
  const { trackSearchDebounced, flushSearch } = useTrackSearchDebounced(1000);

  // A pending search must not be lost when the visitor leaves the page.
  useEffect(() => {
    return () => {
      try {
        flushSearch();
      } catch {
        // Tracking is best-effort — never break navigation over it.
      }
    };
  }, [flushSearch]);

  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<SearchResultItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [requestId, setRequestId] = useState<string | undefined>();
  const [hasSearched, setHasSearched] = useState(false);
  const [minPrice, setMinPrice] = useState<string>('');
  const [maxPrice, setMaxPrice] = useState<string>('');
  const [rooms, setRooms] = useState<string>('');
  const [propertyType, setPropertyType] = useState<string>('');
  const [sortBy, setSortBy] = useState<string>('relevance');
  const [sortOrder, setSortOrder] = useState<string>('desc');
  const [exportFormat, setExportFormat] = useState<string>('csv');
  const [exportColumns, setExportColumns] = useState<string>('');
  const [exportIncludeHeader, setExportIncludeHeader] = useState<boolean>(true);
  const [csvDelimiter, setCsvDelimiter] = useState<string>(',');
  const [csvDecimal, setCsvDecimal] = useState<string>('.');
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<'list' | 'map'>('list');
  const [useMapbox, setUseMapbox] = useState(false);
  const [mapFilterOptions, setMapFilterOptions] = useState<MapFilterOptions>({
    showHeatmap: false,
    heatmapIntensity: 1,
    heatmapMode: 'density',
    showClusters: true,
    clusterOptions: DEFAULT_CLUSTER_OPTIONS,
    priceRange: undefined,
    propertyType: undefined,
  });
  const [enableDrawing, setEnableDrawing] = useState(false);
  const [drawnPolygon, setDrawnPolygon] = useState<PolygonCoordinates[] | null>(null);

  // Handlers for polygon drawing
  const handlePolygonDraw = useCallback(
    (coordinates: PolygonCoordinates[]) => {
      // Validate polygon
      const validation = validatePolygon(coordinates);
      if (!validation.valid) {
        warn('Invalid polygon', { error: validation.error });
        // Still set the polygon but log the issue
        // In production, you might want to show a toast notification
      }

      setDrawnPolygon(coordinates);
      setEnableDrawing(false);

      // Persist to URL
      const params = new URLSearchParams(searchParams.toString());
      if (coordinates[0]) {
        params.set('polygon', serializePolygonToUrl(coordinates[0]));
        router.replace(`?${params.toString()}`, { scroll: false });
      }
    },
    [searchParams, router]
  );

  const handlePolygonClear = useCallback(() => {
    setDrawnPolygon(null);
    setEnableDrawing(false);

    // Remove from URL
    const params = new URLSearchParams(searchParams.toString());
    params.delete('polygon');
    const newUrl = params.toString() ? `?${params.toString()}` : '';
    router.replace(newUrl || window.location.pathname, { scroll: false });
  }, [searchParams, router]);

  // Restore polygon from URL on mount
  useEffect(() => {
    const polygonParam = searchParams.get('polygon');
    if (polygonParam && !drawnPolygon) {
      const coords = deserializePolygonFromUrl(polygonParam);
      if (coords) {
        const validation = validatePolygon(coords);
        if (validation.valid) {
          setDrawnPolygon(coords);
        }
      }
    }
  }, [searchParams]); // eslint-disable-line react-hooks/exhaustive-deps
  // Only run on mount - drawnPolygon intentionally excluded to prevent loops

  // Handle property marker click on map
  const handlePropertyClick = (point: PropertyMapPoint) => {
    // For now, just log the click. Future enhancement: scroll to property in list
    info('Property clicked', { id: point.id, title: point.title });
  };

  const mapPoints = useMemo(() => extractMapPoints(results), [results]);

  const filteredMapPoints = useMemo(() => {
    let points = mapPoints;
    if (mapFilterOptions.priceRange) {
      const [min, max] = mapFilterOptions.priceRange;
      points = points.filter((p) => p.price !== undefined && p.price >= min && p.price <= max);
    }
    return points;
  }, [mapPoints, mapFilterOptions.priceRange]);

  // Filter points by drawn polygon
  const filteredByPolygon = useMemo(() => {
    if (!drawnPolygon || drawnPolygon.length === 0) return filteredMapPoints;

    return filteredMapPoints.filter((point) => {
      // Simple point-in-polygon check using ray casting
      const polygon = drawnPolygon[0]; // First ring
      if (!polygon || polygon.length < 3) return true;

      let inside = false;
      const x = point.lon;
      const y = point.lat;

      for (let i = 0, j = polygon.length - 1; i < polygon.length; j++) {
        const xi = polygon[i][0];
        const yi_coord = polygon[i][1];
        const xj = polygon[j][0];
        const yj_coord = polygon[j][1];

        if (
          yi_coord > y !== yj_coord > y &&
          x < ((xj - xi) * (y - yi_coord)) / (yj_coord - yi_coord) + xi
        ) {
          inside = !inside;
        }
      }

      return inside;
    });
  }, [filteredMapPoints, drawnPolygon]);

  const buildFilters = (): { filters?: Record<string, unknown>; error?: string } => {
    const min = minPrice.trim() ? Number(minPrice) : undefined;
    const max = maxPrice.trim() ? Number(maxPrice) : undefined;
    const minRooms = rooms.trim() ? Number(rooms) : undefined;

    if (min !== undefined && Number.isNaN(min))
      return { error: t('errors.invalidMinPrice') };
    if (max !== undefined && Number.isNaN(max))
      return { error: t('errors.invalidMaxPrice') };
    if (minRooms !== undefined && Number.isNaN(minRooms)) {
      return { error: t('errors.invalidMinRooms') };
    }
    if (min !== undefined && max !== undefined && min > max) {
      return { error: t('errors.minGreaterThanMax') };
    }

    const filters: Record<string, unknown> = {};
    if (min !== undefined) filters['min_price'] = min;
    if (max !== undefined) filters['max_price'] = max;
    if (minRooms !== undefined) filters['rooms'] = minRooms;
    if (propertyType.trim()) filters['property_type'] = propertyType;

    return { filters: Object.keys(filters).length ? filters : undefined };
  };

  const handleSearch = async (e?: React.FormEvent) => {
    e?.preventDefault();
    setLoading(true);
    setError(null);
    setRequestId(undefined);
    setHasSearched(true);
    try {
      if (!query.trim()) {
        setResults([]);
        setError(t('errors.emptyQuery'));
        return;
      }

      const { filters, error: filterError } = buildFilters();
      if (filterError) {
        setResults([]);
        setError(filterError);
        return;
      }

      // Lead tracking: record the search intent (debounced, best-effort).
      try {
        trackSearchDebounced(query.trim(), filters);
      } catch {
        // Tracking must never break the search.
      }

      const response = await searchProperties({
        query,
        sort_by: sortBy as 'relevance' | 'price' | 'price_per_sqm' | 'area_sqm' | 'year_built',
        sort_order: sortOrder as 'asc' | 'desc',
        filters,
      });
      setResults(response.results);
      setViewMode('list');
    } catch (err) {
      setResults([]);
      if (err instanceof ApiError) {
        setError(err.message);
        setRequestId(err.request_id);
      } else {
        setError(t('errors.genericSearch'));
      }
    } finally {
      setLoading(false);
    }
  };

  const handleExport = async () => {
    setExporting(true);
    setExportError(null);
    try {
      if (!query.trim()) {
        setExportError('Please enter a search query.');
        return;
      }

      const { filters, error: filterError } = buildFilters();
      if (filterError) {
        setExportError(filterError);
        return;
      }

      const searchPayload = {
        query,
        limit: Math.max(results.length, 10) || 10,
        sort_by: sortBy as 'relevance' | 'price' | 'price_per_sqm' | 'area_sqm' | 'year_built',
        sort_order: sortOrder as 'asc' | 'desc',
        filters,
      };
      const columns = exportColumns
        .split(',')
        .map((c) => c.trim())
        .filter(Boolean);
      const { filename, blob } = await exportPropertiesBySearch(
        searchPayload,
        exportFormat as 'csv' | 'xlsx' | 'json' | 'md' | 'pdf',
        {
          columns: columns.length ? columns : undefined,
          include_header: exportIncludeHeader,
          csv_delimiter: exportFormat === 'csv' ? csvDelimiter : undefined,
          csv_decimal: exportFormat === 'csv' ? csvDecimal : undefined,
        }
      );
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      if (err instanceof ApiError) {
        setExportError(`${err.message}${err.request_id ? ` (request_id=${err.request_id})` : ''}`);
      } else {
        setExportError(t('errors.exportFailed'));
      }
    } finally {
      setExporting(false);
    }
  };

  const handleExampleQuery = (exampleQuery: string) => {
    setQuery(exampleQuery);
    setTimeout(() => {
      const form = document.querySelector('form[role="search"]') as HTMLFormElement;
      form?.requestSubmit();
    }, 100);
  };

  return (
    <div className="container mx-auto px-4 py-8" aria-live="polite">
      <div className="flex flex-col space-y-8">
        {/* Search Header */}
        <PageHeader title={tPage('title')} description={tPage('description')} />

        {/* Search Bar */}
        <form
          onSubmit={handleSearch}
          className="flex gap-4"
          role="search"
          aria-label={t('searchLabel')}
        >
          <div className="relative flex-1">
            <SearchIcon className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
            <input
              type="text"
              data-testid="search-input"
              placeholder={t('placeholder')}
              className={[
                'w-full rounded-md border border-input bg-background',
                'pl-10 pr-4 py-2 text-sm',
                'placeholder:text-muted-foreground focus-visible:outline-none',
                'focus-visible:outline-2 focus-visible:outline-ring/50',
                'disabled:cursor-not-allowed disabled:opacity-50',
              ].join(' ')}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              aria-label={t('queryLabel')}
              required
              disabled={loading}
            />
          </div>
          <Button
            type="submit"
            data-testid="search-submit"
            disabled={loading || !query.trim()}
            aria-busy={loading ? 'true' : 'false'}
            aria-label={loading ? tCommon('searching') : tCommon('search')}
          >
            {loading ? tCommon('searching') : tCommon('search')}
          </Button>
        </form>

        {/* Filters & Results Layout */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          {/* Sidebar Filters */}
          <div className="space-y-6">
            <Card>
              <CardContent className="p-6">
                <div className="mb-4 flex items-center gap-2 font-semibold">
                  <Filter className="h-4 w-4" aria-hidden="true" /> {t('filters.title')}
                </div>
              <div className="space-y-4">
                <div className="grid grid-cols-1 gap-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label htmlFor="sort-by" className="mb-1 block text-sm font-medium">
                        {t('filters.sortBy')}
                      </label>
                      <select
                        id="sort-by"
                        className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                        value={sortBy}
                        onChange={(e) => setSortBy(e.target.value)}
                        aria-label={t('filters.sortBy')}
                        disabled={loading}
                      >
                        <option value="relevance">{t('sortOptions.relevance')}</option>
                        <option value="price">{t('sortOptions.price')}</option>
                        <option value="price_per_sqm">{t('sortOptions.pricePerSqm')}</option>
                        <option value="area_sqm">{t('sortOptions.area')}</option>
                        <option value="year_built">{t('sortOptions.yearBuilt')}</option>
                      </select>
                    </div>
                    <div>
                      <label htmlFor="sort-order" className="mb-1 block text-sm font-medium">
                        {t('filters.order')}
                      </label>
                      <select
                        id="sort-order"
                        className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                        value={sortOrder}
                        onChange={(e) => setSortOrder(e.target.value)}
                        aria-label={t('filters.order')}
                        disabled={loading}
                      >
                        <option value="desc">{t('orderOptions.descending')}</option>
                        <option value="asc">{t('orderOptions.ascending')}</option>
                      </select>
                    </div>
                  </div>
                  <div>
                    <label htmlFor="min-price" className="mb-1 block text-sm font-medium">
                      {t('filters.minPrice')}
                    </label>
                    <input
                      id="min-price"
                      type="number"
                      inputMode="numeric"
                      min={0}
                      className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                      value={minPrice}
                      onChange={(e) => setMinPrice(e.target.value)}
                      aria-label={t('filters.minPrice')}
                      disabled={loading}
                    />
                  </div>
                  <div>
                    <label htmlFor="max-price" className="mb-1 block text-sm font-medium">
                      {t('filters.maxPrice')}
                    </label>
                    <input
                      id="max-price"
                      type="number"
                      inputMode="numeric"
                      min={0}
                      className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                      value={maxPrice}
                      onChange={(e) => setMaxPrice(e.target.value)}
                      aria-label={t('filters.maxPrice')}
                      disabled={loading}
                    />
                  </div>
                  <div>
                    <label htmlFor="rooms" className="mb-1 block text-sm font-medium">
                      {t('filters.minRooms')}
                    </label>
                    <input
                      id="rooms"
                      type="number"
                      inputMode="numeric"
                      min={0}
                      className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                      value={rooms}
                      onChange={(e) => setRooms(e.target.value)}
                      aria-label={t('filters.minRooms')}
                      disabled={loading}
                    />
                  </div>
                  <div>
                    <label htmlFor="property-type" className="mb-1 block text-sm font-medium">
                      {t('filters.propertyType')}
                    </label>
                    <select
                      id="property-type"
                      className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                      value={propertyType}
                      onChange={(e) => setPropertyType(e.target.value)}
                      aria-label={t('filters.propertyType')}
                      disabled={loading}
                    >
                      <option value="">{t('propertyTypes.any')}</option>
                      <option value="apartment">{t('propertyTypes.apartment')}</option>
                      <option value="house">{t('propertyTypes.house')}</option>
                      <option value="studio">{t('propertyTypes.studio')}</option>
                      <option value="loft">{t('propertyTypes.loft')}</option>
                      <option value="townhouse">{t('propertyTypes.townhouse')}</option>
                      <option value="other">{t('propertyTypes.other')}</option>
                    </select>
                  </div>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      setMinPrice('');
                      setMaxPrice('');
                      setRooms('');
                      setPropertyType('');
                      setSortBy('relevance');
                      setSortOrder('desc');
                    }}
                    aria-label={t('filters.clearFilters')}
                    disabled={loading}
                  >
                    {t('filters.clearFilters')}
                  </Button>
                  <div className="mt-2 grid grid-cols-2 gap-4">
                    <div>
                      <label htmlFor="export-format" className="mb-1 block text-sm font-medium">
                        {t('export.format')}
                      </label>
                      <select
                        id="export-format"
                        className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                        value={exportFormat}
                        onChange={(e) => setExportFormat(e.target.value)}
                        aria-label={t('export.format')}
                        disabled={loading || results.length === 0}
                      >
                        <option value="csv">CSV</option>
                        <option value="xlsx">Excel</option>
                        <option value="json">JSON</option>
                        <option value="md">Markdown</option>
                        <option value="pdf">PDF</option>
                      </select>
                    </div>
                    <div>
                      <label htmlFor="export-columns" className="mb-1 block text-sm font-medium">
                        {t('export.columns')}
                      </label>
                      <input
                        id="export-columns"
                        className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                        value={exportColumns}
                        onChange={(e) => setExportColumns(e.target.value)}
                        placeholder={t('export.columnsPlaceholder')}
                        aria-label={t('export.columns')}
                        disabled={loading}
                      />
                    </div>
                    {exportFormat === 'csv' ? (
                      <div className="col-span-2 grid grid-cols-2 gap-4">
                        <div>
                          <label htmlFor="csv-delimiter" className="mb-1 block text-sm font-medium">
                            {t('export.delimiter')}
                          </label>
                          <select
                            id="csv-delimiter"
                            className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                            value={csvDelimiter}
                            onChange={(e) => setCsvDelimiter(e.target.value)}
                            aria-label={t('export.delimiter')}
                            disabled={loading}
                          >
                            <option value=",">{t('export.delimiterComma')}</option>
                            <option value=";">{t('export.delimiterSemicolon')}</option>
                          </select>
                        </div>
                        <div>
                          <label htmlFor="csv-decimal" className="mb-1 block text-sm font-medium">
                            {t('export.decimalSeparator')}
                          </label>
                          <select
                            id="csv-decimal"
                            className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                            value={csvDecimal}
                            onChange={(e) => setCsvDecimal(e.target.value)}
                            aria-label={t('export.decimalSeparator')}
                            disabled={loading}
                          >
                            <option value=".">{t('export.decimalDot')}</option>
                            <option value=",">{t('export.decimalComma')}</option>
                          </select>
                        </div>
                        <label className="col-span-2 flex items-center gap-2 text-sm">
                          <input
                            type="checkbox"
                            checked={exportIncludeHeader}
                            onChange={(e) => setExportIncludeHeader(e.target.checked)}
                            aria-label={t('export.includeHeader')}
                            disabled={loading}
                          />
                          {t('export.includeHeader')}
                        </label>
                      </div>
                    ) : null}
                    <div className="flex items-end">
                      <Button
                        type="button"
                        size="sm"
                        onClick={handleExport}
                        disabled={exporting || !query.trim() || results.length === 0}
                        aria-label={exporting ? tCommon('exporting') : tCommon('export')}
                      >
                        <Download className="mr-2 h-4 w-4" aria-hidden="true" />
                        {exporting ? tCommon('exporting') : tCommon('export')}
                      </Button>
                    </div>
                  </div>
                  {exportError ? (
                    <div className="text-sm text-destructive" role="alert">
                      {exportError}
                    </div>
                  ) : null}
                </div>
              </div>
              </CardContent>
            </Card>
          </div>

          {/* Results Grid - 4 Mandated States */}
          <div className="md:col-span-3">
            {/* STATE 1: Empty state (zero-data) */}
            {!hasSearched && !loading && !error && (
              <EmptyState
                icon={SearchIcon}
                title={t('emptyState.title')}
                description={t('emptyState.description')}
                action={
                  <div className="flex flex-col items-center gap-2">
                    <p className="text-sm font-medium text-foreground">
                      {t('emptyState.tryExamples')}
                    </p>
                    <div className="flex flex-col items-center gap-1">
                      {EXAMPLE_QUERIES.map((example, idx) => (
                        <button
                          key={idx}
                          type="button"
                          onClick={() => handleExampleQuery(example)}
                          className="text-sm text-primary hover:underline disabled:opacity-50"
                          disabled={loading}
                        >
                          &ldquo;{example}&rdquo;
                        </button>
                      ))}
                    </div>
                    <p className="text-xs text-muted-foreground">{t('emptyState.exportHint')}</p>
                  </div>
                }
              />
            )}

            {/* STATE 2: Loading state */}
            {loading && !hasSearched && (
              <div
                className="space-y-4"
                role="status"
                aria-live="polite"
                aria-label={tCommon('loading')}
              >
                {/* Skeleton results */}
                <LoadingState variant="cards" rows={6} />
                {/* Map placeholder */}
                <div
                  className="h-[420px] w-full bg-muted animate-pulse rounded-lg border border-dashed"
                  aria-hidden="true"
                />
              </div>
            )}

            {/* STATE 3: Error state */}
            {error && !loading && (
              <ErrorState
                title={t('errors.searchFailed')}
                description={error}
                onRetry={() => handleSearch()}
                retryLabel={tCommon('retry')}
                action={
                  requestId ? (
                    <p className="font-mono text-xs text-muted-foreground">
                      Request ID: {requestId}
                    </p>
                  ) : null
                }
              />
            )}

            {/* STATE 4: Populated state */}
            {!loading && hasSearched && !error && (
              <div className="space-y-4">
                {results.length === 0 ? (
                  /* No results sub-state of Populated */
                  <EmptyState
                    icon={MapPin}
                    title={t('results.noResults')}
                    description={t('results.noResultsHint')}
                  />
                ) : (
                  <>
                    <div className="flex items-center justify-between gap-4">
                      <div className="flex items-center gap-4">
                        <div
                          className="inline-flex rounded-md border bg-background p-1"
                          role="group"
                          aria-label={t('view.label')}
                        >
                          <button
                            type="button"
                            onClick={() => setViewMode('list')}
                            className={[
                              'rounded-md px-3 py-1.5 text-sm',
                              viewMode === 'list' ? 'bg-muted font-medium' : 'hover:bg-muted/50',
                              'disabled:opacity-50',
                            ].join(' ')}
                            aria-pressed={viewMode === 'list'}
                            aria-label={t('view.list')}
                          >
                            {t('view.list')}
                          </button>
                          <button
                            type="button"
                            onClick={() => setViewMode('map')}
                            className={[
                              'rounded-md px-3 py-1.5 text-sm',
                              viewMode === 'map' ? 'bg-muted font-medium' : 'hover:bg-muted/50',
                              'disabled:opacity-50',
                            ].join(' ')}
                            aria-pressed={viewMode === 'map'}
                            aria-label={t('view.map')}
                          >
                            {t('view.map')}
                          </button>
                        </div>
                        <SaveSearchButton
                          filters={{
                            query,
                            min_price: minPrice.trim() ? Number(minPrice) : undefined,
                            max_price: maxPrice.trim() ? Number(maxPrice) : undefined,
                            min_rooms: rooms.trim() ? Number(rooms) : undefined,
                            property_type: propertyType.trim() || undefined,
                          }}
                          query={query}
                        />
                        <PresetSelector
                          onPresetSelect={(preset: FilterPreset) => {
                            // Apply preset filters to state
                            const filters = preset.filters;
                            if (filters.min_price !== undefined) {
                              setMinPrice(String(filters.min_price));
                            }
                            if (filters.max_price !== undefined) {
                              setMaxPrice(String(filters.max_price));
                            }
                            if (filters.min_rooms !== undefined) {
                              setRooms(String(filters.min_rooms));
                            }
                            if (filters.property_type !== undefined) {
                              setPropertyType(String(filters.property_type));
                            }
                            // Trigger search with new filters
                            setTimeout(() => {
                              const form = document.querySelector('form');
                              if (form) {
                                form.requestSubmit();
                              }
                            }, 0);
                          }}
                          currentFilters={{
                            min_price: minPrice.trim() ? Number(minPrice) : undefined,
                            max_price: maxPrice.trim() ? Number(maxPrice) : undefined,
                            min_rooms: rooms.trim() ? Number(rooms) : undefined,
                            property_type: propertyType.trim() || undefined,
                          }}
                        />
                      </div>
                      {viewMode === 'map' && (
                        <div className="flex items-center gap-2">
                          <label className="flex items-center gap-2 text-sm">
                            <input
                              type="checkbox"
                              checked={useMapbox}
                              onChange={(e) => setUseMapbox(e.target.checked)}
                              className="h-4 w-4 rounded border-input"
                              aria-label={t('map.useMapbox')}
                            />
                            {t('map.enhanced')}
                          </label>
                          {useMapbox && (
                            <Button
                              type="button"
                              size="sm"
                              variant={enableDrawing ? 'default' : 'outline'}
                              onClick={() => {
                                setEnableDrawing(!enableDrawing);
                                if (enableDrawing) {
                                  setDrawnPolygon(null);
                                }
                              }}
                              aria-label={
                                enableDrawing ? t('map.disableDrawing') : t('map.enableDrawing')
                              }
                            >
                              <Pencil className="h-3 w-3" aria-hidden="true" />
                              {enableDrawing ? t('map.drawing') : t('map.drawArea')}
                            </Button>
                          )}
                          {drawnPolygon && (
                            <Button
                              type="button"
                              size="sm"
                              variant="ghost"
                              onClick={handlePolygonClear}
                              aria-label={t('map.clearArea')}
                            >
                              {t('map.clearArea')}
                            </Button>
                          )}
                        </div>
                      )}
                      <div className="text-sm text-muted-foreground">
                        {t('map.shown', {
                          shown: drawnPolygon ? filteredByPolygon.length : filteredMapPoints.length,
                          total: results.length,
                        })}
                        {drawnPolygon && (
                          <span className="ml-1 text-primary">{t('map.filteredByArea')}</span>
                        )}
                      </div>
                    </div>

                    {viewMode === 'map' ? (
                      <div className="relative">
                        {mapPoints.length ? (
                          useMapbox ? (
                            <>
                              <PropertyMapboxMap
                                points={drawnPolygon ? filteredByPolygon : filteredMapPoints}
                                mapboxToken={process.env.NEXT_PUBLIC_MAPBOX_TOKEN}
                                showHeatmap={mapFilterOptions.showHeatmap}
                                heatmapIntensity={mapFilterOptions.heatmapIntensity}
                                heatmapMode={mapFilterOptions.heatmapMode}
                                showClusters={mapFilterOptions.showClusters}
                                clusterOptions={mapFilterOptions.clusterOptions}
                                enableDrawing={enableDrawing}
                                onMarkerClick={handlePropertyClick}
                                onPolygonDraw={handlePolygonDraw}
                                onPolygonClear={handlePolygonClear}
                              />
                              <MapControls
                                options={mapFilterOptions}
                                onChange={setMapFilterOptions}
                                onZoomIn={() => {
                                  /* Handled by Mapbox */
                                }}
                                onZoomOut={() => {
                                  /* Handled by Mapbox */
                                }}
                                onFitBounds={() => {
                                  /* Handled by Mapbox */
                                }}
                              />
                            </>
                          ) : (
                            <PropertyMap points={filteredMapPoints} />
                          )
                        ) : (
                          <EmptyState
                            icon={MapPin}
                            title={t('map.noMappableResults')}
                            description={t('map.noMappableResultsHint')}
                          />
                        )}
                      </div>
                    ) : (
                      <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
                        {results.map((item, index) => {
                          const prop = item.property;
                          return (
                            <PropertyCard
                              key={`${prop.id ?? 'unknown'}-${index}`}
                              property={prop}
                              footer={
                                <>
                                  {prop.id && <ListingGenerator propertyId={prop.id} compact />}
                                  {prop.id && <RelevanceRating query={query} propertyId={prop.id} />}
                                </>
                              }
                            />
                          );
                        })}
                      </div>
                    )}
                  </>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function SearchPageFallback() {
  return (
    <div className="container mx-auto px-4 py-8">
      <div className="flex flex-col space-y-8">
        <div className="flex flex-col space-y-4">
          <div className="h-9 w-64 bg-muted animate-pulse rounded" />
          <div className="h-5 w-96 bg-muted animate-pulse rounded" />
        </div>
        <div className="flex gap-4">
          <div className="flex-1 h-10 bg-muted animate-pulse rounded" />
          <div className="h-10 w-24 bg-muted animate-pulse rounded" />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          <div className="h-[600px] bg-muted animate-pulse rounded-lg" />
          <div className="md:col-span-3 h-[400px] bg-muted animate-pulse rounded-lg" />
        </div>
      </div>
    </div>
  );
}

export default function SearchPage() {
  return (
    <Suspense fallback={<SearchPageFallback />}>
      <SearchPageContent />
    </Suspense>
  );
}
