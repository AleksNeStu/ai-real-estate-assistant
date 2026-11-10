'use client';

import { useState, useEffect, useCallback } from 'react';
import { useTranslations } from 'next-intl';
import {
  FileUp,
  Loader2,
  Upload,
  X,
  CheckCircle2,
  Table,
  Globe,
  Filter,
} from 'lucide-react';

import { PortalLedger, SourceLedger } from '@/components/admin/source-ledger';
import {
  DeleteConfirmDialog,
  EditDataSourceDialog,
} from '@/components/admin/data-sources';
import { Button } from '@/components/ui/button';
import { MonoAnnotation } from '@/components/ui/mono-annotation';
import { SectionHeader } from '@/components/ui/page-header';
import { ErrorState, LoadingState } from '@/components/ui/states';
import {
  listDataSources,
  syncDataSource,
  deleteDataSource,
  updateDataSource,
  ingestData,
  getExcelSheets,
  listPortals,
  fetchFromPortal,
  ingestFileUpload,
  getExcelSheetsUpload,
  ApiError,
} from '@/lib/api';
import type { DataSource, DataSourceUpdate, IngestResponse, PortalAdapterInfo } from '@/lib/types';

interface ErrorStateValue {
  message: string;
  requestId?: string;
}

interface SheetInfo {
  name: string;
  rowCount: number;
}

/**
 * The data sources tab.
 *
 * The sources are a list, so the tab is a ledger: every row is a source with
 * its kind, its listings and its last sync. The portals get their own ledger
 * below it - a portal that is not configured is a different thing from a
 * source, and the two are read separately.
 */
