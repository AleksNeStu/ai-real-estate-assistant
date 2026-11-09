import { render, screen } from '@testing-library/react';

import { HighValueRail } from '../high-value-rail';
import type { LeadStatus, LeadWithScore } from '@/lib/types';

/**
 * The high-value rail.
 *
 * The rail holds the leads the score says are worth the attention, ordered
 * by that score, and says so when there are none.
 */

function makeLead(
  id: string,
  total_score: number,
  status: LeadStatus = 'new'
): LeadWithScore {
  return {
    id,
    visitor_id: `v-${id}`,
    name: `Lead ${id}`,
    status,
    current_score: total_score,
    first_seen_at: '2026-11-01T10:00:00Z',
    last_activity_at: '2026-11-08T10:00:00Z',
    created_at: '2026-11-01T10:00:00Z',
    updated_at: '2026-11-08T10:00:00Z',
    consent_given: true,
    interaction_count: 3,
    total_score,
    search_activity_score: 10,
    engagement_score: 20,
    intent_score: 20,
  };
}

describe('HighValueRail', () => {
  it('keeps the leads over the threshold and drops the rest', () => {
    render(
      <HighValueRail
        leads={[makeLead('a', 91), makeLead('b', 52)]}
        threshold={80}
      />
    );

    expect(screen.getByText('Lead a')).toBeInTheDocument();
    expect(screen.queryByText('Lead b')).not.toBeInTheDocument();
  });

  it('orders the leads by their score', () => {
    render(
      <HighValueRail
        leads={[makeLead('a', 82), makeLead('b', 95)]}
        threshold={80}
      />
    );

    const rows = screen.getAllByTestId('high-value-lead');
    expect(rows[0]).toHaveTextContent('Lead b');
    expect(rows[1]).toHaveTextContent('Lead a');
  });

  it('says so when there is no high-value lead', () => {
    render(<HighValueRail leads={[makeLead('a', 12)]} threshold={80} />);

    expect(screen.getByText('No high-value leads yet')).toBeInTheDocument();
  });

  it('names the threshold it uses', () => {
    render(<HighValueRail leads={[]} threshold={80} />);

    expect(screen.getByText('score ≥ 80, not yet converted')).toBeInTheDocument();
  });
});
