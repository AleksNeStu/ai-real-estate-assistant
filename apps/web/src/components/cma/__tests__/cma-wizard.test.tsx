import { fireEvent, render, screen, waitFor } from '@testing-library/react';

import { CMAWizard } from '../cma-wizard';
import type { CMAComparable, Property } from '@/lib/types';

/**
 * The wizard, step by step.
 *
 * The acceptance of this route is that the five steps work end to end: a
 * subject is picked, comparables are chosen, the adjustments are reviewed,
 * the report is generated and the export follows.
 */

jest.mock('@/lib/api', () => ({
  searchProperties: jest.fn(),
  findComparables: jest.fn(),
  generateCMAReport: jest.fn(),
  downloadCMAPdf: jest.fn(),
  ApiError: class MockApiError extends Error {},
}));

import { searchProperties, findComparables, generateCMAReport } from '@/lib/api';

const subject: Property = {
  id: 'prop-1',
  title: 'Flat on Nowa Huta',
  address: 'os. Centrum C 14',
  city: 'Kraków',
  district: 'Nowa Huta',
  property_type: 'apartment',
  listing_type: 'sale',
  has_parking: false,
  has_garden: false,
  has_pool: false,
  has_garage: false,
  has_bike_room: false,
  price: 489000,
  currency: 'PLN',
  area_sqm: 46,
  rooms: 2,
  year_built: 1978,
};

function makeComparable(index: number): CMAComparable {
  return {
    property_id: `comp-${index}`,
    similarity_score: 80 - index,
    adjusted_price: 470000 + index * 1000,
    currency: 'PLN',
    adjustments: [
      {
        category: 'size',
        description: '5 m² apart',
        subject_value: '46 m²',
        comp_value: '51 m²',
        adjustment_percent: 1.5,
        adjustment_amount: 7050,
        confidence: 0.9,
      },
    ],
  };
}

const report = {
  id: 'report-1',
  user_id: 'u1',
  status: 'completed' as const,
  subject_property: {},
  comparables: [makeComparable(0), makeComparable(1), makeComparable(2)],
  valuation: {
    estimated_value: 512000,
    value_range_low: 495000,
    value_range_high: 529000,
    confidence_score: 72,
    price_per_sqm: 11130,
  },
  market_trend: 'rising',
  market_avg_price_per_sqm: 10800,
  subject_price: 489000,
  created_at: '2026-11-08T10:00:00Z',
  expires_at: null,
};

describe('CMAWizard', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (searchProperties as jest.Mock).mockResolvedValue({
      results: [{ property: subject, score: 0.95 }],
      count: 1,
    });
    (findComparables as jest.Mock).mockResolvedValue([
      makeComparable(0),
      makeComparable(1),
      makeComparable(2),
    ]);
    (generateCMAReport as jest.Mock).mockResolvedValue(report);
  });

  it('numbers the five steps on the rule', () => {
    render(<CMAWizard />);

    expect(screen.getByText('01')).toBeInTheDocument();
    expect(screen.getByText('02')).toBeInTheDocument();
    expect(screen.getByText('05')).toBeInTheDocument();
    expect(screen.getByText('step 1 of 5')).toBeInTheDocument();
  });

  it('does not let the reader leave the subject step without one', () => {
    render(<CMAWizard />);

    expect(screen.getByRole('button', { name: 'Next' })).toBeDisabled();
  });

  it('walks the five steps end to end', async () => {
    render(<CMAWizard />);

    // Step 1 - the subject.
    fireEvent.change(screen.getByLabelText('Search for the subject property'), {
      target: { value: 'Nowa Huta' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Search' }));

    await waitFor(() => expect(screen.getByText('Kraków, Nowa Huta')).toBeInTheDocument());
    fireEvent.click(screen.getByText('Kraków, Nowa Huta'));

    await waitFor(() => expect(screen.getByText('os. Centrum C 14, Nowa Huta')).toBeInTheDocument());
    expect(screen.getByRole('button', { name: 'Next' })).not.toBeDisabled();
    fireEvent.click(screen.getByRole('button', { name: 'Next' }));

    // Step 2 - the comparables.
    await waitFor(() => expect(screen.getByText('Comparables')).toBeInTheDocument());
    await waitFor(() => expect(screen.getByText('Property comp-0')).toBeInTheDocument());
    fireEvent.click(screen.getByRole('button', { name: 'Next' }));

    // Step 3 - the adjustments.
    expect(screen.getByText('Avg Adjustment')).toBeInTheDocument();
    expect(screen.getAllByText('size')).toHaveLength(3);
    fireEvent.click(screen.getByRole('button', { name: 'Next' }));

    // Step 4 - the report.
    await waitFor(() => expect(screen.getByText('CMA · os. Centrum C 14')).toBeInTheDocument());
    expect(screen.getByText('Estimated Market Value')).toBeInTheDocument();
    expect(screen.getByText('Asking vs value')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Continue to export' }));

    // Step 5 - the export.
    expect(screen.getByRole('button', { name: 'Download PDF' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Download JSON' })).toBeInTheDocument();
  });

  it('states the report the API generated', async () => {
    render(<CMAWizard />);

    fireEvent.change(screen.getByLabelText('Search for the subject property'), {
      target: { value: 'Nowa Huta' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Search' }));
    await waitFor(() => expect(screen.getByText('Kraków, Nowa Huta')).toBeInTheDocument());
    fireEvent.click(screen.getByText('Kraków, Nowa Huta'));
    fireEvent.click(screen.getByRole('button', { name: 'Next' }));

    await waitFor(() => expect(screen.getByText('Property comp-0')).toBeInTheDocument());
    fireEvent.click(screen.getByRole('button', { name: 'Next' }));
    fireEvent.click(screen.getByRole('button', { name: 'Next' }));

    await waitFor(() => expect(generateCMAReport).toHaveBeenCalled());
    // The indicated value and the range come from the report the API made.
    expect(screen.getByText('PLN 512,000')).toBeInTheDocument();
    expect(screen.getByText('PLN 495,000 – PLN 529,000')).toBeInTheDocument();
    // The asking price the report carries, against the indicated value.
    expect(screen.getByText('-4.5%')).toBeInTheDocument();
  });
});
