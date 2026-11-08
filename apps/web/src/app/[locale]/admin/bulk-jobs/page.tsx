'use client';

import { useState, useEffect, useCallback } from 'react';
import { useTranslations } from 'next-intl';
import {
  Download,
  Upload,
  Loader2,
  AlertCircle,
  CheckCircle2,
  XCircle,
  Clock,
  Trash2,
  RefreshCw,
  Filter,
  FileSpreadsheet,
  X,
} from 'lucide-react';
import {
  listBulkJobs,
  createBulkImportJob,
  createBulkExportJob,
  cancelBulkJob,
  deleteBulkJob,
  ApiError,
} from '@/lib/api';
import type { BulkJobResponse, BulkJobType, BulkJobStatus, BulkJobSourceType } from '@/lib/types';
import { PageHeader } from '@/components/ui/page-header';
import { EmptyState } from '@/components/ui/states';

interface ErrorState {
  message: string;
  requestId?: string;
}

type TabType = 'jobs' | 'import' | 'export';

const JOB_STATUSES: BulkJobStatus[] = ['pending', 'running', 'completed', 'failed', 'cancelled'];
const JOB_TYPES: BulkJobType[] = ['import', 'export'];
const EXPORT_FORMATS = ['csv', 'json', 'xlsx', 'parquet', 'md', 'pdf'];