export default function DataSourcesPage() {
  const t = useTranslations('pages.admin.dataSources');
  const tLedger = useTranslations('pages.admin.dataSources.ledger');
  const tCommon = useTranslations('common');

  const [sources, setSources] = useState<DataSource[]>([]);
  const [loadingSources, setLoadingSources] = useState(true);
  const [syncingIds, setSyncingIds] = useState<Set<string>>(new Set());

  const [panelOpen, setPanelOpen] = useState(false);
  const [error, setError] = useState<ErrorStateValue | null>(null);
  const [result, setResult] = useState<IngestResponse | null>(null);

  const [deleteSource, setDeleteSource] = useState<DataSource | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  const [editSource, setEditSource] = useState<DataSource | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  const [importMode, setImportMode] = useState<'url' | 'file' | 'portal'>('url');
  const [fileUrl, setFileUrl] = useState<string>('');
  const [sourceName, setSourceName] = useState<string>('');
  const [loading, setLoading] = useState(false);

  const [loadingSheets, setLoadingSheets] = useState(false);
  const [sheets, setSheets] = useState<SheetInfo[]>([]);
  const [selectedSheet, setSelectedSheet] = useState<string>('');
  const [headerRow, setHeaderRow] = useState<number>(0);

  const [uploadFile, setUploadFile] = useState<File | null>(null);

  const [portals, setPortals] = useState<PortalAdapterInfo[]>([]);
  const [loadingPortals, setLoadingPortals] = useState(true);
  const [selectedPortal, setSelectedPortal] = useState<string>('');
  const [portalCity, setPortalCity] = useState<string>('');
  const [portalMinPrice, setPortalMinPrice] = useState<string>('');
  const [portalMaxPrice, setPortalMaxPrice] = useState<string>('');
  const [portalMinRooms, setPortalMinRooms] = useState<string>('');
  const [portalMaxRooms, setPortalMaxRooms] = useState<string>('');
  const [portalPropertyType, setPortalPropertyType] = useState<string>('');
  const [portalListingType, setPortalListingType] = useState<string>('rent');
  const [portalLimit, setPortalLimit] = useState<number>(50);

  // The reference point for "how long ago". It is measured in an effect, not
  // during render: the clock is impure, and a relative time computed against
  // an unmetered clock is a wrong number.
  const [now, setNow] = useState<number | null>(null);

  const loadDataSources = useCallback(async () => {
    try {
      setLoadingSources(true);
      const response = await listDataSources();
      setSources(response.sources);
    } catch (e) {
      console.error('Failed to load data sources:', e);
    } finally {
      setLoadingSources(false);
    }
  }, []);

  useEffect(() => {
    listPortals()
      .then((data) => {
        setPortals(data.adapters);
        if (data.adapters.length > 0) {
          setSelectedPortal(data.adapters[0].name);
        }
      })
      .catch((e) => {
        console.error('Failed to load portals:', e);
      })
      .finally(() => {
        setLoadingPortals(false);
      });
  }, []);

  useEffect(() => {
    loadDataSources();
  }, [loadDataSources]);

  useEffect(() => {
    const update = () => setNow(Date.now());
    update();
    const interval = setInterval(update, 60000);
    return () => clearInterval(interval);
  }, []);

  const extractErrorState = (err: unknown): ErrorStateValue => {
    let message = t('errors.unknown');
    let requestId: string | undefined = undefined;

    if (err instanceof ApiError) {
      message = err.message;
      requestId = err.request_id;
    } else if (err instanceof Error) {
      message = err.message;
    } else {
      message = String(err);
    }

    return { message, requestId };
  };

  const handleSync = async (id: string) => {
    setSyncingIds((prev) => new Set(prev).add(id));
    setError(null);

    try {
      await syncDataSource(id);
      setTimeout(() => {
        loadDataSources();
      }, 1000);
    } catch (e) {
      setError(extractErrorState(e));
    } finally {
      setSyncingIds((prev) => {
        const next = new Set(prev);
        next.delete(id);
        return next;
      });
    }
  };

  const handleSaveEdit = async (id: string, data: DataSourceUpdate) => {
    setIsSaving(true);
    setError(null);
    try {
      await updateDataSource(id, data);
      setEditSource(null);
      loadDataSources();
    } catch (e) {
      setError(extractErrorState(e));
    } finally {
      setIsSaving(false);
    }
  };

  const handleDeleteConfirm = async (id: string) => {
    setIsDeleting(true);
    setError(null);
    try {
      await deleteDataSource(id, true);
      setDeleteSource(null);
      loadDataSources();
    } catch (e) {
      setError(extractErrorState(e));
    } finally {
      setIsDeleting(false);
    }
  };

  const isExcelFile = (url: string): boolean => {
    const lowerUrl = url.toLowerCase();
    return lowerUrl.endsWith('.xlsx') || lowerUrl.endsWith('.xls') || lowerUrl.endsWith('.ods');
  };

  const isExcelFileObj = (file: File | null): boolean => {
    if (!file) return false;
    const name = file.name.toLowerCase();
    return name.endsWith('.xlsx') || name.endsWith('.xls') || name.endsWith('.ods');
  };

  const onLoadSheets = async () => {
    const url = fileUrl.trim();
    if (!url) {
      setError({ message: t('errors.urlRequired') });
      return;
    }

    if (!isExcelFile(url)) {
      setError({ message: t('errors.urlMustBeExcel') });
      return;
    }

    setLoadingSheets(true);
    setError(null);
    setSheets([]);

    try {
      const res = await getExcelSheets({ file_url: url });
      setSheets(
        res.sheet_names.map((name) => ({ name, rowCount: res.row_count[name] || 0 }))
      );
      if (res.default_sheet) {
        setSelectedSheet(res.default_sheet);
      }
    } catch (e) {
      setError(extractErrorState(e));
    } finally {
      setLoadingSheets(false);
    }
  };

  const onLoadSheetsUpload = async () => {
    if (!uploadFile) {
      setError({ message: t('errors.fileRequired') });
      return;
    }

    if (!isExcelFileObj(uploadFile)) {
      setError({ message: t('errors.fileMustBeExcel') });
      return;
    }

    setLoadingSheets(true);
    setError(null);
    setSheets([]);

    try {
      const res = await getExcelSheetsUpload(uploadFile);
      setSheets(
        res.sheet_names.map((name) => ({ name, rowCount: res.row_count[name] || 0 }))
      );
      if (res.default_sheet) {
        setSelectedSheet(res.default_sheet);
      }
    } catch (e) {
      setError(extractErrorState(e));
    } finally {
      setLoadingSheets(false);
    }
  };

  const onIngest = async () => {
    if (importMode === 'file') {
      if (!uploadFile) {
        setError({ message: t('errors.fileToUpload') });
        return;
      }

      setLoading(true);
      setError(null);
      setResult(null);

      try {
        const res = await ingestFileUpload(uploadFile, {
          sheet_name: isExcelFileObj(uploadFile) ? selectedSheet || undefined : undefined,
          header_row: headerRow,
          source_name: sourceName.trim() || undefined,
        });
        setResult(res);
        loadDataSources();
      } catch (e) {
        setError(extractErrorState(e));
      } finally {
        setLoading(false);
      }
      return;
    }

    const url = fileUrl.trim();
    if (!url) {
      setError({ message: t('errors.urlMissing') });
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const request = {
        file_urls: [url],
        sheet_name: isExcelFile(url) ? selectedSheet || undefined : undefined,
        header_row: headerRow,
        source_name: sourceName.trim() || undefined,
      };
      const res = await ingestData(request);
      setResult(res);
      loadDataSources();
    } catch (e) {
      setError(extractErrorState(e));
    } finally {
      setLoading(false);
    }
  };

  const onFetchFromPortal = async () => {
    if (!selectedPortal) {
      setError({ message: t('errors.portalRequired') });
      return;
    }

    if (!portalCity.trim()) {
      setError({ message: t('errors.cityRequired') });
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const request = {
        portal: selectedPortal,
        city: portalCity.trim(),
        min_price: portalMinPrice ? parseFloat(portalMinPrice) : undefined,
        max_price: portalMaxPrice ? parseFloat(portalMaxPrice) : undefined,
        min_rooms: portalMinRooms ? parseFloat(portalMinRooms) : undefined,
        max_rooms: portalMaxRooms ? parseFloat(portalMaxRooms) : undefined,
        property_type: portalPropertyType || undefined,
        listing_type: portalListingType,
        limit: portalLimit,
        source_name: sourceName.trim() || undefined,
      };
      const res = await fetchFromPortal(request);
      setResult({
        message: res.message,
        properties_processed: res.properties_processed,
        errors: res.errors,
        source_type: res.source_type,
        source_name: res.source_name,
      });
      loadDataSources();
    } catch (e) {
      setError(extractErrorState(e));
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <SectionHeader
        title={tLedger('title')}
        description={t('description')}
        actions={
          <Button size="sm" onClick={() => setPanelOpen((open) => !open)} aria-pressed={panelOpen}>
            <Upload className="mr-2 size-4" aria-hidden="true" />
            {t('tabs.import')}
          </Button>
        }
      />

      {error ? (
        <ErrorState
          title={tCommon('error')}
          description={
            error.requestId ? `${error.message} · ${t('requestId', { id: error.requestId })}` : error.message
          }
          action={
            <button
              type="button"
              onClick={() => setError(null)}
              className="text-muted-foreground transition-colors hover:text-foreground"
              aria-label={tCommon('close')}
            >
              <X className="size-4" aria-hidden="true" />
            </button>
          }
        />
      ) : null}

      {result ? (
        <div className="flex items-start gap-3 border-t border-success py-3">
          <CheckCircle2 className="mt-0.5 size-4 shrink-0 text-success" aria-hidden="true" />
          <div className="min-w-0 flex-1">
            <p className="m-0 text-app text-foreground">{result.message}</p>
            <MonoAnnotation className="mt-0.5 block">
              {t('result.propertiesProcessed', { count: result.properties_processed })}
            </MonoAnnotation>
            {result.source_name ? (
              <MonoAnnotation className="mt-0.5 block">
                {t('result.sourceName', { name: result.source_name })}
              </MonoAnnotation>
            ) : null}
          </div>
          <button
            type="button"
            onClick={() => setResult(null)}
            className="text-muted-foreground transition-colors hover:text-foreground"
            aria-label={tCommon('close')}
          >
            <X className="size-4" aria-hidden="true" />
          </button>
        </div>
      ) : null}

      {panelOpen ? (
        <section className="flex flex-col gap-4 rounded-lg border border-border p-4">
          <div className="flex flex-wrap gap-2">
            {(['url', 'file', 'portal'] as const).map((mode) => (
              <button
                type="button"
                key={mode}
                onClick={() => {
                  setImportMode(mode);
                  setSheets([]);
                  setSelectedSheet('');
                }}
                aria-pressed={importMode === mode}
                className={`h-[34px] rounded-md border px-3 text-[13px] font-medium transition-colors ${
                  importMode === mode
                    ? 'border-foreground bg-foreground text-background'
                    : 'border-border bg-transparent text-foreground hover:bg-muted'
                }`}
              >
                {t(`importMode.${mode}`)}
              </button>
            ))}
          </div>

          {importMode === 'url' || importMode === 'file' ? (
            <div className="flex flex-col gap-4">
              <h2 className="m-0 flex items-center gap-2 text-app font-semibold text-foreground">
                <FileUp className="size-4" aria-hidden="true" />
                {t('import.title')}
              </h2>

              {importMode === 'url' ? (
                <div className="flex flex-col gap-1.5">
                  <label htmlFor="fileUrl" className="text-app font-medium text-foreground">
                    {t('import.fileUrl')}
                  </label>
                  <input
                    id="fileUrl"
                    className="rounded-md border border-border bg-background px-3 py-2 text-app"
                    type="text"
                    placeholder="https://example.com/data.xlsx"
                    value={fileUrl}
                    onChange={(e) => setFileUrl(e.target.value)}
                    disabled={loading}
                  />
                  <MonoAnnotation>{t('import.fileUrlHint')}</MonoAnnotation>
                </div>
              ) : (
                <div className="flex flex-col gap-1.5">
                  <label htmlFor="fileUpload" className="text-app font-medium text-foreground">
                    {t('import.selectFile')}
                  </label>
                  <input
                    id="fileUpload"
                    className="rounded-md border border-border bg-background px-3 py-2 text-app"
                    type="file"
                    accept=".xlsx,.xls,.ods,.csv"
                    onChange={(e) => {
                      setUploadFile(e.target.files?.[0] || null);
                      setSheets([]);
                      setSelectedSheet('');
                    }}
                    disabled={loading}
                  />
                  <MonoAnnotation>{t('import.fileHint')}</MonoAnnotation>
                  {uploadFile ? (
                    <MonoAnnotation className="mt-1 block">
                      {t('import.selected')} {uploadFile.name} (
                      {t('import.fileSize', {
                        size: (uploadFile.size / 1024 / 1024).toFixed(2),
                      })}
                      )
                    </MonoAnnotation>
                  ) : null}
                </div>
              )}

              <div className="flex flex-col gap-1.5">
                <label htmlFor="sourceName" className="text-app font-medium text-foreground">
                  {t('import.sourceName')}
                </label>
                <input
                  id="sourceName"
                  type="text"
                  placeholder={t('import.sourceNamePlaceholder')}
                  value={sourceName}
                  onChange={(e) => setSourceName(e.target.value)}
                  disabled={loading}
                  className="rounded-md border border-border bg-background px-3 py-2 text-app"
                />
              </div>

              {((importMode === 'url' && isExcelFile(fileUrl)) ||
                (importMode === 'file' && isExcelFileObj(uploadFile))) && (
                <div className="flex flex-col gap-4 border-t border-border pt-4">
                  <h3 className="m-0 flex items-center gap-2 text-app font-semibold text-foreground">
                    <Table className="size-4" aria-hidden="true" />
                    {t('import.excelOptions')}
                  </h3>

                  <div>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={importMode === 'url' ? onLoadSheets : onLoadSheetsUpload}
                      disabled={loadingSheets || loading}
                    >
                      {loadingSheets ? (
                        <Loader2 className="mr-2 size-4 animate-spin" aria-hidden="true" />
                      ) : (
                        <Table className="mr-2 size-4" aria-hidden="true" />
                      )}
                      {t('import.loadSheets')}
                    </Button>
                  </div>

                  {sheets.length > 0 ? (
                    <>
                      <div className="flex flex-col gap-1.5">
                        <label htmlFor="sheetSelect" className="text-app font-medium text-foreground">
                          {t('import.selectSheet')}
                        </label>
                        <select
                          id="sheetSelect"
                          className="rounded-md border border-border bg-background px-3 py-2 text-app"
                          value={selectedSheet}
                          onChange={(e) => setSelectedSheet(e.target.value)}
                          disabled={loading}
                        >
                          {sheets.map((sheet) => (
                            <option key={sheet.name} value={sheet.name}>
                              {t('import.sheetOption', {
                                name: sheet.name,
                                count: sheet.rowCount,
                              })}
                            </option>
                          ))}
                        </select>
                      </div>

                      <div className="flex flex-col gap-1.5">
                        <label htmlFor="headerRow" className="text-app font-medium text-foreground">
                          {t('import.headerRow')}
                        </label>
                        <input
                          id="headerRow"
                          className="rounded-md border border-border bg-background px-3 py-2 text-app"
                          type="number"
                          min="0"
                          value={headerRow}
                          onChange={(e) => setHeaderRow(parseInt(e.target.value) || 0)}
                          disabled={loading}
                        />
                      </div>
                    </>
                  ) : null}
                </div>
              )}

              <div>
                <Button onClick={onIngest} disabled={loading}>
                  {loading ? (
                    <>
                      <Loader2 className="mr-2 size-4 animate-spin" aria-hidden="true" />
                      {t('import.importing')}
                    </>
                  ) : (
                    <>
                      <Upload className="mr-2 size-4" aria-hidden="true" />
                      {t('import.action')}
                    </>
                  )}
                </Button>
              </div>
            </div>
          ) : null}

          {importMode === 'portal' ? (
            <div className="flex flex-col gap-4">
              <h2 className="m-0 flex items-center gap-2 text-app font-semibold text-foreground">
                <Globe className="size-4" aria-hidden="true" />
                {t('portal.title')}
              </h2>

              {loadingPortals ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="size-5 animate-spin" aria-hidden="true" />
                </div>
              ) : portals.length === 0 ? (
                <p className="m-0 text-app text-muted-foreground">{t('portal.none')}</p>
              ) : (
                <>
                  <div className="flex flex-col gap-1.5">
                    <label htmlFor="portalSelect" className="text-app font-medium text-foreground">
                      {t('portal.label')}
                    </label>
                    <select
                      id="portalSelect"
                      className="rounded-md border border-border bg-background px-3 py-2 text-app"
                      value={selectedPortal}
                      onChange={(e) => setSelectedPortal(e.target.value)}
                      disabled={loading}
                    >
                      {portals.map((portal) => (
                        <option key={portal.name} value={portal.name} disabled={!portal.configured}>
                          {portal.display_name}
                          {!portal.configured && ` ${t('portal.notConfigured')}`}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="flex flex-col gap-1.5">
                    <label htmlFor="portalCity" className="text-app font-medium text-foreground">
                      {t('portal.city')}
                    </label>
                    <input
                      id="portalCity"
                      type="text"
                      placeholder={t('portal.cityPlaceholder')}
                      value={portalCity}
                      onChange={(e) => setPortalCity(e.target.value)}
                      disabled={loading}
                      className="rounded-md border border-border bg-background px-3 py-2 text-app"
                    />
                  </div>

                  <div className="flex flex-col gap-4 border-t border-border pt-4">
                    <h3 className="m-0 flex items-center gap-2 text-app font-semibold text-foreground">
                      <Filter className="size-4" aria-hidden="true" />
                      {t('portal.filters')}
                    </h3>

                    <div className="grid grid-cols-2 gap-4">
                      <div className="flex flex-col gap-1.5">
                        <label htmlFor="minPrice" className="text-app font-medium text-foreground">
                          {t('portal.minPrice')}
                        </label>
                        <input
                          id="minPrice"
                          type="number"
                          min="0"
                          step="100"
                          placeholder={t('portal.minPricePlaceholder')}
                          value={portalMinPrice}
                          onChange={(e) => setPortalMinPrice(e.target.value)}
                          disabled={loading}
                          className="rounded-md border border-border bg-background px-3 py-2 text-app"
                        />
                      </div>

                      <div className="flex flex-col gap-1.5">
                        <label htmlFor="maxPrice" className="text-app font-medium text-foreground">
                          {t('portal.maxPrice')}
                        </label>
                        <input
                          id="maxPrice"
                          type="number"
                          min="0"
                          step="100"
                          placeholder={t('portal.maxPricePlaceholder')}
                          value={portalMaxPrice}
                          onChange={(e) => setPortalMaxPrice(e.target.value)}
                          disabled={loading}
                          className="rounded-md border border-border bg-background px-3 py-2 text-app"
                        />
                      </div>

                      <div className="flex flex-col gap-1.5">
                        <label htmlFor="minRooms" className="text-app font-medium text-foreground">
                          {t('portal.minRooms')}
                        </label>
                        <input
                          id="minRooms"
                          type="number"
                          min="0"
                          step="0.5"
                          placeholder={t('portal.minRoomsPlaceholder')}
                          value={portalMinRooms}
                          onChange={(e) => setPortalMinRooms(e.target.value)}
                          disabled={loading}
                          className="rounded-md border border-border bg-background px-3 py-2 text-app"
                        />
                      </div>

                      <div className="flex flex-col gap-1.5">
                        <label htmlFor="maxRooms" className="text-app font-medium text-foreground">
                          {t('portal.maxRooms')}
                        </label>
                        <input
                          id="maxRooms"
                          type="number"
                          min="0"
                          step="0.5"
                          placeholder={t('portal.maxRoomsPlaceholder')}
                          value={portalMaxRooms}
                          onChange={(e) => setPortalMaxRooms(e.target.value)}
                          disabled={loading}
                          className="rounded-md border border-border bg-background px-3 py-2 text-app"
                        />
                      </div>

                      <div className="flex flex-col gap-1.5">
                        <label htmlFor="propertyType" className="text-app font-medium text-foreground">
                          {t('portal.propertyType')}
                        </label>
                        <select
                          id="propertyType"
                          value={portalPropertyType}
                          onChange={(e) => setPortalPropertyType(e.target.value)}
                          disabled={loading}
                          className="rounded-md border border-border bg-background px-3 py-2 text-app"
                        >
                          <option value="">{t('portal.propertyTypeAny')}</option>
                          <option value="apartment">{t('portal.propertyTypeApartment')}</option>
                          <option value="house">{t('portal.propertyTypeHouse')}</option>
                          <option value="studio">{t('portal.propertyTypeStudio')}</option>
                        </select>
                      </div>

                      <div className="flex flex-col gap-1.5">
                        <label htmlFor="listingType" className="text-app font-medium text-foreground">
                          {t('portal.listingType')}
                        </label>
                        <select
                          id="listingType"
                          value={portalListingType}
                          onChange={(e) => setPortalListingType(e.target.value)}
                          disabled={loading}
                          className="rounded-md border border-border bg-background px-3 py-2 text-app"
                        >
                          <option value="rent">{t('portal.listingTypeRent')}</option>
                          <option value="sale">{t('portal.listingTypeSale')}</option>
                        </select>
                      </div>
                    </div>

                    <div className="flex flex-col gap-1.5">
                      <label htmlFor="limit" className="text-app font-medium text-foreground">
                        {t('portal.maxResults')}
                      </label>
                      <input
                        id="limit"
                        type="number"
                        min="1"
                        max="500"
                        value={portalLimit}
                        onChange={(e) => setPortalLimit(parseInt(e.target.value) || 50)}
                        disabled={loading}
                        className="rounded-md border border-border bg-background px-3 py-2 text-app"
                      />
                    </div>
                  </div>

                  <div className="flex flex-col gap-1.5">
                    <label htmlFor="portalSourceName" className="text-app font-medium text-foreground">
                      {t('import.sourceName')}
                    </label>
                    <input
                      id="portalSourceName"
                      type="text"
                      placeholder={t('portal.sourceNamePlaceholder')}
                      value={sourceName}
                      onChange={(e) => setSourceName(e.target.value)}
                      disabled={loading}
                      className="rounded-md border border-border bg-background px-3 py-2 text-app"
                    />
                  </div>

                  <div>
                    <Button onClick={onFetchFromPortal} disabled={loading}>
                      {loading ? (
                        <>
                          <Loader2 className="mr-2 size-4 animate-spin" aria-hidden="true" />
                          {t('portal.fetching')}
                        </>
                      ) : (
                        <>
                          <Globe className="mr-2 size-4" aria-hidden="true" />
                          {t('portal.action')}
                        </>
                      )}
                    </Button>
                  </div>
                </>
              )}
            </div>
          ) : null}
        </section>
      ) : null}

      {loadingSources ? (
        <LoadingState rows={3} />
      ) : (
        <SourceLedger
          sources={sources}
          now={now}
          syncingIds={syncingIds}
          onSync={(source) => handleSync(source.id)}
          onEdit={setEditSource}
          onDelete={setDeleteSource}
        />
      )}

      <p className="m-0 max-w-[640px] text-annot text-muted-foreground">{tLedger('note')}</p>

      <section className="flex flex-col gap-2">
        <h2 className="m-0 text-app font-semibold text-foreground">{tLedger('portals.title')}</h2>
        <PortalLedger adapters={portals} sources={sources} />
      </section>

      <DeleteConfirmDialog
        source={deleteSource}
        isOpen={!!deleteSource}
        onClose={() => setDeleteSource(null)}
        onConfirm={handleDeleteConfirm}
        isDeleting={isDeleting}
      />

      <EditDataSourceDialog
        key={editSource?.id}
        source={editSource}
        isOpen={!!editSource}
        onClose={() => setEditSource(null)}
        onSave={handleSaveEdit}
        isSaving={isSaving}
      />
    </>
  );
}
