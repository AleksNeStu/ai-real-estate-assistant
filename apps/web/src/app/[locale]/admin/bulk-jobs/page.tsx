'use client';

import { useState, useEffect, useCallback } from 'react';
import { useTranslations } from 'next-intl';
import { Loader2, Upload, Download, X, CheckCircle2 } from 'lucide-react';

import { JobLedger } from '@/components/admin/job-ledger';
import { Button } from '@/components/ui/button';
import { MonoAnnotation } from '@/components/ui/mono-annotation';
import { SectionHeader } from '@/components/ui/page-header';
import { EmptyState, ErrorState, LoadingState } from '@/components/ui/states';
import {
  listBulkJobs,
  createBulkImportJob,
  createBulkExportJob,
  cancelBulkJob,
  deleteBulkJob,
  ApiError,
} from '@/lib/api';
import type { BulkJobResponse, BulkJobType, BulkJobStatus, BulkJobSourceType } from '@/lib/types';

interface ErrorStateValue {
  message: string;
  requestId?: string;
}

const JOB_STATUSES: BulkJobStatus[] = ['pending', 'running', 'completed', 'failed', 'cancelled'];
const JOB_TYPES: BulkJobType[] = ['import', 'export'];
const EXPORT_FORMATS = ['csv', 'json', 'xlsx', 'parquet', 'md', 'pdf'];

/**
 * The bulk jobs tab.
 *
 * The jobs are a list, so the tab is a ledger: the jobs, their progress,
 * their status, and the two things an administrator can do with them. The
 * import and the export forms open above the ledger, one at a time.
 */
