'use client';

import { useState, useMemo, useCallback, useEffect, useRef, Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { useLocale, useTranslations } from 'next-intl';
import {
  Search as SearchIcon,
  MapPin,
  Download,
  Pencil,
} from 'lucide-react';
import { searchProperties, exportPropertiesBySearch, ApiError } from '@/lib/api';
import { SearchResultItem } from '@/lib/types';
import { warn } from '@/lib/logger';
import { extractMapPoints, type PropertyMapPoint } from '@/components/search/property-map-utils';
import type { PolygonCoordinates } from '@/components/search/geo-draw-control';
import {
  validatePolygon,
  serializePolygonToUrl,
  deserializePolygonFromUrl,
} from '@/lib/geo-validation';
import { Button } from '@/components/ui/button';
import { MonoAnnotation } from '@/components/ui/mono-annotation';
import { EmptyState, ErrorState, LoadingState } from '@/components/ui/states';
import dynamic from 'next/dynamic';
import MapControls, {
  type MapFilterOptions,
  DEFAULT_CLUSTER_OPTIONS,
} from '@/components/search/map-controls';
import { SaveSearchButton } from '@/components/search/save-search-button';
import { PresetSelector } from '@/components/search/preset-selector';
import { ParsedChips } from '@/components/search/parsed-chips';
import { ResultsLedger } from '@/components/search/results-ledger';
import { AreaAnalyticsCard } from '@/components/search/area-analytics-card';
import { useTrackSearchDebounced } from '@/hooks/useLeadTracking';
import type { FilterPreset } from '@/lib/types';
import { formatPrice } from '@/lib/format';

const PropertyMap = dynamic(() => import('@/components/search/property-map'), {
  ssr: false,
  loading: () => <div className="h-[420px] w-full bg-muted animate-pulse" />,
});

const PropertyMapboxMap = dynamic(() => import('@/components/search/property-mapbox-map'), {
  ssr: false,
  loading: () => <div className="h-[420px] w-full bg-muted animate-pulse" />,
});

/** The label of a sort, in the catalogue's own words. */
const SORT_LABEL_KEY: Record<string, string> = {
  relevance: 'sortOptions.relevance',
  price: 'sortOptions.price',
  price_per_sqm: 'sortOptions.pricePerSqm',
  area_sqm: 'sortOptions.area',
  year_built: 'sortOptions.yearBuilt',
};

const CONTROL_CLASS =
  'h-9 w-full rounded-md border border-input bg-background px-2.5 text-[13px] text-foreground';
const MONO_CONTROL_CLASS = `${CONTROL_CLASS} font-mono`;
const LABEL_CLASS = 'text-[12px] font-medium text-foreground';

/**
 * How many results one page of the ledger holds.
 *
 * The search is a ranked list, so "the next page" is "more of the same
 * ranking": asking for a longer list answers with the rows the short list
 * left out. The page starts at twenty rows and grows by twenty at a time,
 * up to the ceiling - a catalogue of a hundred thousand deeds is not read
 * in one screen, and the visitor is never asked to.
 */
const RESULTS_PAGE_SIZE = 20;
const RESULTS_MAX = 100;

/**
 * The width at which the panes stand side by side.
 *
 * The same breakpoint the layout uses (`lg`): under it the panes are one
 * column, over it they are three.
 */
const DESKTOP_WIDTH = 1024;

function SearchPageContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const locale = useLocale();
  const t = useTranslations('search');
  const tCommon = useTranslations('common');
  const tPage = useTranslations('pages.search');

  // Example queries for empty state
  const exampleQueries = [
    t('examples.madrid'),
    t('examples.houseGarden'),
    t('examples.studioCity'),
    t('examples.luxuryParking'),
  ];
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

  // A link that carries a question - the chips of the landing, the example
  // queries of the empty state - has to land on a search that already holds
  // that question. The parameter is read once, here.
  const [query, setQuery] = useState(() => searchParams.get('q') ?? '');
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<SearchResultItem[]>([]);
  const [total, setTotal] = useState(0);
  const [limit, setLimit] = useState(RESULTS_PAGE_SIZE);
  const [error, setError] = useState<string | null>(null);
  const [requestId, setRequestId] = useState<string | undefined>();
  const [hasSearched, setHasSearched] = useState(false);
  const [minPrice, setMinPrice] = useState<string>('');
  const [maxPrice, setMaxPrice] = useState<string>('');
  const [rooms, setRooms] = useState<string>('');
  const [propertyType, setPropertyType] = useState<string>('');
  const [sortBy, setSortBy] = useState<string>('relevance');
  const [sortOrder, setSortOrder] = useState<string>('desc');

  /**
   * The currency the listings are priced in. The map and its price bands
   * speak in it - a Polish market is filtered in zloty, not in dollars.
   */
  const resultCurrency = useMemo(
    () => results.find((item) => item.property?.currency)?.property?.currency,
    [results]
  );
  const [exportFormat, setExportFormat] = useState<string>('csv');
  const [exportColumns, setExportColumns] = useState<string>('');
  const [exportIncludeHeader, setExportIncludeHeader] = useState<boolean>(true);
  const [csvDelimiter, setCsvDelimiter] = useState<string>(',');
  const [csvDecimal, setCsvDecimal] = useState<string>('.');
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);
  // The map is a pane of its own, next to the results - so the map is what
  // the route opens on. The switch narrows the route to the list.
  const [viewMode, setViewMode] = useState<'list' | 'map'>('map');
  // The pane that holds the map, so a narrow screen can be brought to it.
  const mapPaneRef = useRef<HTMLElement | null>(null);
  // The first run of the view is not a change: the page did not scroll
  // itself on arrival.
  const firstViewRun = useRef(true);
  const [filtersOpen, setFiltersOpen] = useState(false);
  // The enhanced map is Mapbox GL, and Mapbox asks for an access token. A
  // deployment without one (the public demo, a self-hoster) must not be
  // offered a switch that opens a map the provider refuses to serve: the
  // style request answers 401 and the visitor gets a grey rectangle. So the
  // switch appears only where the token exists - and the free OpenStreetMap
  // map is what everyone else gets.
  const mapboxToken = process.env.NEXT_PUBLIC_MAPBOX_TOKEN;
  const canUseMapbox = Boolean(mapboxToken);
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
        warn(t('errors.invalidPolygon'), { error: validation.error });
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
    [searchParams, router, t]
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
    // A marker on the map is a listing, and a listing has a page of its own.
    // The click opens it.
    if (!point.id) return;
    router.push(`/${locale}/property/${point.id}`);
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

  /**
   * The city the results stand in. It is read from the catalogue, not from
   * the sentence: the sentence is parsed by the model on the server, and
   * what came back is the only truth about where the listings are.
   */
  const city = useMemo(() => {
    const counts = new Map<string, number>();
    for (const item of results) {
      const name = item.property?.city;
      if (!name) continue;
      counts.set(name, (counts.get(name) ?? 0) + 1);
    }
    let best: string | undefined;
    let bestCount = 0;
    counts.forEach((count, name) => {
      if (count > bestCount) {
        best = name;
        bestCount = count;
      }
    });
    return best;
  }, [results]);

  const listingsInCity = useMemo(
    () => results.filter((item) => item.property?.city === city).length,
    [results, city]
  );

  /**
   * The chips of the parsed sentence: the filters that are in force, written
   * the way the landing's instrument writes them.
   */
  const chips = useMemo(() => {
    const list: string[] = [];
    if (city) list.push(`city = ${city}`);

    const amount = (value: string) => {
      const parsed = Number(value);
      if (!Number.isFinite(parsed)) return value;
      return formatPrice(parsed, resultCurrency ?? 'PLN', locale);
    };

    if (minPrice.trim()) list.push(`price ≥ ${amount(minPrice.trim())}`);
    if (maxPrice.trim()) list.push(`price ≤ ${amount(maxPrice.trim())}`);
    if (rooms.trim()) list.push(`rooms = ${rooms.trim()}`);
    if (propertyType.trim()) list.push(`type = ${propertyType.trim().toLowerCase()}`);

    return list;
  }, [city, minPrice, maxPrice, rooms, propertyType, resultCurrency, locale]);

  const buildFilters = (): { filters?: Record<string, unknown>; error?: string } => {
    const min = minPrice.trim() ? Number(minPrice) : undefined;
    const max = maxPrice.trim() ? Number(maxPrice) : undefined;
    const minRooms = rooms.trim() ? Number(rooms) : undefined;

    if (min !== undefined && Number.isNaN(min)) return { error: t('errors.invalidMinPrice') };
    if (max !== undefined && Number.isNaN(max)) return { error: t('errors.invalidMaxPrice') };
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

  const handleSearch = async (e?: React.FormEvent, nextLimit?: number) => {
    e?.preventDefault();
    setLoading(true);
    setError(null);
    setRequestId(undefined);
    setHasSearched(true);
    try {
      if (!query.trim()) {
        setResults([]);
        setTotal(0);
        setError(t('errors.emptyQuery'));
        return;
      }

      const { filters, error: filterError } = buildFilters();
      if (filterError) {
        setResults([]);
        setTotal(0);
        setError(filterError);
        return;
      }

      // Lead tracking: record the search intent (debounced, best-effort).
      try {
        trackSearchDebounced(query.trim(), filters);
      } catch {
        // Tracking must never break the search.
      }

      const wanted = nextLimit ?? limit;
      const response = await searchProperties({
        query,
        limit: wanted,
        sort_by: sortBy as 'relevance' | 'price' | 'price_per_sqm' | 'area_sqm' | 'year_built',
        sort_order: sortOrder as 'asc' | 'desc',
        filters,
      });
      setResults(response.results);
      setTotal(response.count ?? response.results.length);
      setLimit(wanted);
    } catch (err) {
      setResults([]);
      setTotal(0);
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

  // A question that arrives in the URL is searched for, once, on arrival.
  // The landing sends people here with a question in the address; landing on
  // an empty search box would throw that away.
  const initialQuery = searchParams.get('q');
  useEffect(() => {
    if (initialQuery) {
      void handleSearch();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleExport = async () => {
    setExporting(true);
    setExportError(null);
    try {
      if (!query.trim()) {
        setExportError(t('errors.emptyQuery'));
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

  const resetFilters = () => {
    setMinPrice('');
    setMaxPrice('');
    setRooms('');
    setPropertyType('');
    setSortBy('relevance');
    setSortOrder('desc');
  };

  /**
   * The next page of the ledger.
   *
   * The search is a ranking, so the next page is more of the same ranking:
   * the request asks for a longer list and the rows the short list left
   * out arrive in it.
   */
  const loadMore = () => {
    void handleSearch(undefined, Math.min(limit + RESULTS_PAGE_SIZE, RESULTS_MAX));
  };

  const sortLabel = t(SORT_LABEL_KEY[sortBy] ?? 'sortOptions.relevance');
  const shownCount = drawnPolygon ? filteredByPolygon.length : filteredMapPoints.length;
  /**
   * The points the map draws.
   *
   * The pane shows what the map shows: a filter that hides every point
   * leaves an empty map, and the pane says so instead of drawing a map
   * with nothing on it.
   */
  const shownMapPoints = drawnPolygon ? filteredByPolygon : filteredMapPoints;
  const showMap = viewMode === 'map';

  /**
   * The narrow screen is brought to the map when the visitor asks for it.
   *
   * On a desktop the map is a column that is always on the screen, so
   * nothing is scrolled. On a phone it stands under the rows, and the
   * visitor who pressed "Map" is answered by seeing the map.
   */
  useEffect(() => {
    if (firstViewRun.current) {
      firstViewRun.current = false;
      return;
    }
    if (!showMap) return;
    if (typeof window === 'undefined') return;
    if (window.innerWidth >= DESKTOP_WIDTH) return;
    mapPaneRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }, [showMap]);

  return (
    <div className="flex min-h-full flex-col bg-background" aria-live="polite">
      {/* The route has a name for the search engine and the screen reader;
          the top bar of the application already carries it on the screen. */}
      <h1 className="sr-only">{tPage('title')}</h1>

      {/* The query bar: the sentence, and the filters it produced. */}
      <form
        onSubmit={handleSearch}
        role="search"
        aria-label={t('searchLabel')}
        className="flex shrink-0 flex-col gap-2.5 border-b border-border px-6 py-3"
      >
        <div className="flex gap-2">
          <div className="relative min-w-0 flex-1">
            <SearchIcon
              className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground"
              aria-hidden="true"
            />
            <input
              type="text"
              data-testid="search-input"
              placeholder={t('placeholder')}
              className={[
                'h-11 w-full rounded-lg border border-input bg-background',
                'pl-9 pr-4 text-[15px]',
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
            className="h-11 rounded-lg px-5"
          >
            {loading ? tCommon('searching') : tCommon('search')}
          </Button>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <ParsedChips
            chips={chips}
            note={chips.length ? t('parsed.note') : undefined}
            count={total}
          />
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => setFiltersOpen((open) => !open)}
            aria-expanded={filtersOpen}
            data-testid="search-filters-toggle"
            className="h-7 rounded-full px-3 text-[12px] lg:hidden"
          >
            {t('filters.title')}
          </Button>
        </div>
      </form>

      {/* The three panes: the filters, the results, the map. */}
      <div
        className={[
          'grid flex-1 grid-cols-1',
          showMap
            ? 'lg:grid-cols-[248px_460px_minmax(0,1fr)]'
            : 'lg:grid-cols-[248px_minmax(0,1fr)]',
        ].join(' ')}
      >
        {/* The filters. */}
        <aside
          data-testid="search-filters"
          className={[
            'border-b border-border px-6 py-4 lg:border-b-0 lg:border-r',
            filtersOpen ? 'block' : 'hidden',
            'lg:block',
          ].join(' ')}
        >
          <div className="flex items-baseline justify-between gap-3">
            <h2 className="text-[14px] font-semibold text-foreground">{t('filters.title')}</h2>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={resetFilters}
              disabled={loading}
              className="h-7 px-2 text-[12px] font-normal text-muted-foreground"
            >
              {t('filters.reset')}
            </Button>
          </div>

          <div className="mt-4 flex flex-col gap-4">
            <div className="flex flex-col gap-1.5">
              <span className={LABEL_CLASS}>{t('filters.city')}</span>
              <div className="flex h-9 items-center justify-between gap-2 rounded-md border border-input bg-background px-2.5">
                <span className="truncate font-mono text-[13px] text-foreground">
                  {city ?? '—'}
                </span>
                {city ? (
                  <MonoAnnotation className="shrink-0">
                    {t('filters.inResults', { count: listingsInCity })}
                  </MonoAnnotation>
                ) : null}
              </div>
            </div>

            <div className="flex flex-col gap-1.5">
              <label htmlFor="min-price" className={LABEL_CLASS}>
                {t('filters.minPrice')}
              </label>
              <input
                id="min-price"
                type="number"
                inputMode="numeric"
                min={0}
                className={MONO_CONTROL_CLASS}
                value={minPrice}
                onChange={(e) => setMinPrice(e.target.value)}
                aria-label={t('filters.minPrice')}
                disabled={loading}
              />
            </div>

            <div className="flex flex-col gap-1.5">
              <label htmlFor="max-price" className={LABEL_CLASS}>
                {t('filters.maxPrice')}
              </label>
              <input
                id="max-price"
                type="number"
                inputMode="numeric"
                min={0}
                className={MONO_CONTROL_CLASS}
                value={maxPrice}
                onChange={(e) => setMaxPrice(e.target.value)}
                aria-label={t('filters.maxPrice')}
                disabled={loading}
              />
            </div>

            <div className="flex flex-col gap-1.5">
              <label htmlFor="rooms" className={LABEL_CLASS}>
                {t('filters.minRooms')}
              </label>
              <input
                id="rooms"
                type="number"
                inputMode="numeric"
                min={0}
                className={MONO_CONTROL_CLASS}
                value={rooms}
                onChange={(e) => setRooms(e.target.value)}
                aria-label={t('filters.minRooms')}
                disabled={loading}
              />
            </div>

            <div className="flex flex-col gap-1.5">
              <label htmlFor="property-type" className={LABEL_CLASS}>
                {t('filters.propertyType')}
              </label>
              <select
                id="property-type"
                className={CONTROL_CLASS}
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

            <div className="flex flex-col gap-1.5">
              <label htmlFor="sort-by" className={LABEL_CLASS}>
                {t('filters.sortBy')}
              </label>
              <select
                id="sort-by"
                className={CONTROL_CLASS}
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

            <div className="flex flex-col gap-1.5">
              <label htmlFor="sort-order" className={LABEL_CLASS}>
                {t('filters.order')}
              </label>
              <select
                id="sort-order"
                className={CONTROL_CLASS}
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

          <div className="mt-6 flex flex-col gap-3 border-t border-border pt-4">
            <SaveSearchButton
              filters={{
                query,
                min_price: minPrice.trim() ? Number(minPrice) : undefined,
                max_price: maxPrice.trim() ? Number(maxPrice) : undefined,
                min_rooms: rooms.trim() ? Number(rooms) : undefined,
                property_type: propertyType.trim() || undefined,
              }}
              query={query}
              className="w-full justify-center"
            />

            <div className="flex flex-col gap-1.5">
              <label htmlFor="export-format" className={LABEL_CLASS}>
                {t('export.format')}
              </label>
              <select
                id="export-format"
                className={CONTROL_CLASS}
                value={exportFormat}
                onChange={(e) => setExportFormat(e.target.value)}
                aria-label={t('export.format')}
                disabled={loading || results.length === 0}
              >
                <option value="csv">{t('export.csv')}</option>
                <option value="xlsx">{t('export.excel')}</option>
                <option value="json">{t('export.json')}</option>
                <option value="md">{t('export.markdown')}</option>
                <option value="pdf">{t('export.pdf')}</option>
              </select>
            </div>

            <div className="flex flex-col gap-1.5">
              <label htmlFor="export-columns" className={LABEL_CLASS}>
                {t('export.columns')}
              </label>
              <input
                id="export-columns"
                className={MONO_CONTROL_CLASS}
                value={exportColumns}
                onChange={(e) => setExportColumns(e.target.value)}
                placeholder={t('export.columnsPlaceholder')}
                aria-label={t('export.columns')}
                disabled={loading}
              />
            </div>

            {exportFormat === 'csv' ? (
              <div className="flex flex-col gap-3">
                <div className="flex flex-col gap-1.5">
                  <label htmlFor="csv-delimiter" className={LABEL_CLASS}>
                    {t('export.delimiter')}
                  </label>
                  <select
                    id="csv-delimiter"
                    className={CONTROL_CLASS}
                    value={csvDelimiter}
                    onChange={(e) => setCsvDelimiter(e.target.value)}
                    aria-label={t('export.delimiter')}
                    disabled={loading}
                  >
                    <option value=",">{t('export.delimiterComma')}</option>
                    <option value=";">{t('export.delimiterSemicolon')}</option>
                  </select>
                </div>
                <div className="flex flex-col gap-1.5">
                  <label htmlFor="csv-decimal" className={LABEL_CLASS}>
                    {t('export.decimalSeparator')}
                  </label>
                  <select
                    id="csv-decimal"
                    className={CONTROL_CLASS}
                    value={csvDecimal}
                    onChange={(e) => setCsvDecimal(e.target.value)}
                    aria-label={t('export.decimalSeparator')}
                    disabled={loading}
                  >
                    <option value=".">{t('export.decimalDot')}</option>
                    <option value=",">{t('export.decimalComma')}</option>
                  </select>
                </div>
                <label className="flex items-center gap-2 text-[13px] text-foreground">
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

            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={handleExport}
              disabled={exporting || !query.trim() || results.length === 0}
              aria-label={exporting ? tCommon('exporting') : tCommon('export')}
              className="w-full justify-center"
            >
              <Download className="mr-1.5 size-3.5" aria-hidden="true" />
              {exporting ? tCommon('exporting') : tCommon('export')}
            </Button>
            <MonoAnnotation>{t('export.hint')}</MonoAnnotation>

            {exportError ? (
              <div className="text-[12px] text-destructive" role="alert">
                {exportError}
              </div>
            ) : null}
          </div>
        </aside>

        {/* The results: a ledger of prices. */}
        <section
          data-testid="search-results"
          className="order-2 flex flex-col lg:border-r lg:border-border"
        >
          <div className="flex flex-col gap-2 border-b border-border px-6 py-2.5">
            <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-2">
              <p className="min-w-0 text-[14px]">
                {city ? (
                  <span className="font-semibold text-foreground">{city}</span>
                ) : null}
                <span className="text-muted-foreground">
                  {city ? ' · ' : ''}
                  {t('results.summarySort', { sort: sortLabel })}
                </span>
              </p>
              <div className="flex items-center gap-3">
                <MonoAnnotation>
                  {t('map.shown', { shown: shownCount, total: results.length })}
                </MonoAnnotation>
                <div
                  className="inline-flex rounded-md border border-border p-0.5"
                  role="group"
                  aria-label={t('view.label')}
                >
                  <button
                    type="button"
                    onClick={() => setViewMode('list')}
                    className={[
                      'rounded-sm px-2.5 py-1 text-[12px]',
                      viewMode === 'list' ? 'bg-muted font-medium' : 'text-muted-foreground',
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
                      'rounded-sm px-2.5 py-1 text-[12px]',
                      viewMode === 'map' ? 'bg-muted font-medium' : 'text-muted-foreground',
                    ].join(' ')}
                    aria-pressed={viewMode === 'map'}
                    aria-label={t('view.map')}
                  >
                    {t('view.map')}
                  </button>
                </div>
              </div>
            </div>

            {hasSearched && results.length > 0 ? (
              <div className="flex flex-wrap items-center gap-2">
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
                      const form = document.querySelector(
                        'form[role="search"]'
                      ) as HTMLFormElement | null;
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
            ) : null}
          </div>

          <div className="flex-1">
            {/* STATE 1: Empty state (zero-data) */}
            {!hasSearched && !loading && !error && (
              <EmptyState
                icon={SearchIcon}
                title={t('emptyState.title')}
                description={t('emptyState.description')}
                action={
                  <div className="flex flex-col items-start gap-2">
                    <p className="text-[14px] font-medium text-foreground">
                      {t('emptyState.tryExamples')}
                    </p>
                    <div className="flex flex-col items-start gap-1">
                      {exampleQueries.map((example, idx) => (
                        <button
                          key={idx}
                          type="button"
                          onClick={() => handleExampleQuery(example)}
                          className="text-left text-[14px] text-foreground hover:underline disabled:opacity-50"
                          disabled={loading}
                        >
                          &ldquo;{example}&rdquo;
                        </button>
                      ))}
                    </div>
                    <MonoAnnotation>{t('emptyState.exportHint')}</MonoAnnotation>
                  </div>
                }
              />
            )}

            {/* STATE 2: Loading state. The state belongs to the search that is
                running: `hasSearched` is set before the request starts, so
                the old condition never showed the skeletons. The results of a
                finished search stay on the screen while the next one runs. */}
            {loading && results.length === 0 && (
              <div
                role="status"
                aria-live="polite"
                aria-label={tCommon('loading')}
              >
                <LoadingState variant="rows" rows={6} />
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
                      {t('page.requestId', { id: requestId })}
                    </p>
                  ) : null
                }
              />
            )}

            {/* STATE 4: Populated state. The ledger knows how to say that it
                is empty, so the whole result set goes to it. */}
            {!loading && hasSearched && !error && (
              <ResultsLedger results={results} query={query} />
            )}

            {/* The next page of the ledger. The ranking is the same one -
                the page asks for more of the list the search already
                ranked, so the rows that were left out arrive here. */}
            {hasSearched && !error && results.length > 0 && results.length >= limit && (
              <div className="flex justify-center border-t border-border px-6 py-4">
                <Button
                  type="button"
                  variant="outline"
                  onClick={loadMore}
                  disabled={loading || limit >= RESULTS_MAX}
                  data-testid="search-load-more"
                  className="rounded-full px-5"
                >
                  {t('results.loadMore')}
                </Button>
              </div>
            )}
          </div>
        </section>

        {/* The map, with the area analytics over it. The map is the last
            pane at every width: on a desktop it stands beside the results,
            on a phone it stands under them. The two widths show the same
            panes in the same order, so the toggle means the same thing in
            both - and a phone visitor is not pushed under a map to reach
            the results. */}
        {showMap ? (
          <section
            data-testid="search-map"
            ref={mapPaneRef}
            className="relative order-3"
          >
            <div className="lg:sticky lg:top-0">
              {shownMapPoints.length ? (
                useMapbox && canUseMapbox ? (
                  <>
                    <PropertyMapboxMap
                      points={shownMapPoints}
                      mapboxToken={mapboxToken}
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
                      currency={resultCurrency}
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
                <div className="flex h-[420px] items-center justify-center border-b border-border bg-muted/40 px-6">
                  <EmptyState
                    icon={MapPin}
                    title={
                      results.length ? t('map.noMappableResults') : t('map.noResultsToMap')
                    }
                    description={
                      results.length
                        ? t('map.noMappableResultsHint')
                        : t('map.noResultsToMapHint')
                    }
                    className="w-full"
                  />
                </div>
              )}

              {results.length > 0 ? <AreaAnalyticsCard results={results} /> : null}

              {shownMapPoints.length ? (
                <div className="absolute right-4 top-4 z-[1000] flex items-center gap-2 rounded-lg border border-border bg-background px-2.5 py-1.5">
                  {canUseMapbox ? (
                    <label className="flex items-center gap-2 text-[12px] text-foreground">
                      <input
                        type="checkbox"
                        checked={useMapbox}
                        onChange={(e) => setUseMapbox(e.target.checked)}
                        className="size-3.5 rounded border-input"
                        aria-label={t('map.useMapbox')}
                      />
                      {t('map.enhanced')}
                    </label>
                  ) : null}
                  {useMapbox ? (
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
                      className="h-7 text-[12px]"
                    >
                      <Pencil className="mr-1 size-3" aria-hidden="true" />
                      {enableDrawing ? t('map.drawing') : t('map.drawArea')}
                    </Button>
                  ) : null}
                  {drawnPolygon ? (
                    <Button
                      type="button"
                      size="sm"
                      variant="ghost"
                      onClick={handlePolygonClear}
                      aria-label={t('map.clearArea')}
                      className="h-7 text-[12px]"
                    >
                      {t('map.clearArea')}
                    </Button>
                  ) : null}
                </div>
              ) : null}
            </div>
          </section>
        ) : null}
      </div>
    </div>
  );
}

function SearchPageFallback() {
  return (
    <div className="flex min-h-full flex-col bg-background">
      <div className="flex flex-col gap-2.5 border-b border-border px-6 py-3">
        <div className="h-11 w-full bg-muted animate-pulse rounded-lg" />
        <div className="h-4 w-64 bg-muted animate-pulse rounded" />
      </div>
      <div className="grid flex-1 grid-cols-1 lg:grid-cols-[248px_460px_minmax(0,1fr)]">
        <div className="hidden h-[600px] bg-muted animate-pulse lg:block" />
        <div className="h-[400px] bg-muted animate-pulse" />
        <div className="hidden h-[420px] bg-muted animate-pulse lg:block" />
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
