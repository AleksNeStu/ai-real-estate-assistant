import { render, screen } from '@testing-library/react';

import { LeadBoard, nextStatus } from '../lead-board';
import type { LeadStatus, LeadWithScore } from '@/lib/types';

/**
 * The board.
 *
 * The board's two jobs are to hold a lead in the right column and to offer
 * the one step forward it can take.
 */

function makeLead(status: LeadStatus, id: string, overrides: Partial<LeadWithScore> = {}): LeadWithScore {
  return {
    id,
    visitor_id: `v-${id}`,
    name: `Lead ${id}`,
    email: `${id}@example.com`,
    status,
    current_score: 50,
    first_seen_at: '2026-11-01T10:00:00Z',
    last_activity_at: '2026-11-08T10:00:00Z',
    created_at: '2026-11-01T10:00:00Z',
    updated_at: '2026-11-08T10:00:00Z',
    consent_given: true,
    interaction_count: 3,
    total_score: 50,
    search_activity_score: 10,
    engagement_score: 20,
    intent_score: 20,
    ...overrides,
  };
}

const NOW = Date.parse('2026-11-08T12:00:00Z');

describe('nextStatus', () => {
  it('moves a lead one stage along', () => {
    expect(nextStatus('new')).toBe('contacted');
    expect(nextStatus('contacted')).toBe('qualified');
    expect(nextStatus('qualified')).toBe('converted');
  });

  it('stops at the end of the pipeline', () => {
    expect(nextStatus('converted')).toBeNull();
    expect(nextStatus('lost')).toBeNull();
  });
});

describe('LeadBoard', () => {
  it('puts a lead in the column of its status', () => {
    render(<LeadBoard leads={[makeLead('qualified', 'a')]} now={NOW} />);

    const column = screen.getByRole('region', { name: 'Qualified' });
    expect(column).toBeInTheDocument();
    expect(screen.getByText('Lead a')).toBeInTheDocument();
  });

  it('counts the leads in a column', () => {
    render(
      <LeadBoard
        leads={[makeLead('new', 'a'), makeLead('new', 'b'), makeLead('new', 'c')]}
        now={NOW}
      />
    );

    const column = screen.getByRole('region', { name: 'New' });
    expect(column).toHaveTextContent('3');
  });

  it('shows the score in mono and marks a high one', () => {
    render(
      <LeadBoard leads={[makeLead('new', 'a', { total_score: 91 })]} now={NOW} />
    );

    expect(screen.getByText('91')).toBeInTheDocument();
  });

  it('offers the step forward and calls for it', () => {
    const onAdvance = jest.fn();
    render(
      <LeadBoard leads={[makeLead('new', 'a')]} onAdvance={onAdvance} now={NOW} />
    );

    screen.getByRole('button', { name: 'Advance →' }).click();
    expect(onAdvance).toHaveBeenCalledWith(expect.objectContaining({ id: 'a' }), 'contacted');
  });

  it('offers no step forward at the end of the pipeline', () => {
    render(
      <LeadBoard
        leads={[makeLead('converted', 'a')]}
        onAdvance={jest.fn()}
        now={NOW}
      />
    );

    expect(screen.queryByRole('button', { name: 'Advance →' })).not.toBeInTheDocument();
  });

  it('states the interest the lead carries', () => {
    render(
      <LeadBoard
        leads={[
          makeLead('new', 'a', {
            preferred_locations: ['Nowa Huta'],
            budget_max: 500000,
            source: 'website',
          }),
        ]}
        now={NOW}
      />
    );

    expect(screen.getByText('Nowa Huta · budget ≤ 500000 · website')).toBeInTheDocument();
  });

  it('says so when a column is empty', () => {
    render(<LeadBoard leads={[]} now={NOW} />);

    expect(screen.getAllByText('No leads here')).toHaveLength(5);
  });
});