export default function BulkJobsPage() {
  const t = useTranslations('pages.admin.bulkJobs');
  const tCommon = useTranslations('common');
  // Jobs state
  const [jobs, setJobs] = useState<BulkJobResponse[]>([]);
  const [loadingJobs, setLoadingJobs] = useState(true);
  const [totalJobs, setTotalJobs] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(10);

  // UI state
  const [activeTab, setActiveTab] = useState<TabType>('jobs');
  const [error, setError] = useState<ErrorState | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Filter state
  const [filterJobType, setFilterJobType] = useState<string>('');
  const [filterStatus, setFilterStatus] = useState<string>('');

  // Import form state
  const [importSourceType, setImportSourceType] = useState<BulkJobSourceType>('url');
  const [importUrl, setImportUrl] = useState('');
  const [importSourceName, setImportSourceName] = useState('');
  const [importing, setImporting] = useState(false);

  // Export form state
  const [exportFormat, setExportFormat] = useState('csv');
  const [exportQuery, setExportQuery] = useState('');
  const [exportLimit, setExportLimit] = useState(100);
  const [exporting, setExporting] = useState(false);

  // Load jobs
  const loadJobs = useCallback(async () => {
    setLoadingJobs(true);
    try {
      const response = await listBulkJobs({
        job_type: filterJobType || undefined,
        status: filterStatus || undefined,
        page,
        page_size: pageSize,
      });
      setJobs(response.jobs);
      setTotalJobs(response.total);
    } catch (err) {
      if (err instanceof ApiError) {
        setError({ message: err.message, requestId: err.request_id });
      } else {
        setError({ message: t('errors.loadJobs') });
      }
    } finally {
      setLoadingJobs(false);
    }
  }, [filterJobType, filterStatus, page, pageSize, t]);

  useEffect(() => {
    if (activeTab === 'jobs') {
      loadJobs();
    }
  }, [activeTab, loadJobs]);

  // Auto-refresh jobs every 5 seconds if there are running jobs
  useEffect(() => {
    if (activeTab !== 'jobs') return;

    const hasRunningJobs = jobs.some((job) => job.status === 'running' || job.status === 'pending');
    if (!hasRunningJobs) return;

    const interval = setInterval(loadJobs, 5000);
    return () => clearInterval(interval);
  }, [activeTab, jobs, loadJobs]);

  // Handle import
  const handleImport = async () => {
    if (importSourceType === 'url' && !importUrl) {
      setError({ message: t('errors.urlRequired') });
      return;
    }

    setImporting(true);
    setError(null);
    setSuccess(null);

    try {
      const config: Record<string, unknown> =
        importSourceType === 'url' ? { file_urls: importUrl.split(',').map((u) => u.trim()) } : {};

      await createBulkImportJob({
        source_type: importSourceType,
        config,
        source_name: importSourceName || undefined,
      });

      setSuccess(t('success.importCreated'));
      setImportUrl('');
      setImportSourceName('');
      setActiveTab('jobs');
    } catch (err) {
      if (err instanceof ApiError) {
        setError({ message: err.message, requestId: err.request_id });
      } else {
        setError({ message: t('errors.createImport') });
      }
    } finally {
      setImporting(false);
    }
  };

  // Handle export
  const handleExport = async () => {
    if (!exportQuery) {
      setError({ message: t('errors.queryRequired') });
      return;
    }

    setExporting(true);
    setError(null);
    setSuccess(null);

    try {
      await createBulkExportJob({
        format: exportFormat,
        source_type: 'search',
        config: {
          query: exportQuery,
          limit: exportLimit,
        },
      });

      setSuccess(t('success.exportCreated'));
      setExportQuery('');
      setActiveTab('jobs');
    } catch (err) {
      if (err instanceof ApiError) {
        setError({ message: err.message, requestId: err.request_id });
      } else {
        setError({ message: t('errors.createExport') });
      }
    } finally {
      setExporting(false);
    }
  };

  // Handle cancel job
  const handleCancelJob = async (jobId: string) => {
    try {
      await cancelBulkJob(jobId);
      loadJobs();
    } catch (err) {
      if (err instanceof ApiError) {
        setError({ message: err.message, requestId: err.request_id });
      } else {
        setError({ message: t('errors.cancelJob') });
      }
    }
  };

  // Handle delete job
  const handleDeleteJob = async (jobId: string) => {
    if (!confirm(t('confirm.deleteJob'))) return;

    try {
      await deleteBulkJob(jobId);
      loadJobs();
    } catch (err) {
      if (err instanceof ApiError) {
        setError({ message: err.message, requestId: err.request_id });
      } else {
        setError({ message: t('errors.deleteJob') });
      }
    }
  };

  // Get status icon and color
  const getStatusDisplay = (status: BulkJobStatus) => {
    switch (status) {
      case 'pending':
        return {
          icon: Clock,
          color: 'text-warning bg-warning/10 dark:bg-warning/30',
          label: t('status.pending'),
        };
      case 'running':
        return {
          icon: Loader2,
          color: 'text-info bg-info/10 dark:bg-info/30 animate-spin',
          label: t('status.running'),
        };
      case 'completed':
        return {
          icon: CheckCircle2,
          color: 'text-success bg-success/10 dark:bg-success/30',
          label: t('status.completed'),
        };
      case 'failed':
        return {
          icon: XCircle,
          color: 'text-destructive bg-destructive/10 dark:bg-destructive/30',
          label: t('status.failed'),
        };
      case 'cancelled':
        return {
          icon: XCircle,
          color: 'text-muted-foreground bg-muted dark:bg-muted',
          label: t('status.cancelled'),
        };
      default:
        return { icon: Clock, color: 'text-muted-foreground bg-muted', label: status };
    }
  };

  // Format date
  const formatDate = (dateStr?: string) => {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleString();
  };

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-6">
        <PageHeader title={t('title')} description={t('description')} />
      </div>

      {/* Tabs */}
      <div className="flex gap-2 mb-6 border-b">
        <button
          type="button"
          onClick={() => setActiveTab('jobs')}
          className={`px-4 py-2 border-b-2 transition-colors ${
            activeTab === 'jobs'
              ? 'border-primary text-primary'
              : 'border-transparent text-muted-foreground hover:text-foreground'
          }`}
        >
          <RefreshCw className="w-4 h-4 inline-block mr-2" />
          {t('tabs.jobs')}
        </button>
        <button
          type="button"
          onClick={() => setActiveTab('import')}
          className={`px-4 py-2 border-b-2 transition-colors ${
            activeTab === 'import'
              ? 'border-primary text-primary'
              : 'border-transparent text-muted-foreground hover:text-foreground'
          }`}
        >
          <Upload className="w-4 h-4 inline-block mr-2" />
          {t('tabs.import')}
        </button>
        <button
          type="button"
          onClick={() => setActiveTab('export')}
          className={`px-4 py-2 border-b-2 transition-colors ${
            activeTab === 'export'
              ? 'border-primary text-primary'
              : 'border-transparent text-muted-foreground hover:text-foreground'
          }`}
        >
          <Download className="w-4 h-4 inline-block mr-2" />
          {t('tabs.export')}
        </button>
      </div>

      {/* Error Display */}
      {error && (
        <div className="flex items-start gap-3 p-4 bg-destructive/10 text-destructive rounded mb-4">
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
      {success && (
        <div className="flex items-start gap-3 p-4 bg-success/10 text-success dark:bg-success/30 dark:text-success rounded mb-4">
          <CheckCircle2 className="w-5 h-5 shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="font-medium">{tCommon('success')}</p>
            <p className="text-sm">{success}</p>
          </div>
          <button
            type="button"
            onClick={() => setSuccess(null)}
            className="text-success/50 hover:text-success text-success/50"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Jobs Tab */}
      {activeTab === 'jobs' && (
        <div className="space-y-4">
          {/* Filters */}
          <div className="flex flex-wrap gap-4 p-4 bg-muted/50 rounded-lg">
            <div className="flex items-center gap-2">
              <Filter className="w-4 h-4 text-muted-foreground" />
              <span className="text-sm font-medium">{t('filters.label')}</span>
            </div>
            <select
              value={filterJobType}
              onChange={(e) => {
                setFilterJobType(e.target.value);
                setPage(1);
              }}
              className="border rounded px-2 py-1 text-sm bg-background"
            >
              <option value="">{t('filters.allTypes')}</option>
              {JOB_TYPES.map((type) => (
                <option key={type} value={type}>
                  {type.charAt(0).toUpperCase() + type.slice(1)}
                </option>
              ))}
            </select>
            <select
              value={filterStatus}
              onChange={(e) => {
                setFilterStatus(e.target.value);
                setPage(1);
              }}
              className="border rounded px-2 py-1 text-sm bg-background"
            >
              <option value="">{t('filters.allStatuses')}</option>
              {JOB_STATUSES.map((status) => (
                <option key={status} value={status}>
                  {status.charAt(0).toUpperCase() + status.slice(1)}
                </option>
              ))}
            </select>
            <button
              type="button"
              onClick={() => {
                setFilterJobType('');
                setFilterStatus('');
                setPage(1);
              }}
              className="text-sm text-muted-foreground hover:text-foreground"
            >
              {tCommon('clear')}
            </button>
          </div>

          {/* Jobs List */}
          {loadingJobs ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
            </div>
          ) : jobs.length === 0 ? (
            <EmptyState
              icon={FileSpreadsheet}
              title={t('empty.title')}
              description={t('empty.description')}
            />
          ) : (
            <div className="space-y-3">
              {jobs.map((job) => {
                const statusDisplay = getStatusDisplay(job.status);
                const StatusIcon = statusDisplay.icon;
                return (
                  <div
                    key={job.id}
                    className="border rounded-lg p-4 hover:bg-muted/30 transition-colors"
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1">
                        <div className="flex items-center gap-3 mb-2">
                          <span
                            className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${
                              job.job_type === 'import'
                                ? 'bg-info/20 text-info'
                                : 'bg-critical/20 text-critical'
                            }`}
                          >
                            {job.job_type === 'import' ? (
                              <Upload className="w-3 h-3" />
                            ) : (
                              <Download className="w-3 h-3" />
                            )}
                            {job.job_type.toUpperCase()}
                          </span>
                          <span
                            className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${statusDisplay.color}`}
                          >
                            <StatusIcon className="w-3 h-3" />
                            {statusDisplay.label}
                          </span>
                          <span className="text-xs text-muted-foreground">{job.source_type}</span>
                        </div>
                        <p className="text-sm text-muted-foreground mb-2">ID: {job.id}</p>
                        <div className="grid grid-cols-3 gap-4 text-sm">
                          <div>
                            <span className="text-muted-foreground">{t('job.progress')}</span>{' '}
                            <span className="font-medium">{job.progress_percent.toFixed(1)}%</span>
                          </div>
                          <div>
                            <span className="text-muted-foreground">{t('job.processed')}</span>{' '}
                            <span className="font-medium">
                              {job.records_processed}/{job.records_total}
                            </span>
                          </div>
                          {job.records_failed > 0 && (
                            <div>
                              <span className="text-muted-foreground">{t('job.failed')}</span>{' '}
                              <span className="font-medium text-destructive">
                                {job.records_failed}
                              </span>
                            </div>
                          )}
                        </div>
                        {job.error_message && (
                          <p className="text-sm text-destructive mt-2">{job.error_message}</p>
                        )}
                        <div className="flex gap-4 mt-2 text-xs text-muted-foreground">
                          <span>{t('job.created', { date: formatDate(job.created_at) })}</span>
                          {job.completed_at && (
                            <span>
                              {t('job.completed', { date: formatDate(job.completed_at) })}
                            </span>
                          )}
                          {job.expires_at && (
                            <span>{t('job.expires', { date: formatDate(job.expires_at) })}</span>
                          )}
                        </div>
                      </div>
                      <div className="flex gap-2">
                        {job.status === 'running' && (
                          <button
                            type="button"
                            onClick={() => handleCancelJob(job.id)}
                            className="p-2 text-warning hover:bg-warning/10 rounded"
                            title={t('job.cancelTitle')}
                          >
                            <XCircle className="w-4 h-4" />
                          </button>
                        )}
                        {job.result_url && (
                          <a
                            href={job.result_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="p-2 text-primary hover:bg-primary/10 rounded"
                            title={t('job.downloadTitle')}
                          >
                            <Download className="w-4 h-4" />
                          </a>
                        )}
                        {(job.status === 'completed' ||
                          job.status === 'failed' ||
                          job.status === 'cancelled') && (
                          <button
                            type="button"
                            onClick={() => handleDeleteJob(job.id)}
                            className="p-2 text-destructive hover:bg-destructive/10 rounded"
                            title={t('job.deleteTitle')}
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        )}
                      </div>
                    </div>
                    {/* Progress bar */}
                    {(job.status === 'running' || job.status === 'pending') && (
                      <div className="mt-3">
                        <div className="w-full bg-muted rounded-full h-2">
                          <div
                            className="bg-primary h-2 rounded-full transition-all duration-300"
                            style={{ width: `${job.progress_percent}%` }}
                          />
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}

          {/* Pagination */}
          {totalJobs > pageSize && (
            <div className="flex justify-center gap-2 mt-6">
              <button
                type="button"
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="px-3 py-1 border rounded disabled:opacity-50"
              >
                {tCommon('previous')}
              </button>
              <span className="px-3 py-1">
                {t('pagination.page', { page, total: Math.ceil(totalJobs / pageSize) })}
              </span>
              <button
                type="button"
                onClick={() => setPage((p) => p + 1)}
                disabled={page >= Math.ceil(totalJobs / pageSize)}
                className="px-3 py-1 border rounded disabled:opacity-50"
              >
                {tCommon('next')}
              </button>
            </div>
          )}
        </div>
      )}

      {/* Import Tab */}
      {activeTab === 'import' && (
        <div className="max-w-2xl mx-auto space-y-6">
          <div className="border rounded-lg p-6">
            <h2 className="text-lg font-semibold mb-4">{t('import.title')}</h2>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-2">{t('import.sourceType')}</label>
                <div className="flex gap-2">
                  {['url', 'file_upload', 'portal_api'].map((type) => (
                    <button
                      type="button"
                      key={type}
                      onClick={() => setImportSourceType(type as BulkJobSourceType)}
                      className={`px-4 py-2 rounded border ${
                        importSourceType === type
                          ? 'bg-primary text-primary-foreground'
                          : 'bg-background hover:bg-muted'
                      }`}
                    >
                      {type === 'url' && t('import.typeUrl')}
                      {type === 'file_upload' && t('import.typeFile')}
                      {type === 'portal_api' && t('import.typePortal')}
                    </button>
                  ))}
                </div>
              </div>

              {importSourceType === 'url' && (
                <div>
                  <label className="block text-sm font-medium mb-2">{t('import.fileUrls')}</label>
                  <textarea
                    value={importUrl}
                    onChange={(e) => setImportUrl(e.target.value)}
                    className="w-full border rounded p-2 min-h-[100px]"
                    placeholder={t('import.fileUrlsPlaceholder')}
                    disabled={importing}
                  />
                  <p className="text-xs text-muted-foreground mt-1">{t('import.supports')}</p>
                </div>
              )}

              {importSourceType === 'file_upload' && (
                <div className="p-8 border-2 border-dashed rounded-lg text-center text-muted-foreground">
                  <Upload className="w-8 h-8 mx-auto mb-2" />
                  <p>{t('import.fileUploadAvailable')}</p>
                  <p className="text-sm">{t('import.fileUploadEndpoint')}</p>
                </div>
              )}

              {importSourceType === 'portal_api' && (
                <div className="p-8 border rounded-lg text-center text-muted-foreground">
                  <p>{t('import.portalConfigured')}</p>
                  <p className="text-sm mt-1">{t('import.portalHint')}</p>
                </div>
              )}

              <div>
                <label className="block text-sm font-medium mb-2">{t('import.sourceName')}</label>
                <input
                  type="text"
                  value={importSourceName}
                  onChange={(e) => setImportSourceName(e.target.value)}
                  className="w-full border rounded p-2"
                  placeholder={t('import.sourceNamePlaceholder')}
                  disabled={importing}
                />
              </div>

              <button
                type="button"
                onClick={handleImport}
                disabled={importing || (importSourceType === 'url' && !importUrl)}
                className="w-full py-2 bg-primary text-primary-foreground rounded hover:bg-primary/90 disabled:opacity-50 flex items-center justify-center gap-2 focus-visible:outline-none focus-visible:outline-2 focus-visible:outline-ring/50"
              >
                {importing ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    {t('import.creating')}
                  </>
                ) : (
                  <>
                    <Upload className="w-4 h-4" />
                    {t('import.start')}
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Export Tab */}
      {activeTab === 'export' && (
        <div className="max-w-2xl mx-auto space-y-6">
          <div className="border rounded-lg p-6">
            <h2 className="text-lg font-semibold mb-4">{t('export.title')}</h2>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-2">{t('export.format')}</label>
                <select
                  value={exportFormat}
                  onChange={(e) => setExportFormat(e.target.value)}
                  className="w-full border rounded p-2"
                  disabled={exporting}
                >
                  {EXPORT_FORMATS.map((format) => (
                    <option key={format} value={format}>
                      {format.toUpperCase()}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium mb-2">{t('export.query')}</label>
                <textarea
                  value={exportQuery}
                  onChange={(e) => setExportQuery(e.target.value)}
                  className="w-full border rounded p-2 min-h-[100px]"
                  placeholder={t('export.queryPlaceholder')}
                  disabled={exporting}
                />
                <p className="text-xs text-muted-foreground mt-1">{t('export.queryHint')}</p>
              </div>

              <div>
                <label className="block text-sm font-medium mb-2">{t('export.maxResults')}</label>
                <input
                  type="number"
                  value={exportLimit}
                  onChange={(e) => setExportLimit(parseInt(e.target.value) || 100)}
                  className="w-full border rounded p-2"
                  min={1}
                  max={10000}
                  disabled={exporting}
                />
              </div>

              <button
                type="button"
                onClick={handleExport}
                disabled={exporting || !exportQuery}
                className="w-full py-2 bg-primary text-primary-foreground rounded hover:bg-primary/90 disabled:opacity-50 flex items-center justify-center gap-2 focus-visible:outline-none focus-visible:outline-2 focus-visible:outline-ring/50"
              >
                {exporting ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    {t('export.creating')}
                  </>
                ) : (
                  <>
                    <Download className="w-4 h-4" />
                    {t('export.start')}
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
