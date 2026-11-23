/**
 * The factors nobody could measure.
 *
 * A factor the map could not answer carries no score - the answer says so
 * in `components_without_data`, and the reader sees a dash. It never sees a
 * zero: a zero would say the neighbourhood is bad, and the map said
 * nothing about it.
 */

import { render, screen } from '@testing-library/react';
import { describe, it, expect } from '@jest/globals';
import type { NeighborhoodQualityResult } from '@/lib/types';
import { FactorBreakdown } from '../factor-breakdown';
import {
  NeighborhoodBadge,
  NeighborhoodScoreDisplay,
} from '@/components/analytics/neighborhood-badge';

function result(overrides: Partial<NeighborhoodQualityResult> = {}): NeighborhoodQualityResult {
  return {
    property_id: 'p1',
    overall_score: 70,
    safety_score: 75,
    schools_score: null,
    amenities_score: 68,
    walkability_score: 70,
    green_space_score: 60,
    air_quality_score: 65,
    noise_level_score: 55,
    public_transport_score: 62,
    factor_details: {},
    score_breakdown: {},
    data_sources: ['osm_overpass_api'],
    components_without_data: {
      schools: 'the provider could not be asked for the schools nearby',
    },
    ...overrides,
  };
}

describe('A factor nobody could measure', () => {
  it('is shown as a dash on the badge, never as a zero', () => {
    const { container } = render(<NeighborhoodBadge overallScore={null} />);

    expect(screen.getAllByText('—').length).toBeGreaterThan(0);
    expect(screen.queryByText('0.0')).not.toBeInTheDocument();
    expect(container.firstChild).toHaveAttribute('title', 'No neighborhood data available');
  });

  it('is shown as a dash in the breakdown, and the measured factors keep their score', () => {
    render(<FactorBreakdown result={result()} />);

    expect(screen.getByText('—')).toBeInTheDocument();
    expect(screen.getByText('68.0')).toBeInTheDocument();
    expect(screen.queryByText('0.0')).not.toBeInTheDocument();
  });

  it('is shown as a dash in the score display, and no bar is drawn for it', () => {
    const { container } = render(
      <NeighborhoodScoreDisplay
        result={{
          overall_score: 70,
          safety_score: 75,
          schools_score: null,
          amenities_score: 68,
          walkability_score: 70,
          green_space_score: 60,
        }}
      />,
    );

    expect(screen.getByText('—')).toBeInTheDocument();
    // Five factors, four of them measured: one bar less than the factors.
    expect(container.querySelectorAll('.w-32 > .h-2.rounded-full')).toHaveLength(4);
  });
});
