'use client';

import { useState, useMemo, useCallback, useEffect, Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
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
import { HeartButton, ListingGenerator } from '@/components/property';
import { RelevanceRating } from '@/components/search/relevance-rating';
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
      return { error: 'Min price must be a valid number.' };
    if (max !== undefined && Number.isNaN(max))
      return { error: 'Max price must be a valid number.' };
    if (minRooms !== undefined && Number.isNaN(minRooms)) {
      return { error: 'Minimum rooms must be a valid number.' };
    }
    if (min !== undefined && max !== undefined && min > max) {
      return { error: 'Min price cannot be greater than max price.' };
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
        setError('Please enter a search query.');
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
        setError('Failed to perform search. Please try again.');
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
        setExportError('Failed to export. Please try again.');
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
        <div className="flex flex-col space-y-4">
          <h1 className="text-3xl font-bold tracking-tight">Find Your Property</h1>
          <p className="text-muted-foreground">
            Search across thousands of listings using AI-powered semantic search.
          </p>
        </div>

        {/* Search Bar */}
        <form
          onSubmit={handleSearch}
          className="flex gap-4"
          role="search"
          aria-label="Property search"
        >
          <div className="relative flex-1">
            <SearchIcon className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
            <input
              type="text"
              data-testid="search-input"
              placeholder="Describe what you're looking for (e.g., 2-bed apartment under $500k)..."
              className={[
                'w-full rounded-md border border-input bg-background',
                'pl-10 pr-4 py-2 text-sm ring-offset-background',
                'placeholder:text-muted-foreground focus-visible:outline-none',
                'focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
                'disabled:cursor-not-allowed disabled:opacity-50',
              ].join(' ')}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              aria-label="Search query"
              required
              disabled={loading}
            />
          </div>
          <button
            type="submit"
            data-testid="search-submit"
            disabled={loading || !query.trim()}
            className={[
              'inline-flex items-center justify-center rounded-md bg-primary px-8',
              'text-sm font-medium text-primary-foreground shadow transition-colors',
              'hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring',
              'disabled:pointer-events-none disabled:opacity-50',
            ].join(' ')}
            aria-busy={loading ? 'true' : 'false'}
            aria-label={loading ? 'Searching' : 'Search'}
          >
            {loading ? 'Searching...' : 'Search'}
          </button>
        </form>

        {/* Filters & Results Layout */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          {/* Sidebar Filters */}
          <div className="space-y-6">
            <div className="rounded-lg border bg-card text-card-foreground shadow-sm p-6">
              <div className="flex items-center gap-2 font-semibold mb-4">
                <Filter className="h-4 w-4" /> Filters
              </div>
              <div className="space-y-4">
                <div className="grid grid-cols-1 gap-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label htmlFor="sort-by" className="block text-sm font-medium mb-1">
                        Sort By
                      </label>
                      <select
                        id="sort-by"
                        className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                        value={sortBy}
                        onChange={(e) => setSortBy(e.target.value)}
                        aria-label="Sort by"
                        disabled={loading}
                      >
                        <option value="relevance">Relevance</option>
                        <option value="price">Price</option>
                        <option value="price_per_sqm">Price per m²</option>
                        <option value="area_sqm">Area (m²)</option>
                        <option value="year_built">Year Built</option>
                      </select>
                    </div>
                    <div>
                      <label htmlFor="sort-order" className="block text-sm font-medium mb-1">
                        Order
                      </label>
                      <select
                        id="sort-order"
                        className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                        value={sortOrder}
                        onChange={(e) => setSortOrder(e.target.value)}
                        aria-label="Sort order"
                        disabled={loading}
                      >
                        <option value="desc">Descending</option>
                        <option value="asc">Ascending</option>
                      </select>
                    </div>
                  </div>
                  <div>
                    <label htmlFor="min-price" className="block text-sm font-medium mb-1">
                      Min Price
                    </label>
                    <input
                      id="min-price"
                      type="number"
                      inputMode="numeric"
                      min={0}
                      className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                      value={minPrice}
                      onChange={(e) => setMinPrice(e.target.value)}
                      aria-label="Minimum price"
                      disabled={loading}
                    />
                  </div>
                  <div>
                    <label htmlFor="max-price" className="block text-sm font-medium mb-1">
                      Max Price
                    </label>
                    <input
                      id="max-price"
                      type="number"
                      inputMode="numeric"
                      min={0}
                      className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                      value={maxPrice}
                      onChange={(e) => setMaxPrice(e.target.value)}
                      aria-label="Maximum price"
                      disabled={loading}
                    />
                  </div>
                  <div>
                    <label htmlFor="rooms" className="block text-sm font-medium mb-1">
                      Minimum Rooms
                    </label>
                    <input
                      id="rooms"
                      type="number"
                      inputMode="numeric"
                      min={0}
                      className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                      value={rooms}
                      onChange={(e) => setRooms(e.target.value)}
                      aria-label="Minimum rooms"
                      disabled={loading}
                    />
                  </div>
                  <div>
                    <label htmlFor="property-type" className="block text-sm font-medium mb-1">
                      Property Type
                    </label>
                    <select
                      id="property-type"
                      className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                      value={propertyType}
                      onChange={(e) => setPropertyType(e.target.value)}
                      aria-label="Property type"
                      disabled={loading}
                    >
                      <option value="">Any</option>
                      <option value="apartment">Apartment</option>
                      <option value="house">House</option>
                      <option value="studio">Studio</option>
                      <option value="loft">Loft</option>
                      <option value="townhouse">Townhouse</option>
                      <option value="other">Other</option>
                    </select>
                  </div>
                  <button
                    type="button"
                    onClick={() => {
                      setMinPrice('');
                      setMaxPrice('');
                      setRooms('');
                      setPropertyType('');
                      setSortBy('relevance');
                      setSortOrder('desc');
                    }}
                    className={[
                      'inline-flex items-center justify-center rounded-md border',
                      'px-3 py-2 text-sm hover:bg-muted',
                      'disabled:opacity-50',
                    ].join(' ')}
                    aria-label="Clear filters"
                    disabled={loading}
                  >
                    Clear Filters
                  </button>
                  <div className="grid grid-cols-2 gap-4 mt-2">
                    <div>
                      <label htmlFor="export-format" className="block text-sm font-medium mb-1">
                        Export Format
                      </label>
                      <select
                        id="export-format"
                        className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                        value={exportFormat}
                        onChange={(e) => setExportFormat(e.target.value)}
                        aria-label="Export format"
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
                      <label htmlFor="export-columns" className="block text-sm font-medium mb-1">
                        Columns (optional)
                      </label>
                      <input
                        id="export-columns"
                        className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                        value={exportColumns}
                        onChange={(e) => setExportColumns(e.target.value)}
                        placeholder="e.g., id, city, price"
                        aria-label="Export columns"
                        disabled={loading}
                      />
                    </div>
                    {exportFormat === 'csv' ? (
                      <div className="grid grid-cols-2 gap-4 col-span-2">
                        <div>
                          <label htmlFor="csv-delimiter" className="block text-sm font-medium mb-1">
                            CSV Delimiter
                          </label>
                          <select
                            id="csv-delimiter"
                            className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                            value={csvDelimiter}
                            onChange={(e) => setCsvDelimiter(e.target.value)}
                            aria-label="CSV delimiter"
                            disabled={loading}
                          >
                            <option value=",">Comma (,)</option>
                            <option value=";">Semicolon (;)</option>
                          </select>
                        </div>
                        <div>
                          <label htmlFor="csv-decimal" className="block text-sm font-medium mb-1">
                            Decimal Separator
                          </label>
                          <select
                            id="csv-decimal"
                            className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                            value={csvDecimal}
                            onChange={(e) => setCsvDecimal(e.target.value)}
                            aria-label="CSV decimal separator"
                            disabled={loading}
                          >
                            <option value=".">Dot (.)</option>
                            <option value=",">Comma (,)</option>
                          </select>
                        </div>
                        <label className="flex items-center gap-2 text-sm col-span-2">
                          <input
                            type="checkbox"
                            checked={exportIncludeHeader}
                            onChange={(e) => setExportIncludeHeader(e.target.checked)}
                            aria-label="Include CSV header"
                            disabled={loading}
                          />
                          Include header row
                        </label>
                      </div>
                    ) : null}
                    <div className="flex items-end">
                      <button
                        type="button"
                        onClick={handleExport}
                        disabled={exporting || !query.trim() || results.length === 0}
                        className={[
                          'inline-flex items-center justify-center rounded-md bg-primary px-3 py-2',
                          'text-sm font-medium text-primary-foreground shadow transition-colors',
                          'hover:bg-primary/90 disabled:opacity-50',
                        ].join(' ')}
                        aria-label={exporting ? 'Exporting' : 'Export'}
                      >
                        <Download className="h-4 w-4 mr-2" />
                        {exporting ? 'Exporting...' : 'Export'}
                      </button>
                    </div>
                  </div>
                  {exportError ? (
                    <div className="text-red-500 text-sm" role="alert">
                      {exportError}
                    </div>
                  ) : null}
                </div>
              </div>
            </div>
          </div>

          {/* Results Grid - 4 Mandated States */}
          <div className="md:col-span-3">
            {/* STATE 1: Empty state (zero-data) */}
            {!hasSearched && !loading && !error && (
              <div
                className="flex flex-col items-center justify-center h-full min-h-[400px] text-center border rounded-lg border-dashed bg-muted/30"
                role="status"
                aria-live="polite"
              >
                <div className="p-4 rounded-full bg-primary/10 mb-4">
                  <SearchIcon className="h-12 w-12 text-primary" aria-hidden="true" />
                </div>
                <h2 className="text-2xl font-bold mb-2">Start Your Property Search</h2>
                <p className="text-muted-foreground max-w-md mb-6">
                  Enter a search query to explore thousands of property listings. Use natural
                  language to describe what you&apos;re looking for.
                </p>
                <div className="space-y-2 mb-6">
                  <p className="text-sm font-medium text-foreground">Try these examples:</p>
                  <div className="flex flex-col gap-2">
                    {EXAMPLE_QUERIES.map((example, idx) => (
                      <button
                        key={idx}
                        type="button"
                        onClick={() => handleExampleQuery(example)}
                        className="text-left text-sm text-primary hover:underline disabled:opacity-50 text-left w-full text-left"
                        disabled={loading}
                      >
                        &ldquo;{example}&rdquo;
                      </button>
                    ))}
                  </div>
                </div>
                <p className="text-xs text-muted-foreground">
                  Export will be available once you have search results.
                </p>
              </div>
            )}

            {/* STATE 2: Loading state */}
            {loading && !hasSearched && (
              <div
                className="space-y-4"
                role="status"
                aria-live="polite"
                aria-label="Loading search results"
              >
                {/* Skeleton results */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                  {[1, 2, 3, 4, 5, 6].map((i) => (
                    <div key={i} className="rounded-lg border bg-card overflow-hidden">
                      <div className="h-48 bg-muted animate-pulse" aria-hidden="true" />
                      <div className="p-6 space-y-4">
                        <div className="h-6 bg-muted animate-pulse rounded" aria-hidden="true" />
                        <div
                          className="h-4 bg-muted animate-pulse rounded w-3/4"
                          aria-hidden="true"
                        />
                        <div
                          className="h-4 bg-muted animate-pulse rounded w-1/2"
                          aria-hidden="true"
                        />
                      </div>
                    </div>
                  ))}
                </div>
                {/* Map placeholder */}
                <div
                  className="h-[420px] w-full bg-muted animate-pulse rounded-lg border border-dashed"
                  aria-hidden="true"
                />
              </div>
            )}

            {/* STATE 3: Error state */}
            {error && !loading && (
              <div
                className="flex flex-col items-center justify-center h-full min-h-[400px] text-center border rounded-lg bg-destructive/10"
                role="alert"
                aria-live="assertive"
              >
                <div className="p-4 rounded-full bg-destructive/20 mb-4">
                  <AlertCircle className="h-12 w-12 text-destructive" aria-hidden="true" />
                </div>
                <h2 className="text-2xl font-bold mb-2 text-destructive">Search Failed</h2>
                <p className="text-destructive/90 max-w-md mb-4">{error}</p>
                {requestId && (
                  <p className="text-xs text-muted-foreground mb-6 font-mono">
                    Request ID: {requestId}
                  </p>
                )}
                <button
                  type="button"
                  onClick={() => handleSearch()}
                  className={[
                    'inline-flex items-center gap-2 rounded-md bg-primary px-6 py-2',
                    'text-sm font-medium text-primary-foreground shadow transition-colors',
                    'hover:bg-primary/90',
                  ].join(' ')}
                  aria-label="Retry search"
                >
                  <RefreshCw className="h-4 w-4" />
                  Retry
                </button>
              </div>
            )}

            {/* STATE 4: Populated state */}
            {!loading && hasSearched && !error && (
              <div className="space-y-4">
                {results.length === 0 ? (
                  /* No results sub-state of Populated */
                  <div
                    className="flex flex-col items-center justify-center h-64 text-center border rounded-lg border-dashed"
                    role="status"
                    aria-live="polite"
                  >
                    <div className="p-4 rounded-full bg-muted/50 mb-4">
                      <MapPin className="h-8 w-8 text-muted-foreground" aria-hidden="true" />
                    </div>
                    <h3 className="text-lg font-semibold">No Results Found</h3>
                    <p className="text-sm text-muted-foreground max-w-sm mt-2">
                      Try adjusting your search terms, filters, or sorting options to find more
                      properties.
                    </p>
                  </div>
                ) : (
                  <>
                    <div className="flex items-center justify-between gap-4">
                      <div className="flex items-center gap-4">
                        <div
                          className="inline-flex rounded-md border bg-background p-1"
                          role="group"
                          aria-label="View mode"
                        >
                          <button
                            type="button"
                            onClick={() => setViewMode('list')}
                            className={[
                              'px-3 py-1.5 text-sm rounded-md',
                              viewMode === 'list' ? 'bg-muted font-medium' : 'hover:bg-muted/50',
                              'disabled:opacity-50',
                            ].join(' ')}
                            aria-pressed={viewMode === 'list'}
                            aria-label="List view"
                          >
                            List
                          </button>
                          <button
                            type="button"
                            onClick={() => setViewMode('map')}
                            className={[
                              'px-3 py-1.5 text-sm rounded-md',
                              viewMode === 'map' ? 'bg-muted font-medium' : 'hover:bg-muted/50',
                              'disabled:opacity-50',
                            ].join(' ')}
                            aria-pressed={viewMode === 'map'}
                            aria-label="Map view"
                          >
                            Map
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
                              className="w-4 h-4 rounded border-gray-300"
                              aria-label="Use Mapbox"
                            />
                            Enhanced Map
                          </label>
                          {useMapbox && (
                            <button
                              type="button"
                              onClick={() => {
                                setEnableDrawing(!enableDrawing);
                                if (enableDrawing) {
                                  setDrawnPolygon(null);
                                }
                              }}
                              className={[
                                'inline-flex items-center gap-1 px-2 py-1 text-sm rounded-md border',
                                enableDrawing
                                  ? 'bg-primary text-primary-foreground'
                                  : 'hover:bg-muted',
                              ].join(' ')}
                              aria-label={enableDrawing ? 'Disable drawing' : 'Enable drawing'}
                            >
                              <Pencil className="h-3 w-3" />
                              {enableDrawing ? 'Drawing...' : 'Draw Area'}
                            </button>
                          )}
                          {drawnPolygon && (
                            <button
                              type="button"
                              onClick={handlePolygonClear}
                              className="text-xs text-muted-foreground hover:text-foreground"
                              aria-label="Clear drawn area"
                            >
                              Clear Area
                            </button>
                          )}
                        </div>
                      )}
                      <div className="text-sm text-muted-foreground">
                        {drawnPolygon ? filteredByPolygon.length : filteredMapPoints.length} /{' '}
                        {mapPoints.length} / {results.length} shown
                        {drawnPolygon && (
                          <span className="text-primary ml-1">(filtered by area)</span>
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
                          <div className="flex items-center justify-center h-64 text-center border rounded-lg border-dashed">
                            <div>
                              <div className="font-semibold">No mappable results</div>
                              <div className="text-sm text-muted-foreground mt-1">
                                These listings do not include latitude/longitude coordinates.
                              </div>
                            </div>
                          </div>
                        )}
                      </div>
                    ) : (
                      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {results.map((item, index) => {
                          const prop = item.property;
                          return (
                            <div
                              key={`${prop.id ?? 'unknown'}-${index}`}
                              className="rounded-lg border bg-card text-card-foreground shadow-sm overflow-hidden"
                            >
                              <div className="aspect-video w-full bg-muted relative">
                                <div
                                  className="absolute inset-0 flex items-center justify-center text-muted-foreground"
                                  aria-label="Property image placeholder"
                                >
                                  Property image
                                </div>
                                {prop.id && (
                                  <div className="absolute top-2 right-2">
                                    <HeartButton propertyId={prop.id} />
                                  </div>
                                )}
                              </div>
                              <div className="p-6 space-y-2">
                                <h3 className="text-2xl font-semibold leading-none tracking-tight">
                                  {prop.title || 'Untitled Property'}
                                </h3>
                                <p className="text-sm text-muted-foreground">
                                  {prop.city}, {prop.country}
                                </p>
                                <div className="font-bold text-lg">
                                  {prop.price
                                    ? `$${prop.price.toLocaleString()}`
                                    : 'Price on request'}
                                </div>
                                <p className="text-sm text-muted-foreground">
                                  {[
                                    prop.rooms ? `${prop.rooms} beds` : null,
                                    prop.bathrooms ? `${prop.bathrooms} baths` : null,
                                    prop.area_sqm ? `${prop.area_sqm} m²` : null,
                                  ]
                                    .filter(Boolean)
                                    .join(' • ')}
                                </p>
                                {prop.id && (
                                  <div className="pt-2">
                                    <ListingGenerator propertyId={prop.id} compact />
                                  </div>
                                )}
                                {prop.id && (
                                  <div className="pt-1">
                                    <RelevanceRating query={query} propertyId={prop.id} />
                                  </div>
                                )}
                              </div>
                            </div>
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
