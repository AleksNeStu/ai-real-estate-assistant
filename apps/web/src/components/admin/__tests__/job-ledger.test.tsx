import { render, screen } from '@testing-library/react';

import { JobLedger, canCancel, canDelete, jobProgress, jobTone } from '../job-ledger';
import type { BulkJobResponse, BulkJobStatus } from '@/lib/types';

/**
 * The job ledger.
 *
 * The ledger holds a job per row, with its progress and its status, and it
 * offers the two things an administrator can do with a job - and only those.
 */

function makeJob(overrides: Partial<BulkJobResponse> = {}): BulkJobResponse {
  return {
    id: 'J-1042',
    job_type: 'import',
    source_type: 'url',
    status: 'completed',
    records_total: 1240,
    records_processed: 1240,
    records_failed: 0,
    progress_percent: 100,
    created_at: '2026-11-08T09:00:00Z',
    ...overrides,
  };
}

describe('jobTone', () => {
  it('gives every status its meaning', () => {
    const cases: Array<[BulkJobStatus, string]> = [
      ['completed', 'success'],
      ['failed', 'destructive'],
      ['running', 'warning'],
      ['pending', 'warning'],
      ['cancelled', 'neutral'],
    ];
    for (const [status, tone] of cases) {
      expect(jobTone(status)).toBe(tone);
    }
  });
});

describe('jobProgress', () => {
  it('clamps the percentage into the range a bar can draw', () => {
    expect(jobProgress(makeJob({ progress_percent: 140 })).percent).toBe(100);
    expect(jobProgress(makeJob({ progress_percent: -5 })).percent).toBe(0);
  });

  it('carries the counts of the records', () => {
    const progress = jobProgress(makeJob({ records_processed: 812, records_total: 1270 }));
    expect(progress.processed).toBe(812);
    expect(progress.total).toBe(1270);
  });
});

describe('canCancel and canDelete', () => {
  it('cancels a job that is on its way and deletes a job that is over', () => {
    expect(canCancel(makeJob({ status: 'running' }))).toBe(true);
    expect(canCancel(makeJob({ status: 'completed' }))).toBe(false);
    expect(canDelete(makeJob({ status: 'failed' }))).toBe(true);
    expect(canDelete(makeJob({ status: 'running' }))).toBe(false);
  });
});

describe('JobLedger', () => {
  it('holds a job per row, with its records and its status', () => {
    render(
      <JobLedger
        jobs={[
          makeJob(),
          makeJob({
            id: 'J-1043',
            status: 'running',
            progress_percent: 64,
            records_processed: 812,
            records_total: 1270,
          }),
        ]}
      />
    );

    expect(screen.getByText('J-1042')).toBeInTheDocument();
    expect(screen.getByText('J-1043')).toBeInTheDocument();
    expect(screen.getByText('1240 / 1240')).toBeInTheDocument();
    expect(screen.getByText('812 / 1270')).toBeInTheDocument();
    expect(screen.getByText('Completed')).toBeInTheDocument();
    expect(screen.getByText('Running')).toBeInTheDocument();
  });

  it('offers cancel only for a running job', () => {
    render(
      <JobLedger
        jobs={[makeJob({ status: 'running' }), makeJob({ id: 'J-2', status: 'completed' })]}
        onCancel={jest.fn()}
        onDelete={jest.fn()}
      />
    );

    expect(screen.getAllByRole('button', { name: 'Cancel' })).toHaveLength(1);
  });

  it('offers delete only for a job that is over', () => {
    render(
      <JobLedger
        jobs={[makeJob({ status: 'running' }), makeJob({ id: 'J-2', status: 'failed' })]}
        onCancel={jest.fn()}
        onDelete={jest.fn()}
      />
    );

    expect(screen.getAllByRole('button', { name: 'Delete' })).toHaveLength(1);
  });

  it('says when there is no job at all', () => {
    render(<JobLedger jobs={[]} />);
    expect(screen.getByText(/No jobs yet/)).toBeInTheDocument();
  });
});
