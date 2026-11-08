'use client';

import { useState, useEffect, useCallback } from 'react';
import { useTranslations } from 'next-intl';
import {
  FileUp,
  Loader2,
  Upload,
  AlertCircle,
  FileSpreadsheet,
  CheckCircle2,
  Table,
  Database,
  Globe,
  Filter,
  X,
} from 'lucide-react';
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
import {
  DataSourceList,
  DeleteConfirmDialog,
  EditDataSourceDialog,
} from '@/components/admin/data-sources';
import type { DataSource, DataSourceUpdate, IngestResponse, PortalAdapterInfo } from '@/lib/types';
import { PageHeader } from '@/components/ui/page-header';

interface ErrorState {
  message: string;
  requestId?: string;
}

interface SheetInfo {
  name: string;
  rowCount: number;
}

type TabType = 'sources' | 'import';

export default function DataSourcesPage() {
  const t = useTranslations('pages.admin.dataSources');
  const tCommon = useTranslations('common');
  // Data sources state
  const [sources, setSources] = useState<DataSource[]>([]);
  const [loadingSources, setLoadingSources] = useState(true);
  const [syncingIds, setSyncingIds] = useState<Set<string>>(new Set());

  // UI state
  const [activeTab, setActiveTab] = useState<TabType>('sources');
  const [error, setError] = useState<ErrorState | null>(null);
  const [result, setResult] = useState<IngestResponse | null>(null);

  // Delete dialog state
  const [deleteSource, setDeleteSource] = useState<DataSource | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  // Edit dialog state
  const [editSource, setEditSource] = useState<DataSource | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  // Import state
  const [importMode, setImportMode] = useState<'url' | 'file' | 'portal'>('url');
  const [fileUrl, setFileUrl] = useState<string>('');
  const [sourceName, setSourceName] = useState<string>('');
  const [loading, setLoading] = useState(false);

  // Excel sheets state
  const [loadingSheets, setLoadingSheets] = useState(false);
  const [sheets, setSheets] = useState<SheetInfo[]>([]);
  const [selectedSheet, setSelectedSheet] = useState<string>('');
  const [headerRow, setHeaderRow] = useState<number>(0);

  // File upload state
  const [uploadFile, setUploadFile] = useState<File | null>(null);

  // Portal state
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

  // Load data sources
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

  // Load available portals
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

  // Load sources on mount
  useEffect(() => {
    loadDataSources();
  }, [loadDataSources]);

  const extractErrorState = (err: unknown): ErrorState => {
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

  // Handle sync
  const handleSync = async (id: string) => {
    setSyncingIds((prev) => new Set(prev).add(id));
    setError(null);

    try {
      await syncDataSource(id);
      // Refresh the list after sync starts
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

  // Handle edit
  const handleEdit = (source: DataSource) => {
    setEditSource(source);
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

  // Handle delete
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

  // File helpers
  const isExcelFile = (url: string): boolean => {
    const lowerUrl = url.toLowerCase();
    return lowerUrl.endsWith('.xlsx') || lowerUrl.endsWith('.xls') || lowerUrl.endsWith('.ods');
  };

  const isExcelFileObj = (file: File | null): boolean => {
    if (!file) return false;
    const name = file.name.toLowerCase();
    return name.endsWith('.xlsx') || name.endsWith('.xls') || name.endsWith('.ods');
  };

  // Load sheets handlers
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
      const sheetInfo: SheetInfo[] = res.sheet_names.map((name) => ({
        name,
        rowCount: res.row_count[name] || 0,
      }));
      setSheets(sheetInfo);
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
      const sheetInfo: SheetInfo[] = res.sheet_names.map((name) => ({
        name,
        rowCount: res.row_count[name] || 0,
      }));
      setSheets(sheetInfo);
      if (res.default_sheet) {
        setSelectedSheet(res.default_sheet);
      }
    } catch (e) {
      setError(extractErrorState(e));
    } finally {
      setLoadingSheets(false);
    }
  };

  // Ingest handlers
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
    <div className="container mx-auto px-4 py-8">
      {/* Header */}
      <PageHeader className="mb-8" title={t('title')} description={t('description')} />

      {/* Tab Navigation */}
      <div className="flex gap-4 border-b-2 mb-6">
        <button
          type="button"
          className={`pb-3 px-4 font-medium transition-colors ${
            activeTab === 'sources'
              ? 'border-b-2 border-primary text-primary'
              : 'text-muted-foreground hover:text-foreground'
          }`}
          onClick={() => setActiveTab('sources')}
        >
          <Database className="w-4 h-4 inline mr-2" />
          {t('tabs.sources', { count: sources.length })}
        </button>
        <button
          type="button"
          className={`pb-3 px-4 font-medium transition-colors ${
            activeTab === 'import'
              ? 'border-b-2 border-primary text-primary'
              : 'text-muted-foreground hover:text-foreground'
          }`}
          onClick={() => setActiveTab('import')}
        >
          <Upload className="w-4 h-4 inline mr-2" />
          {t('tabs.import')}
        </button>
      </div>

      {/* Sources Tab */}
      {activeTab === 'sources' && (
        <DataSourceList
          sources={sources}
          onAddNew={() => setActiveTab('import')}
          onSync={handleSync}
          onEdit={handleEdit}
          onDelete={setDeleteSource}
          syncingIds={syncingIds}
          isLoading={loadingSources}
        />
      )}

      {/* Import Tab */}
      {activeTab === 'import' && (
        <section className="space-y-6">
          {/* Import Mode Toggle */}
          <div className="flex gap-2">
            <button
              type="button"
              className={`px-4 py-2 rounded text-sm font-medium transition-colors ${
                importMode === 'url'
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-secondary text-secondary-foreground hover:bg-secondary/80'
              }`}
              onClick={() => {
                setImportMode('url');
                setSheets([]);
                setSelectedSheet('');
              }}
            >
              <Globe className="w-4 h-4 inline mr-2" />
              {t('importMode.url')}
            </button>
            <button
              type="button"
              className={`px-4 py-2 rounded text-sm font-medium transition-colors ${
                importMode === 'file'
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-secondary text-secondary-foreground hover:bg-secondary/80'
              }`}
              onClick={() => {
                setImportMode('file');
                setSheets([]);
                setSelectedSheet('');
              }}
            >
              <Upload className="w-4 h-4 inline mr-2" />
              {t('importMode.file')}
            </button>
            <button
              type="button"
              className={`px-4 py-2 rounded text-sm font-medium transition-colors ${
                importMode === 'portal'
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-secondary text-secondary-foreground hover:bg-secondary/80'
              }`}
              onClick={() => {
                setImportMode('portal');
                setSheets([]);
                setSelectedSheet('');
              }}
            >
              <Globe className="w-4 h-4 inline mr-2" />
              {t('importMode.portal')}
            </button>
          </div>

          {/* URL/File Import */}
          {(importMode === 'url' || importMode === 'file') && (
            <div className="border rounded-lg p-6">
              <div className="flex items-center gap-2 mb-4">
                <FileUp className="w-5 h-5" />
                <h2 className="text-xl font-semibold">{t('import.title')}</h2>
              </div>

              <div className="space-y-4">
                {importMode === 'url' && (
                  <div>
                    <label htmlFor="fileUrl" className="block text-sm font-medium mb-2">
                      {t('import.fileUrl')}
                    </label>
                    <input
                      id="fileUrl"
                      className="border p-2 w-full rounded"
                      type="text"
                      placeholder="https://example.com/data.xlsx"
                      value={fileUrl}
                      onChange={(e) => setFileUrl(e.target.value)}
                      disabled={loading}
                    />
                    <p className="text-xs text-muted-foreground mt-1">{t('import.fileUrlHint')}</p>
                  </div>
                )}

                {importMode === 'file' && (
                  <div>
                    <label htmlFor="fileUpload" className="block text-sm font-medium mb-2">
                      {t('import.selectFile')}
                    </label>
                    <input
                      id="fileUpload"
                      className="border p-2 w-full rounded"
                      type="file"
                      accept=".xlsx,.xls,.ods,.csv"
                      onChange={(e) => {
                        setUploadFile(e.target.files?.[0] || null);
                        setSheets([]);
                        setSelectedSheet('');
                      }}
                      disabled={loading}
                    />
                    <p className="text-xs text-muted-foreground mt-1">{t('import.fileHint')}</p>
                    {uploadFile && (
                      <p className="text-sm text-muted-foreground mt-2">
                        {t('import.selected')} <strong>{uploadFile.name}</strong> (
                        {t('import.fileSize', {
                          size: (uploadFile.size / 1024 / 1024).toFixed(2),
                        })}
                        )
                      </p>
                    )}
                  </div>
                )}

                <div>
                  <label htmlFor="sourceName" className="block text-sm font-medium mb-2">
                    {t('import.sourceName')}
                  </label>
                  <input
                    id="sourceName"
                    className="border p-2 w-full rounded"
                    type="text"
                    placeholder={t('import.sourceNamePlaceholder')}
                    value={sourceName}
                    onChange={(e) => setSourceName(e.target.value)}
                    disabled={loading}
                  />
                </div>

                {/* Excel Options */}
                {((importMode === 'url' && isExcelFile(fileUrl)) ||
                  (importMode === 'file' && isExcelFileObj(uploadFile))) && (
                  <div className="border-t pt-4 mt-4">
                    <h3 className="text-sm font-semibold mb-3 flex items-center gap-2">
                      <FileSpreadsheet className="w-4 h-4" />
                      {t('import.excelOptions')}
                    </h3>
                    <div className="grid gap-4">
                      <div className="flex gap-2">
                        <button
                          type="button"
                          className="px-4 py-2 bg-secondary text-secondary-foreground rounded hover:bg-secondary/80 disabled:opacity-50 focus-visible:outline-none focus-visible:outline-2 focus-visible:outline-ring/50"
                          onClick={importMode === 'url' ? onLoadSheets : onLoadSheetsUpload}
                          disabled={loadingSheets || loading}
                        >
                          {loadingSheets ? (
                            <>
                              <Loader2 className="w-4 h-4 mr-2 animate-spin inline" />
                              {tCommon('loading')}
                            </>
                          ) : (
                            <>
                              <Table className="w-4 h-4 mr-2 inline" />
                              {t('import.loadSheets')}
                            </>
                          )}
                        </button>
                      </div>

                      {sheets.length > 0 && (
                        <>
                          <div>
                            <label htmlFor="sheetSelect" className="block text-sm font-medium mb-2">
                              {t('import.selectSheet')}
                            </label>
                            <select
                              id="sheetSelect"
                              className="border p-2 w-full rounded"
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

                          <div>
                            <label htmlFor="headerRow" className="block text-sm font-medium mb-2">
                              {t('import.headerRow')}
                            </label>
                            <input
                              id="headerRow"
                              className="border p-2 w-full rounded"
                              type="number"
                              min="0"
                              value={headerRow}
                              onChange={(e) => setHeaderRow(parseInt(e.target.value) || 0)}
                              disabled={loading}
                            />
                          </div>
                        </>
                      )}
                    </div>
                  </div>
                )}

                <button
                  type="button"
                  className="px-4 py-2 bg-primary text-primary-foreground rounded hover:bg-primary/90 disabled:opacity-50 flex items-center gap-2 focus-visible:outline-none focus-visible:outline-2 focus-visible:outline-ring/50"
                  onClick={onIngest}
                  disabled={loading}
                >
                  {loading ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      {t('import.importing')}
                    </>
                  ) : (
                    <>
                      <Upload className="w-4 h-4" />
                      {t('import.action')}
                    </>
                  )}
                </button>
              </div>
            </div>
          )}

          {/* Portal Import */}
          {importMode === 'portal' && (
            <div className="border rounded-lg p-6">
              <div className="flex items-center gap-2 mb-4">
                <Globe className="w-5 h-5" />
                <h2 className="text-xl font-semibold">{t('portal.title')}</h2>
              </div>

              {loadingPortals ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="w-6 h-6 animate-spin mr-2" />
                  {t('portal.loading')}
                </div>
              ) : portals.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">{t('portal.none')}</div>
              ) : (
                <div className="space-y-4">
                  <div>
                    <label htmlFor="portalSelect" className="block text-sm font-medium mb-2">
                      {t('portal.label')}
                    </label>
                    <select
                      id="portalSelect"
                      className="border p-2 w-full rounded"
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

                  <div>
                    <label htmlFor="portalCity" className="block text-sm font-medium mb-2">
                      {t('portal.city')}
                    </label>
                    <input
                      id="portalCity"
                      className="border p-2 w-full rounded"
                      type="text"
                      placeholder={t('portal.cityPlaceholder')}
                      value={portalCity}
                      onChange={(e) => setPortalCity(e.target.value)}
                      disabled={loading}
                    />
                  </div>

                  <div className="border-t pt-4 mt-4">
                    <h3 className="text-sm font-semibold mb-3 flex items-center gap-2">
                      <Filter className="w-4 h-4" />
                      {t('portal.filters')}
                    </h3>

                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label htmlFor="minPrice" className="block text-sm font-medium mb-2">
                          {t('portal.minPrice')}
                        </label>
                        <input
                          id="minPrice"
                          className="border p-2 w-full rounded"
                          type="number"
                          min="0"
                          step="100"
                          placeholder={t('portal.minPricePlaceholder')}
                          value={portalMinPrice}
                          onChange={(e) => setPortalMinPrice(e.target.value)}
                          disabled={loading}
                        />
                      </div>

                      <div>
                        <label htmlFor="maxPrice" className="block text-sm font-medium mb-2">
                          {t('portal.maxPrice')}
                        </label>
                        <input
                          id="maxPrice"
                          className="border p-2 w-full rounded"
                          type="number"
                          min="0"
                          step="100"
                          placeholder={t('portal.maxPricePlaceholder')}
                          value={portalMaxPrice}
                          onChange={(e) => setPortalMaxPrice(e.target.value)}
                          disabled={loading}
                        />
                      </div>

                      <div>
                        <label htmlFor="minRooms" className="block text-sm font-medium mb-2">
                          {t('portal.minRooms')}
                        </label>
                        <input
                          id="minRooms"
                          className="border p-2 w-full rounded"
                          type="number"
                          min="0"
                          step="0.5"
                          placeholder={t('portal.minRoomsPlaceholder')}
                          value={portalMinRooms}
                          onChange={(e) => setPortalMinRooms(e.target.value)}
                          disabled={loading}
                        />
                      </div>

                      <div>
                        <label htmlFor="maxRooms" className="block text-sm font-medium mb-2">
                          {t('portal.maxRooms')}
                        </label>
                        <input
                          id="maxRooms"
                          className="border p-2 w-full rounded"
                          type="number"
                          min="0"
                          step="0.5"
                          placeholder={t('portal.maxRoomsPlaceholder')}
                          value={portalMaxRooms}
                          onChange={(e) => setPortalMaxRooms(e.target.value)}
                          disabled={loading}
                        />
                      </div>

                      <div>
                        <label htmlFor="propertyType" className="block text-sm font-medium mb-2">
                          {t('portal.propertyType')}
                        </label>
                        <select
                          id="propertyType"
                          className="border p-2 w-full rounded"
                          value={portalPropertyType}
                          onChange={(e) => setPortalPropertyType(e.target.value)}
                          disabled={loading}
                        >
                          <option value="">{t('portal.propertyTypeAny')}</option>
                          <option value="apartment">{t('portal.propertyTypeApartment')}</option>
                          <option value="house">{t('portal.propertyTypeHouse')}</option>
                          <option value="studio">{t('portal.propertyTypeStudio')}</option>
                        </select>
                      </div>

                      <div>
                        <label htmlFor="listingType" className="block text-sm font-medium mb-2">
                          {t('portal.listingType')}
                        </label>
                        <select
                          id="listingType"
                          className="border p-2 w-full rounded"
                          value={portalListingType}
                          onChange={(e) => setPortalListingType(e.target.value)}
                          disabled={loading}
                        >
                          <option value="rent">{t('portal.listingTypeRent')}</option>
                          <option value="sale">{t('portal.listingTypeSale')}</option>
                        </select>
                      </div>
                    </div>

                    <div className="mt-4">
                      <label htmlFor="limit" className="block text-sm font-medium mb-2">
                        {t('portal.maxResults')}
                      </label>
                      <input
                        id="limit"
                        className="border p-2 w-full rounded"
                        type="number"
                        min="1"
                        max="500"
                        value={portalLimit}
                        onChange={(e) => setPortalLimit(parseInt(e.target.value) || 50)}
                        disabled={loading}
                      />
                    </div>
                  </div>

                  <div>
                    <label htmlFor="portalSourceName" className="block text-sm font-medium mb-2">
                      {t('import.sourceName')}
                    </label>
                    <input
                      id="portalSourceName"
                      className="border p-2 w-full rounded"
                      type="text"
                      placeholder={t('portal.sourceNamePlaceholder')}
                      value={sourceName}
                      onChange={(e) => setSourceName(e.target.value)}
                      disabled={loading}
                    />
                  </div>

                  <button
                    type="button"
                    className="px-4 py-2 bg-primary text-primary-foreground rounded hover:bg-primary/90 disabled:opacity-50 flex items-center gap-2 focus-visible:outline-none focus-visible:outline-2 focus-visible:outline-ring/50"
                    onClick={onFetchFromPortal}
                    disabled={loading}
                  >
                    {loading ? (
                      <>
                        <Loader2 className="w-4 h-4 animate-spin" />
                        {t('portal.fetching')}
                      </>
                    ) : (
                      <>
                        <Globe className="w-4 h-4" />
                        {t('portal.action')}
                      </>
                    )}
                  </button>
                </div>
              )}
            </div>
          )}
        </section>
      )}

      {/* Error Display */}
      {error && (
        <div className="flex items-start gap-3 p-4 bg-destructive/10 text-destructive rounded mt-4">
          <AlertCircle className="w-5 h-5 shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="font-medium">{tCommon('error')}</p>
            <p className="text-sm">{error.message}</p>
            {error.requestId && (
              <p className="text-xs mt-1">{t('requestId', { id: error.requestId })}</p>
            )}
          </div>
          <button
            type="button"
            onClick={() => setError(null)}
            className="text-destructive/50 hover:text-destructive"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Success Display */}
      {result && (
        <div className="flex items-start gap-3 p-4 bg-success/10 text-success dark:bg-success/30 dark:text-success rounded mt-4">
          <CheckCircle2 className="w-5 h-5 shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="font-medium">{t('result.title')}</p>
            <p className="text-sm">{result.message}</p>
            <p className="text-xs mt-1">
              {t('result.propertiesProcessed', { count: result.properties_processed })}
            </p>
            {result.source_type && (
              <p className="text-xs">{t('result.sourceType', { type: result.source_type })}</p>
            )}
            {result.source_name && (
              <p className="text-xs">{t('result.sourceName', { name: result.source_name })}</p>
            )}
            {result.errors.length > 0 && (
              <details className="mt-2">
                <summary className="text-xs cursor-pointer">
                  {t('result.warnings', { count: result.errors.length })}
                </summary>
                <ul className="text-xs mt-1 list-disc list-inside">
                  {result.errors.map((err, i) => (
                    <li key={i}>{err}</li>
                  ))}
                </ul>
              </details>
            )}
          </div>
          <button
            type="button"
            onClick={() => setResult(null)}
            className="text-success/50 hover:text-success dark:text-success/50 dark:hover:text-success"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Delete Confirmation Dialog */}
      <DeleteConfirmDialog
        source={deleteSource}
        isOpen={!!deleteSource}
        onClose={() => setDeleteSource(null)}
        onConfirm={handleDeleteConfirm}
        isDeleting={isDeleting}
      />

      {/* Edit Dialog */}
      <EditDataSourceDialog
        key={editSource?.id}
        source={editSource}
        isOpen={!!editSource}
        onClose={() => setEditSource(null)}
        onSave={handleSaveEdit}
        isSaving={isSaving}
      />
    </div>
  );
}
