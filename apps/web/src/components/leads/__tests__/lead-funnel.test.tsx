import { render, screen } from '@testing-library/react';

import { LeadFunnel, buildFunnelStages } from '../lead-funnel';
import type { LeadStatus, LeadWithScore } from '@/lib/types';

/**
 * The funnel.
 *
 * The counting is the part worth a test: a lead that moved on is counted
 * at every stage it passed, and a lost lead is counted only where it left.
 */

function makeLead(status: LeadStatus, id = `${status}-1`): LeadWithScore {
  return {
    id,
    visitor_id: 'v1',
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
  };
}

describe('buildFunnelStages', () => {
  it('counts an empty board as an empty funnel', () => {
    const stages = buildFunnelStages([]);

    expect(stages.map((stage) => stage.value)).toEqual([0, 0, 0, 0]);
    // The first stage has nothing to be a percentage of.
    expect(stages[0].rate).toBeNull();
  });

  it('counts a lead at every stage it passed', () => {
    const stages = buildFunnelStages([makeLead('converted')]);

    // One lead, and it reached the last stage, so every stage counts it.
    expect(stages.map((stage) => stage.value)).toEqual([1, 1, 1, 1]);
    expect(stages[1].rate).toBe(100);
  });

  it('stops counting a lead that was lost', () => {
    const stages = buildFunnelStages([
      makeLead('new', 'a'),
      makeLead('contacted', 'b'),
      makeLead('lost', 'c'),
    ]);

    // Every lead counts at the first stage. Contacted counts the leads that
    // got there - a lost lead stopped before it, because the API carries
    // only where the lead stands, not how it got there.
    expect(stages.map((stage) => stage.value)).toEqual([3, 1, 0, 0]);
    expect(stages[1].rate).toBe(33);
  });

  it('has no rate for the first stage', () => {
    const stages = buildFunnelStages([makeLead('qualified')]);

    // The first stage has nothing before it to be a share of.
    expect(stages[0].rate).toBeNull();
    expect(stages[0].value).toBe(1);
  });
});

describe('LeadFunnel', () => {
  it('states each stage and its rate', () => {
    const stages = buildFunnelStages([makeLead('converted'), makeLead('new', 'b')]);

    render(<LeadFunnel stages={stages} />);

    expect(screen.getByText('Leads')).toBeInTheDocument();
    expect(screen.getByText('Contacted')).toBeInTheDocument();
    // Two leads, one of them contacted.
    expect(screen.getByText('50% of previous')).toBeInTheDocument();
  });
});
