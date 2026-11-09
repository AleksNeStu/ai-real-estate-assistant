import { render, screen } from '@testing-library/react';

import { ForecastLedger } from '../forecast-ledger';
import type { PriceForecastResponse } from '@/lib/api/tools';

/**
 * The forecast as a row of numbers.
 *
 * Today is loud, every horizon is quieter, and under each value sits the
 * band the model is uncertain between. The band is the API's own lower and
 * upper bound - nothing here is derived from the form.
 */
function makeResult(overrides: Partial<PriceForecastResponse> = {}): PriceForecastResponse {
  return {
    current_estimate: 489000,
    currency: 'PLN',
    horizon_years: [1, 3],
    forecast: [
      { years_ahead: 1, estimated_value: 507000, lower_bound: 495000, upper_bound: 519000 },
      { years_ahead: 3, estimated_value: 545000, lower_bound: 518000, upper_bound: 572000 },
    ],
    confidence: 0.62,
    drivers: ['below-median price per sqm'],
    explanation: 'A short explanation.',
    comparables_used: 22,
    disclaimer: 'Not a formal appraisal.',
    ...overrides,
  };
}

describe('ForecastLedger', () => {
  it('states today loud and every horizon quieter', () => {
    render(<ForecastLedger result={makeResult()} />);

    expect(screen.getByText('Today')).toBeInTheDocument();
    expect(screen.getByText('PLN 489,000')).toBeInTheDocument();
    expect(screen.getByText('1 year')).toBeInTheDocument();
    expect(screen.getByText('3 years')).toBeInTheDocument();
    expect(screen.getByText('PLN 507,000')).toBeInTheDocument();
    expect(screen.getByText('PLN 545,000')).toBeInTheDocument();
  });

  it('gives every horizon the band it came with', () => {
    render(<ForecastLedger result={makeResult()} />);

    expect(screen.getByText('495K-519K zł')).toBeInTheDocument();
    expect(screen.getByText('518K-572K zł')).toBeInTheDocument();
  });

  it('carries no band under today', () => {
    render(<ForecastLedger result={makeResult()} />);

    // Today is the estimate itself - there is nothing to be uncertain about.
    expect(screen.getAllByText(/PLN/)).toHaveLength(3);
  });

  it('draws one column per horizon the API returned', () => {
    render(
      <ForecastLedger
        result={makeResult({
          forecast: [
            { years_ahead: 5, estimated_value: 586000, lower_bound: 545000, upper_bound: 627000 },
          ],
        })}
      />
    );

    expect(screen.getByText('5 years')).toBeInTheDocument();
    expect(screen.queryByText('1 year')).not.toBeInTheDocument();
  });
});
