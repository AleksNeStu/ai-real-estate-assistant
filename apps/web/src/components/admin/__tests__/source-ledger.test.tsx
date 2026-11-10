import { render, screen } from '@testing-library/react';

import { PortalLedger, SourceLedger, sourceLastSync } from '../source-ledger';
import type { DataSource } from '@/lib/types';

/**
 * The source ledger and the portal ledger.
 *
 * A source says how many listings it brought and when it last ran; a portal
 * says whether it is configured and whether anything ever came through it.
 */

const NOW = Date.parse('2026-11-08T12:00:00Z');

function makeSource(overrides: Partial<DataSource> = {}): DataSource {
  return {
    id: 's-1',
    name: 'Demo catalogue (seed)',
    source_type: 'json',
    config: {},
    status: 'active',
    total_records: 252,
    health_score: 100,
    consecutive_failures: 0,
    auto_sync_enabled: false,
    created_at: '2026-11-01T09:00:00Z',
    updated_at: '2026-11-08T09:00:00Z',
    ...overrides,
  };
}

describe('sourceLastSync', () => {
  it('says never for a source that never ran', () => {
    expect(sourceLastSync(makeSource(), NOW).label).toBe('never');
  });

  it('counts the minutes, the hours and the days', () => {
    const minutes = sourceLastSync(makeSource({ last_sync_at: '2026-11-08T11:30:00Z' }), NOW);
    expect(minutes.label).toBe('minutesAgo');
    expect(minutes.minutes).toBe(30);

    const hours = sourceLastSync(makeSource({ last_sync_at: '2026-11-08T09:00:00Z' }), NOW);
    expect(hours.label).toBe('hoursAgo');
    expect(hours.hours).toBe(3);

    const days = sourceLastSync(makeSource({ last_sync_at: '2026-11-05T12:00:00Z' }), NOW);
    expect(days.label).toBe('daysAgo');
    expect(days.days).toBe(3);
  });
});

describe('SourceLedger', () => {
  it('holds a row per source, with its listings', () => {
    render(<SourceLedger sources={[makeSource()]} now={NOW} />);

    expect(screen.getByText('Demo catalogue (seed)')).toBeInTheDocument();
    expect(screen.getByText('252')).toBeInTheDocument();
    expect(screen.getByText('never')).toBeInTheDocument();
  });

  it('says when there is no source at all', () => {
    render(<SourceLedger sources={[]} now={NOW} />);
    expect(screen.getByText('No data sources configured yet.')).toBeInTheDocument();
  });
});

describe('PortalLedger', () => {
  it('says that a portal was never fetched from', () => {
    render(
      <PortalLedger
        adapters={[{ name: 'otwartek', display_name: 'Otwartek', configured: true, has_api_key: false }]}
        sources={[]}
      />
    );

    expect(screen.getByText('never fetched')).toBeInTheDocument();
  });

  it('counts the listings that came through a portal', () => {
    render(
      <PortalLedger
        adapters={[{ name: 'otwartek', display_name: 'Otwartek', configured: true, has_api_key: false }]}
        sources={[makeSource({ config: { portal: 'otwartek' }, total_records: 41 })]}
      />
    );

    expect(screen.getByText('41')).toBeInTheDocument();
  });

  it('says that a portal is not configured', () => {
    render(
      <PortalLedger
        adapters={[{ name: 'crm', display_name: 'CRM', configured: false, has_api_key: false }]}
        sources={[]}
      />
    );

    expect(screen.getByText('Not configured')).toBeInTheDocument();
  });
});
