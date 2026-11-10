import { render, screen } from '@testing-library/react';

import {
  AlertsLedger,
  MonitoringStats,
  buildAlerts,
  formatUptime,
} from '../monitoring-panels';
import type { HealthStatus, MonitoringOverview, ReadinessStatus } from '@/lib/api/admin';

/**
 * The monitoring panels.
 *
 * The stats say what the deployment measures, and the alerts say what it
 * broke. Neither of them invents a number the API did not carry.
 */

const HEALTH: HealthStatus = {
  status: 'healthy',
  timestamp: '2026-11-08T12:00:00Z',
  service: 'api',
  version: '5.1.10',
  uptime_seconds: 3900,
};

const READY: ReadinessStatus = {
  database: 'healthy',
  database_latency_ms: 420,
  redis: 'healthy',
  llm: 'healthy',
  overall: 'ready',
  timestamp: '2026-11-08T12:00:00Z',
};

const OVERVIEW: MonitoringOverview = {
  database: { total_properties: 252, recent_properties_24h: 3, by_source: { seed: 252 } },
  cache: { hits: 90, misses: 10, hit_rate: 90 },
  knowledge_store: { documents: 1492, chunks: 8201 },
  llm: { default_provider: 'minimax', default_model: 'MiniMax-M2' },
  environment: 'production',
  timestamp: '2026-11-08T12:00:00Z',
};

describe('buildAlerts', () => {
  it('raises nothing when every threshold is inside its bound', () => {
    expect(buildAlerts(READY, OVERVIEW)).toEqual([]);
  });

  it('raises an alert when the database answers too slowly', () => {
    const alerts = buildAlerts({ ...READY, database_latency_ms: 5000 }, OVERVIEW);
    expect(alerts.map((alert) => alert.id)).toContain('db-latency');
  });

  it('raises an alert when the cache is colder than it should be', () => {
    const alerts = buildAlerts(READY, { ...OVERVIEW, cache: { hit_rate: 5 } });
    expect(alerts.map((alert) => alert.id)).toContain('cache-hit-rate');
  });

  it('raises an alert when the deployment is not ready', () => {
    const alerts = buildAlerts({ ...READY, overall: 'not_ready' }, OVERVIEW);
    expect(alerts.map((alert) => alert.id)).toContain('not-ready');
  });
});

describe('formatUptime', () => {
  it('says the hours and the minutes', () => {
    expect(formatUptime(3900)).toBe('1h 5m');
  });
});

describe('MonitoringStats', () => {
  it('shows the measurements the API carried', () => {
    render(<MonitoringStats health={HEALTH} readiness={READY} overview={OVERVIEW} />);

    expect(screen.getByText('Healthy')).toBeInTheDocument();
    expect(screen.getByText('Ready')).toBeInTheDocument();
    expect(screen.getByText('420 ms')).toBeInTheDocument();
    expect(screen.getByText('90.0%')).toBeInTheDocument();
    expect(screen.getByText('1,492')).toBeInTheDocument();
  });

  it('says that there is no cache data when there is none', () => {
    render(
      <MonitoringStats
        health={HEALTH}
        readiness={READY}
        overview={{ ...OVERVIEW, cache: {} }}
      />
    );

    expect(screen.getByText('No cache data')).toBeInTheDocument();
  });
});

describe('AlertsLedger', () => {
  it('says when nothing is wrong', () => {
    render(<AlertsLedger alerts={[]} />);
    expect(screen.getByText(/No alerts/)).toBeInTheDocument();
  });

  it('holds a row per alert, with its threshold', () => {
    render(<AlertsLedger alerts={buildAlerts({ ...READY, overall: 'not_ready' }, OVERVIEW)} />);

    expect(
      screen.getByText('Service is not ready to handle requests')
    ).toBeInTheDocument();
    expect(screen.getByText(/Overall readiness/)).toBeInTheDocument();
  });
});
