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
import type {
  BulkJobResponse,
  BulkJobType,
  BulkJobStatus,
  BulkJobSourceType,
} from '@/lib/types';
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
        setError({ message: 'Failed to load bulk jobs' });
      }
    } finally {
      setLoadingJobs(false);
    }
  }, [filterJobType, filterStatus, page, pageSize]);

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
      setError({ message: 'Please enter a URL' });
      return;
    }

    setImporting(true);
    setError(null);
    setSuccess(null);

    try {
      const config: Record<string, unknown> =
        importSourceType === 'url'
          ? { file_urls: importUrl.split(',').map((u) => u.trim()) }
          : {};

      await createBulkImportJob({
        source_type: importSourceType,
        config,
        source_name: importSourceName || undefined,
      });

      setSuccess('Import job created successfully!');
      setImportUrl('');
      setImportSourceName('');
      setActiveTab('jobs');
    } catch (err) {
      if (err instanceof ApiError) {
        setError({ message: err.message, requestId: err.request_id });
      } else {
        setError({ message: 'Failed to create import job' });
      }
    } finally {
      setImporting(false);
    }
  };

  // Handle export
  const handleExport = async () => {
    if (!exportQuery) {
      setError({ message: 'Please enter a search query' });
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

      setSuccess('Export job created successfully!');
      setExportQuery('');
      setActiveTab('jobs');
    } catch (err) {
      if (err instanceof ApiError) {
        setError({ message: err.message, requestId: err.request_id });
      } else {
        setError({ message: 'Failed to create export job' });
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
        setError({ message: 'Failed to cancel job' });
      }
    }
  };

  // Handle delete job
  const handleDeleteJob = async (jobId: string) => {
    if (!confirm('Are you sure you want to delete this job?')) return;

    try {
      await deleteBulkJob(jobId);
      loadJobs();
    } catch (err) {
      if (err instanceof ApiError) {
        setError({ message: err.message, requestId: err.request_id });
      } else {
        setError({ message: 'Failed to delete job' });
      }
    }
  };

  // Get status icon and color
  const getStatusDisplay = (status: BulkJobStatus) => {
    switch (status) {
      case 'pending':
        return { icon: Clock, color: 'text-warning bg-warning/10 dark:bg-warning/30', label: 'Pending' };
      case 'running':
        return { icon: Loader2, color: 'text-info bg-info/10 dark:bg-info/30 animate-spin', label: 'Running' };
      case 'completed':
        return { icon: CheckCircle2, color: 'text-success bg-success/10 dark:bg-success/30', label: 'Completed' };
      case 'failed':
        return { icon: XCircle, color: 'text-destructive bg-destructive/10 dark:bg-destructive/30', label: 'Failed' };
      case 'cancelled':
        return { icon: XCircle, color: 'text-muted-foreground bg-muted dark:bg-muted', label: 'Cancelled' };
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
        <button type="button"
          onClick={() => setActiveTab('jobs')}
          className={`px-4 py-2 border-b-2 transition-colors ${
            activeTab === 'jobs'
              ? 'border-primary text-primary'
              : 'border-transparent text-muted-foreground hover:text-foreground'
          }`}
        >
          <RefreshCw className="w-4 h-4 inline-block mr-2" />
          Jobs
        </button>
        <button type="button"
          onClick={() => setActiveTab('import')}
          className={`px-4 py-2 border-b-2 transition-colors ${
            activeTab === 'import'
              ? 'border-primary text-primary'
              : 'border-transparent text-muted-foreground hover:text-foreground'
          }`}
        >
          <Upload className="w-4 h-4 inline-block mr-2" />
          Import
        </button>
        <button type="button"
          onClick={() => setActiveTab('export')}
          className={`px-4 py-2 border-b-2 transition-colors ${
            activeTab === 'export'
              ? 'border-primary text-primary'
              : 'border-transparent text-muted-foreground hover:text-foreground'
          }`}
        >
          <Download className="w-4 h-4 inline-block mr-2" />
          Export
        </button>
      </div>

      {/* Error Display */}
      {error && (
        <div className="flex items-start gap-3 p-4 bg-destructive/10 text-destructive rounded mb-4">
          <AlertCircle className="w-5 h-5 shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="font-medium">Error</p>
            <p className="text-sm">{error.message}</p>
            {error.requestId && <p className="text-xs mt-1">Request ID: {error.requestId}</p>}
          </div>
          <button type="button" onClick={() => setError(null)} className="text-destructive/50 hover:text-destructive">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Success Display */}
      {success && (
        <div className="flex items-start gap-3 p-4 bg-success/10 text-success dark:bg-success/30 dark:text-success rounded mb-4">
          <CheckCircle2 className="w-5 h-5 shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="font-medium">Success</p>
            <p className="text-sm">{success}</p>
          </div>
          <button type="button" onClick={() => setSuccess(null)} className="text-success/50 hover:text-success text-success/50">
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
              <span className="text-sm font-medium">Filters:</span>
            </div>
            <select
              value={filterJobType}
              onChange={(e) => {
                setFilterJobType(e.target.value);
                setPage(1);
              }}
              className="border rounded px-2 py-1 text-sm bg-background"
            >
              <option value="">All Types</option>
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
              <option value="">All Statuses</option>
              {JOB_STATUSES.map((status) => (
                <option key={status} value={status}>
                  {status.charAt(0).toUpperCase() + status.slice(1)}
                </option>
              ))}
            </select>
            <button type="button"
              onClick={() => {
                setFilterJobType('');
                setFilterStatus('');
                setPage(1);
              }}
              className="text-sm text-muted-foreground hover:text-foreground"
            >
              Clear
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
              title="No bulk jobs found"
              description="Create an import or export job to get started"
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
                              job.job_type === 'import' ? 'bg-info/20 text-info' : 'bg-critical/20 text-critical'
                            }`}
                          >
                            {job.job_type === 'import' ? <Upload className="w-3 h-3" /> : <Download className="w-3 h-3" />}
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
                            <span className="text-muted-foreground">Progress:</span>{' '}
                            <span className="font-medium">{job.progress_percent.toFixed(1)}%</span>
                          </div>
                          <div>
                            <span className="text-muted-foreground">Processed:</span>{' '}
                            <span className="font-medium">
                              {job.records_processed}/{job.records_total}
                            </span>
                          </div>
                          {job.records_failed > 0 && (
                            <div>
                              <span className="text-muted-foreground">Failed:</span>{' '}
                              <span className="font-medium text-destructive">{job.records_failed}</span>
                            </div>
                          )}
                        </div>
                        {job.error_message && (
                          <p className="text-sm text-destructive mt-2">{job.error_message}</p>
                        )}
                        <div className="flex gap-4 mt-2 text-xs text-muted-foreground">
                          <span>Created: {formatDate(job.created_at)}</span>
                          {job.completed_at && <span>Completed: {formatDate(job.completed_at)}</span>}
                          {job.expires_at && <span>Expires: {formatDate(job.expires_at)}</span>}
                        </div>
                      </div>
                      <div className="flex gap-2">
                        {job.status === 'running' && (
                          <button type="button"
                            onClick={() => handleCancelJob(job.id)}
                            className="p-2 text-warning hover:bg-warning/10 rounded"
                            title="Cancel job"
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
                            title="Download result"
                          >
                            <Download className="w-4 h-4" />
                          </a>
                        )}
                        {(job.status === 'completed' ||
                          job.status === 'failed' ||
                          job.status === 'cancelled') && (
                          <button type="button"
                            onClick={() => handleDeleteJob(job.id)}
                            className="p-2 text-destructive hover:bg-destructive/10 rounded"
                            title="Delete job"
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
              <button type="button"
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="px-3 py-1 border rounded disabled:opacity-50"
              >
                Previous
              </button>
              <span className="px-3 py-1">
                Page {page} of {Math.ceil(totalJobs / pageSize)}
              </span>
              <button type="button"
                onClick={() => setPage((p) => p + 1)}
                disabled={page >= Math.ceil(totalJobs / pageSize)}
                className="px-3 py-1 border rounded disabled:opacity-50"
              >
                Next
              </button>
            </div>
          )}
        </div>
      )}

      {/* Import Tab */}
      {activeTab === 'import' && (
        <div className="max-w-2xl mx-auto space-y-6">
          <div className="border rounded-lg p-6">
            <h2 className="text-lg font-semibold mb-4">Create Import Job</h2>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-2">Source Type</label>
                <div className="flex gap-2">
                  {['url', 'file_upload', 'portal_api'].map((type) => (
                    <button type="button"
                      key={type}
                      onClick={() => setImportSourceType(type as BulkJobSourceType)}
                      className={`px-4 py-2 rounded border ${
                        importSourceType === type
                          ? 'bg-primary text-primary-foreground'
                          : 'bg-background hover:bg-muted'
                      }`}
                    >
                      {type === 'url' && 'URL'}
                      {type === 'file_upload' && 'File Upload'}
                      {type === 'portal_api' && 'Portal API'}
                    </button>
                  ))}
                </div>
              </div>

              {importSourceType === 'url' && (
                <div>
                  <label className="block text-sm font-medium mb-2">File URLs (comma-separated)</label>
                  <textarea
                    value={importUrl}
                    onChange={(e) => setImportUrl(e.target.value)}
                    className="w-full border rounded p-2 min-h-[100px]"
                    placeholder="https://example.com/data.csv, https://example.com/data.xlsx"
                    disabled={importing}
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    Supports CSV, Excel (.xlsx/.xls), JSON files
                  </p>
                </div>
              )}

              {importSourceType === 'file_upload' && (
                <div className="p-8 border-2 border-dashed rounded-lg text-center text-muted-foreground">
                  <Upload className="w-8 h-8 mx-auto mb-2" />
                  <p>File upload via direct API is available</p>
                  <p className="text-sm">Use the /api/v1/admin/ingest/upload endpoint</p>
                </div>
              )}

              {importSourceType === 'portal_api' && (
                <div className="p-8 border rounded-lg text-center text-muted-foreground">
                  <p>Portal API imports are configured in Data Sources</p>
                  <p className="text-sm mt-1">Visit the Data Sources page to set up portal connections</p>
                </div>
              )}

              <div>
                <label className="block text-sm font-medium mb-2">Source Name (optional)</label>
                <input
                  type="text"
                  value={importSourceName}
                  onChange={(e) => setImportSourceName(e.target.value)}
                  className="w-full border rounded p-2"
                  placeholder="e.g., Warsaw Properties Q1 2024"
                  disabled={importing}
                />
              </div>

              <button type="button"
                onClick={handleImport}
                disabled={importing || (importSourceType === 'url' && !importUrl)}
                className="w-full py-2 bg-primary text-primary-foreground rounded hover:bg-primary/90 disabled:opacity-50 flex items-center justify-center gap-2 focus-visible:outline-none focus-visible:outline-2 focus-visible:outline-ring/50"
              >
                {importing ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Creating Import Job...
                  </>
                ) : (
                  <>
                    <Upload className="w-4 h-4" />
                    Start Import Job
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
            <h2 className="text-lg font-semibold mb-4">Create Export Job</h2>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-2">Export Format</label>
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
                <label className="block text-sm font-medium mb-2">Search Query</label>
                <textarea
                  value={exportQuery}
                  onChange={(e) => setExportQuery(e.target.value)}
                  className="w-full border rounded p-2 min-h-[100px]"
                  placeholder="e.g., apartments in Warsaw under 500000 PLN"
                  disabled={exporting}
                />
                <p className="text-xs text-muted-foreground mt-1">
                  Enter a natural language search query to filter properties for export
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium mb-2">Max Results</label>
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

              <button type="button"
                onClick={handleExport}
                disabled={exporting || !exportQuery}
                className="w-full py-2 bg-primary text-primary-foreground rounded hover:bg-primary/90 disabled:opacity-50 flex items-center justify-center gap-2 focus-visible:outline-none focus-visible:outline-2 focus-visible:outline-ring/50"
              >
                {exporting ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Creating Export Job...
                  </>
                ) : (
                  <>
                    <Download className="w-4 h-4" />
                    Start Export Job
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
