import { render, screen } from '@testing-library/react';

import { UsageEventLedger } from '../usage-event-ledger';

/**
 * The activity ledger.
 *
 * Three columns, a rule above them, and the note that says where the rest
 * of the log lives.
 */

const labels = { when: 'When', event: 'Event', detail: 'Detail' };

describe('UsageEventLedger', () => {
  it('states the three columns and every row', () => {
    render(
      <UsageEventLedger
        rows={[
          { when: '8 Nov', event: 'search', detail: '4 events' },
          { when: '7 Nov', event: 'tool_call', detail: '2 calls' },
        ]}
        labels={labels}
        emptyTitle="No activity in this period"
      />
    );

    expect(screen.getByText('When')).toBeInTheDocument();
    expect(screen.getByText('Event')).toBeInTheDocument();
    expect(screen.getByText('Detail')).toBeInTheDocument();
    expect(screen.getByText('8 Nov')).toBeInTheDocument();
    expect(screen.getByText('tool_call')).toBeInTheDocument();
    expect(screen.getByText('2 calls')).toBeInTheDocument();
  });

  it('says so when there is nothing to log', () => {
    render(<UsageEventLedger rows={[]} labels={labels} emptyTitle="No activity in this period" />);

    expect(screen.getByText('No activity in this period')).toBeInTheDocument();
  });

  it('says where the full log lives', () => {
    render(
      <UsageEventLedger
        rows={[{ when: '8 Nov', event: 'search', detail: '4 events' }]}
        labels={labels}
        note="The full log is in the CSV."
        emptyTitle="No activity in this period"
      />
    );

    expect(screen.getByText('The full log is in the CSV.')).toBeInTheDocument();
  });
});
