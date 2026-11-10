'use client';

import { useTranslations } from 'next-intl';

import { Ledger, LedgerRow } from '@/components/ui/ledger';
import { MonoAnnotation, type MonoTone } from '@/components/ui/mono-annotation';
import { cn } from '@/lib/utils';
import type { BulkJobResponse, BulkJobStatus } from '@/lib/types';

/**
 * The job ledger.
 *
 * A list of jobs is a list, so it is a ledger and not a grid of cards: one
 * ink rule opens it, and every row is a job with its progress, its status
 * and the two things an administrator can do with it.
 *
 * Every number on the row is mono - the job id, the counts, the status. A
 * label states what the thing is; it does not shout.
 */

/**
 * The tone a status carries.
 *
 * Green for a job that finished, amber for one that is on its way, red for
 * one that failed, zinc for one that was cancelled - the status keeps its
 * meaning in both themes.
 */
export function jobTone(status: BulkJobStatus): MonoTone {
  switch (status) {
    case 'completed':
      return 'success';
    case 'failed':
      return 'destructive';
    case 'running':
    case 'pending':
      return 'warning';
    case 'cancelled':
      return 'neutral';
    default:
      return 'neutral';
  }
}

/** The progress of a job, clamped into the range a bar can draw. */
export function jobProgress(job: BulkJobResponse): {
  percent: number;
  processed: number;
  total: number;
} {
  const percent = Math.max(0, Math.min(100, Number(job.progress_percent ?? 0)));
  return {
    percent,
    processed: Number(job.records_processed ?? 0),
    total: Number(job.records_total ?? 0),
  };
}

/** A job that is still on its way can be cancelled; a finished one cannot. */
export function canCancel(job: BulkJobResponse): boolean {
  return job.status === 'running' || job.status === 'pending';
}

/** A job that is over can be deleted; a running one cannot. */
export function canDelete(job: BulkJobResponse): boolean {
  return job.status === 'completed' || job.status === 'failed' || job.status === 'cancelled';
}

export interface JobLedgerProps {
  jobs: BulkJobResponse[];
  onCancel?: (job: BulkJobResponse) => void;
  onDelete?: (job: BulkJobResponse) => void;
  className?: string;
}

export function JobLedger({ jobs, onCancel, onDelete, className }: JobLedgerProps) {
  const t = useTranslations('pages.admin.bulkJobs.ledger');
  const tStatus = useTranslations('pages.admin.bulkJobs.status');

  if (jobs.length === 0) {
    return <p className="text-annot text-muted-foreground">{t('empty')}</p>;
  }

  return (
    <Ledger className={className}>
      <div className="hidden gap-4 pb-2 pt-2.5 text-annot text-muted-foreground md:grid md:grid-cols-[120px_150px_minmax(0,1fr)_140px_150px]">
        <span>{t('columns.job')}</span>
        <span>{t('columns.type')}</span>
        <span>{t('columns.progress')}</span>
        <span>{t('columns.status')}</span>
        <span className="text-right">{t('columns.actions')}</span>
      </div>

      {jobs.map((job) => {
        const progress = jobProgress(job);
        return (
          <LedgerRow
            key={job.id}
            className="grid-cols-1 gap-x-4 gap-y-1.5 md:grid-cols-[120px_150px_minmax(0,1fr)_140px_150px] md:items-center"
          >
            <Cell label={t('columns.job')}>
              <MonoAnnotation className="font-medium text-foreground">{job.id}</MonoAnnotation>
            </Cell>

            <Cell label={t('columns.type')}>
              <span className="text-app text-foreground">{job.job_type}</span>
              <MonoAnnotation className="md:ml-1.5">{job.source_type}</MonoAnnotation>
            </Cell>

            <Cell label={t('columns.progress')}>
              <div className="flex items-center gap-2">
                <span className="h-1.5 w-full min-w-[80px] overflow-hidden rounded-[1px] bg-muted">
                  <span
                    className="block h-full rounded-[1px] bg-foreground"
                    style={{ width: `${progress.percent}%` }}
                  />
                </span>
                <MonoAnnotation className="shrink-0">
                  {t('records', { processed: progress.processed, total: progress.total })}
                </MonoAnnotation>
              </div>
              {job.records_failed > 0 ? (
                <MonoAnnotation tone="destructive" className="mt-0.5 block">
                  {t('failedRecords', { count: job.records_failed })}
                </MonoAnnotation>
              ) : null}
              {job.error_message ? (
                <MonoAnnotation tone="destructive" className="mt-0.5 block">
                  {job.error_message}
                </MonoAnnotation>
              ) : null}
            </Cell>

            <Cell label={t('columns.status')}>
              <MonoAnnotation tone={jobTone(job.status)} className="font-medium">
                {tStatus(job.status)}
              </MonoAnnotation>
              <MonoAnnotation className="mt-0.5 block">
                {t('created', { date: formatDate(job.created_at) })}
              </MonoAnnotation>
            </Cell>

            <Cell label={t('columns.actions')} className="md:justify-end">
              <div className="flex items-center justify-end gap-3">
                {canCancel(job) && onCancel ? (
                  <button
                    type="button"
                    onClick={() => onCancel(job)}
                    className="rounded-sm text-app font-medium text-foreground transition-colors hover:underline"
                  >
                    {t('actions.cancel')}
                  </button>
                ) : null}
                {job.result_url ? (
                  <a
                    href={job.result_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="rounded-sm text-app font-medium text-foreground transition-colors hover:underline"
                  >
                    {t('actions.download')}
                  </a>
                ) : null}
                {canDelete(job) && onDelete ? (
                  <button
                    type="button"
                    onClick={() => onDelete(job)}
                    className="rounded-sm text-app text-muted-foreground transition-colors hover:text-foreground hover:underline"
                  >
                    {t('actions.delete')}
                  </button>
                ) : null}
              </div>
            </Cell>
          </LedgerRow>
        );
      })}
    </Ledger>
  );
}

/**
 * A cell of the ledger.
 *
 * On a wide screen the column header says what the cell is; on a narrow one
 * the header is gone, so the cell carries its own label.
 */
function Cell({
  label,
  children,
  className,
}: {
  label: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={cn('flex min-w-0 flex-col gap-0.5 md:block', className)}>
      <span className="text-annot text-muted-foreground md:hidden">{label}</span>
      {children}
    </div>
  );
}

/** The moment a job was created, in the reader's own locale. */
export function formatDate(value?: string): string {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '—';
  return date.toLocaleDateString();
}
