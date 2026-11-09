import { render, screen } from '@testing-library/react';

import { ForecastChart } from '../forecast-chart';
import type { PriceForecastResponse } from '@/lib/api/tools';

/**
 * The forecast, drawn.
 *
 * The chart lives inside a chart frame: a title, a caption and an area
 * whose height is reserved, so the page does not move when the chart lands.
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
    drivers: [],
    explanation: '',
    comparables_used: 22,
    disclaimer: '',
    ...overrides,
  };
}

describe('ForecastChart', () => {
  it('sits in a chart frame with a title and a caption', () => {
    render(<ForecastChart result={makeResult()} />);

    expect(screen.getByText('Price forecast')).toBeInTheDocument();
    expect(screen.getByText('2 horizons · confidence band')).toBeInTheDocument();
    expect(screen.getByTestId('chart-frame-area')).toBeInTheDocument();
  });

  it('draws the line, the band and every horizon', () => {
    const { container } = render(<ForecastChart result={makeResult()} />);

    const svg = container.querySelector('svg');
    expect(svg).toBeInTheDocument();
    // The band is one polygon, the line one path.
    expect(container.querySelectorAll('path')).toHaveLength(2);
    // Today plus the two horizons.
    expect(container.querySelectorAll('circle')).toHaveLength(3);
  });

  it('labels the horizons on the axis', () => {
    render(<ForecastChart result={makeResult()} />);

    expect(screen.getByText('Today')).toBeInTheDocument();
    expect(screen.getByText('+1y')).toBeInTheDocument();
    expect(screen.getByText('+3y')).toBeInTheDocument();
  });

  it('says so when the forecast carries a single point', () => {
    render(
      <ForecastChart
        result={makeResult({
          forecast: [],
          horizon_years: [],
        })}
      />
    );

    expect(screen.getByText('The forecast carries a single point.')).toBeInTheDocument();
    expect(screen.queryByTestId('valuation-forecast-chart')).not.toBeInTheDocument();
  });
});