export default function BulkJobsPage() {
  const t = useTranslations('pages.admin.bulkJobs');
  const tLedger = useTranslations('pages.admin.bulkJobs.ledger');
  const tCommon = useTranslations('common');

  const [jobs, setJobs] = useState<BulkJobResponse[]>([]);
  const [loadingJobs, setLoadingJobs] = useState(true);
  const [totalJobs, setTotalJobs] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(10);

  const [panel, setPanel] = useState<'import' | 'export' | null>(null);
  const [error, setError] = useState<ErrorStateValue | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const [filterJobType, setFilterJobType] = useState<string>('');
  const [filterStatus, setFilterStatus] = useState<string>('');

  const [importSourceType, setImportSourceType] = useState<BulkJobSourceType>('url');
  const [importUrl, setImportUrl] = useState('');
  const [importSourceName, setImportSourceName] = useState('');
  const [importing, setImporting] = useState(false);

  const [exportFormat, setExportFormat] = useState('csv');
  const [exportQuery, setExportQuery] = useState('');
  const [exportLimit, setExportLimit] = useState(100);
  const [exporting, setExporting] = useState(false);

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
    loadJobs();
  }, [loadJobs]);

  // A job that is still running changes on its own, so the ledger refreshes
  // while there is something to refresh.
  useEffect(() => {
    const hasRunningJobs = jobs.some((job) => job.status === 'running' || job.status === 'pending');
    if (!hasRunningJobs) return;

    const interval = setInterval(loadJobs, 5000);
    return () => clearInterval(interval);
  }, [jobs, loadJobs]);

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
      setPanel(null);
      loadJobs();
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
      setPanel(null);
      loadJobs();
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

  const handleCancelJob = async (job: BulkJobResponse) => {
    try {
      await cancelBulkJob(job.id);
      loadJobs();
    } catch (err) {
      if (err instanceof ApiError) {
        setError({ message: err.message, requestId: err.request_id });
      } else {
        setError({ message: t('errors.cancelJob') });
      }
    }
  };

  const handleDeleteJob = async (job: BulkJobResponse) => {
    if (!confirm(t('confirm.deleteJob'))) return;

    try {
      await deleteBulkJob(job.id);
      loadJobs();
    } catch (err) {
      if (err instanceof ApiError) {
        setError({ message: err.message, requestId: err.request_id });
      } else {
        setError({ message: t('errors.deleteJob') });
      }
    }
  };

  return (
    <>
      <SectionHeader
        title={tLedger('title')}
        description={t('description')}
        actions={
          <>
            <Button
              size="sm"
              onClick={() => setPanel(panel === 'import' ? null : 'import')}
              aria-pressed={panel === 'import'}
            >
              <Upload className="mr-2 size-4" aria-hidden="true" />
              {tLedger('actions.import')}
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setPanel(panel === 'export' ? null : 'export')}
              aria-pressed={panel === 'export'}
            >
              <Download className="mr-2 size-4" aria-hidden="true" />
              {tLedger('actions.export')}
            </Button>
          </>
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

      {success ? (
        <div className="flex items-start gap-3 border-t border-success py-3">
          <CheckCircle2 className="mt-0.5 size-4 shrink-0 text-success" aria-hidden="true" />
          <p className="m-0 text-app text-foreground">{success}</p>
          <button
            type="button"
            onClick={() => setSuccess(null)}
            className="ml-auto text-muted-foreground transition-colors hover:text-foreground"
            aria-label={tCommon('close')}
          >
            <X className="size-4" aria-hidden="true" />
          </button>
        </div>
      ) : null}

      {panel === 'import' ? (
        <section className="flex flex-col gap-4 rounded-lg border border-border p-4">
          <h2 className="m-0 text-app font-semibold text-foreground">{t('import.title')}</h2>

          <div className="flex flex-wrap gap-2">
            {(['url', 'file_upload', 'portal_api'] as BulkJobSourceType[]).map((type) => (
              <button
                type="button"
                key={type}
                onClick={() => setImportSourceType(type)}
                aria-pressed={importSourceType === type}
                className={`h-[34px] rounded-md border px-3 text-[13px] font-medium transition-colors ${
                  importSourceType === type
                    ? 'border-foreground bg-foreground text-background'
                    : 'border-border bg-transparent text-foreground hover:bg-muted'
                }`}
              >
                {type === 'url' && t('import.typeUrl')}
                {type === 'file_upload' && t('import.typeFile')}
                {type === 'portal_api' && t('import.typePortal')}
              </button>
            ))}
          </div>

          {importSourceType === 'url' ? (
            <div className="flex flex-col gap-1.5">
              <label htmlFor="importUrls" className="text-app font-medium text-foreground">
                {t('import.fileUrls')}
              </label>
              <textarea
                id="importUrls"
                value={importUrl}
                onChange={(e) => setImportUrl(e.target.value)}
                className="min-h-[100px] w-full rounded-md border border-border bg-background px-3 py-2 text-app"
                placeholder={t('import.fileUrlsPlaceholder')}
                disabled={importing}
              />
              <MonoAnnotation>{t('import.supports')}</MonoAnnotation>
            </div>
          ) : null}

          {importSourceType === 'file_upload' ? (
            <div className="rounded-lg border border-dashed border-border p-6 text-center">
              <p className="m-0 text-app text-foreground">{t('import.fileUploadAvailable')}</p>
              <MonoAnnotation className="mt-1 block">{t('import.fileUploadEndpoint')}</MonoAnnotation>
            </div>
          ) : null}

          {importSourceType === 'portal_api' ? (
            <div className="rounded-lg border border-border p-6 text-center">
              <p className="m-0 text-app text-foreground">{t('import.portalConfigured')}</p>
              <MonoAnnotation className="mt-1 block">{t('import.portalHint')}</MonoAnnotation>
            </div>
          ) : null}

          <div className="flex flex-col gap-1.5">
            <label htmlFor="importSourceName" className="text-app font-medium text-foreground">
              {t('import.sourceName')}
            </label>
            <input
              id="importSourceName"
              type="text"
              value={importSourceName}
              onChange={(e) => setImportSourceName(e.target.value)}
              className="rounded-md border border-border bg-background px-3 py-2 text-app"
              placeholder={t('import.sourceNamePlaceholder')}
              disabled={importing}
            />
          </div>

          <div>
            <Button onClick={handleImport} disabled={importing || (importSourceType === 'url' && !importUrl)}>
              {importing ? (
                <>
                  <Loader2 className="mr-2 size-4 animate-spin" aria-hidden="true" />
                  {t('import.creating')}
                </>
              ) : (
                <>
                  <Upload className="mr-2 size-4" aria-hidden="true" />
                  {t('import.start')}
                </>
              )}
            </Button>
          </div>
        </section>
      ) : null}

      {panel === 'export' ? (
        <section className="flex flex-col gap-4 rounded-lg border border-border p-4">
          <h2 className="m-0 text-app font-semibold text-foreground">{t('export.title')}</h2>

          <div className="flex flex-col gap-1.5">
            <label htmlFor="exportFormat" className="text-app font-medium text-foreground">
              {t('export.format')}
            </label>
            <select
              id="exportFormat"
              value={exportFormat}
              onChange={(e) => setExportFormat(e.target.value)}
              className="rounded-md border border-border bg-background px-3 py-2 text-app"
              disabled={exporting}
            >
              {EXPORT_FORMATS.map((format) => (
                <option key={format} value={format}>
                  {format.toUpperCase()}
                </option>
              ))}
            </select>
          </div>

          <div className="flex flex-col gap-1.5">
            <label htmlFor="exportQuery" className="text-app font-medium text-foreground">
              {t('export.query')}
            </label>
            <textarea
              id="exportQuery"
              value={exportQuery}
              onChange={(e) => setExportQuery(e.target.value)}
              className="min-h-[100px] w-full rounded-md border border-border bg-background px-3 py-2 text-app"
              placeholder={t('export.queryPlaceholder')}
              disabled={exporting}
            />
            <MonoAnnotation>{t('export.queryHint')}</MonoAnnotation>
          </div>

          <div className="flex flex-col gap-1.5">
            <label htmlFor="exportLimit" className="text-app font-medium text-foreground">
              {t('export.maxResults')}
            </label>
            <input
              id="exportLimit"
              type="number"
              value={exportLimit}
              onChange={(e) => setExportLimit(parseInt(e.target.value) || 100)}
              className="rounded-md border border-border bg-background px-3 py-2 text-app"
              min={1}
              max={10000}
              disabled={exporting}
            />
          </div>

          <div>
            <Button onClick={handleExport} disabled={exporting || !exportQuery}>
              {exporting ? (
                <>
                  <Loader2 className="mr-2 size-4 animate-spin" aria-hidden="true" />
                  {t('export.creating')}
                </>
              ) : (
                <>
                  <Download className="mr-2 size-4" aria-hidden="true" />
                  {t('export.start')}
                </>
              )}
            </Button>
          </div>
        </section>
      ) : null}

      <div className="flex flex-wrap items-center gap-3">
        <MonoAnnotation>{t('filters.label')}</MonoAnnotation>
        <select
          aria-label={t('filters.allTypes')}
          value={filterJobType}
          onChange={(e) => {
            setFilterJobType(e.target.value);
            setPage(1);
          }}
          className="h-[30px] rounded-md border border-border bg-background px-2 text-[13px]"
        >
          <option value="">{t('filters.allTypes')}</option>
          {JOB_TYPES.map((type) => (
            <option key={type} value={type}>
              {type.charAt(0).toUpperCase() + type.slice(1)}
            </option>
          ))}
        </select>
        <select
          aria-label={t('filters.allStatuses')}
          value={filterStatus}
          onChange={(e) => {
            setFilterStatus(e.target.value);
            setPage(1);
          }}
          className="h-[30px] rounded-md border border-border bg-background px-2 text-[13px]"
        >
          <option value="">{t('filters.allStatuses')}</option>
          {JOB_STATUSES.map((status) => (
            <option key={status} value={status}>
              {status.charAt(0).toUpperCase() + status.slice(1)}
            </option>
          ))}
        </select>
        {filterJobType || filterStatus ? (
          <button
            type="button"
            onClick={() => {
              setFilterJobType('');
              setFilterStatus('');
              setPage(1);
            }}
            className="text-[13px] text-muted-foreground transition-colors hover:text-foreground"
          >
            {tCommon('clear')}
          </button>
        ) : null}
      </div>

      {loadingJobs ? (
        <LoadingState rows={4} />
      ) : jobs.length === 0 ? (
        <EmptyState title={t('empty.title')} description={t('empty.description')} />
      ) : (
        <JobLedger jobs={jobs} onCancel={handleCancelJob} onDelete={handleDeleteJob} />
      )}

      {totalJobs > pageSize ? (
        <div className="flex items-center justify-center gap-3">
          <button
            type="button"
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            className="rounded-md border border-border px-3 py-1 text-[13px] transition-colors hover:bg-muted disabled:opacity-50"
          >
            {tCommon('previous')}
          </button>
          <MonoAnnotation>{t('pagination.page', { page, total: Math.ceil(totalJobs / pageSize) })}</MonoAnnotation>
          <button
            type="button"
            onClick={() => setPage((p) => p + 1)}
            disabled={page >= Math.ceil(totalJobs / pageSize)}
            className="rounded-md border border-border px-3 py-1 text-[13px] transition-colors hover:bg-muted disabled:opacity-50"
          >
            {tCommon('next')}
          </button>
        </div>
      ) : null}
    </>
  );
}
