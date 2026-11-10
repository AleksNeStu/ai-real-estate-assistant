import { render, screen } from '@testing-library/react';

import { ConnectorLedger, connectorHealth, connectorState } from '../connector-ledger';
import type { MCPConnectorInfo } from '@/lib/types';

/**
 * The connector ledger.
 *
 * A row says what the connector does, what the last health check said about
 * it, and whether this deployment has it turned on.
 */

function makeConnector(overrides: Partial<MCPConnectorInfo> = {}): MCPConnectorInfo {
  return {
    name: 'filesystem',
    display_name: 'filesystem',
    description: 'Read uploaded documents for the RAG index',
    enabled: true,
    edition: 'community',
    status: 'active',
    accessible_in_ce: true,
    registered: true,
    has_instance: true,
    requires_api_key: false,
    supports_streaming: false,
    min_edition: 'community',
    ...overrides,
  };
}

describe('connectorState', () => {
  it('calls a connector that is not registered not configured', () => {
    expect(connectorState(makeConnector({ registered: false }))).toBe('notConfigured');
    expect(connectorState(makeConnector({ has_instance: false }))).toBe('notConfigured');
  });

  it('calls a connector that waits for a key one that needs a key', () => {
    expect(
      connectorState(makeConnector({ requires_api_key: true, enabled: false }))
    ).toBe('needsKey');
  });

  it('calls a connector that is on enabled and one that is off disabled', () => {
    expect(connectorState(makeConnector())).toBe('enabled');
    expect(connectorState(makeConnector({ enabled: false }))).toBe('disabled');
  });
});

describe('connectorHealth', () => {
  it('reports the health of the last check', () => {
    const health = connectorHealth(
      makeConnector(),
      {
        name: 'filesystem',
        status: 'unhealthy',
        success: false,
        errors: [],
        warnings: [],
        timestamp: '2026-11-08T09:00:00Z',
      }
    );
    expect(health.label).toBe('unhealthy');
    expect(health.tone).toBe('destructive');
  });

  it('does not claim a health it has not measured', () => {
    const health = connectorHealth(makeConnector());
    expect(health.label).toBe('notChecked');
    expect(health.tone).toBe('neutral');
  });
});

describe('ConnectorLedger', () => {
  it('holds a row per connector, with what it does', () => {
    render(<ConnectorLedger connectors={[makeConnector()]} />);

    expect(screen.getAllByText('filesystem').length).toBeGreaterThan(0);
    expect(screen.getByText('Read uploaded documents for the RAG index')).toBeInTheDocument();
    expect(screen.getByText('not checked')).toBeInTheDocument();
  });

  it('says that a connector is not configured', () => {
    render(
      <ConnectorLedger
        connectors={[makeConnector({ name: 'crm-webhook', display_name: 'crm-webhook', registered: false })]}
      />
    );

    expect(screen.getByText('Not configured')).toBeInTheDocument();
  });

  it('says that a connector waits for a key', () => {
    render(
      <ConnectorLedger
        connectors={[makeConnector({ requires_api_key: true, enabled: false })]}
      />
    );

    expect(screen.getByText('Needs a key')).toBeInTheDocument();
  });

  it('says when there is no connector at all', () => {
    render(<ConnectorLedger connectors={[]} />);
    expect(screen.getByText(/No connectors are registered/)).toBeInTheDocument();
  });
});
