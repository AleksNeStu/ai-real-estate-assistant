import { render, screen } from '@testing-library/react';
import type { ReactNode } from 'react';

import { MarketTrendsCharts } from '../MarketTrendsCharts';

/**
 * The price curve and the listing volume.
 *
 * The charts sit in a chart frame: the title above, the note beside it, and
 * the space for the chart held open - so the page does not move when the
 * bundle arrives.
 */
jest.mock('recharts', () => ({
  LineChart: ({ children }: { children: ReactNode }) => (
    <div data-testid="line-chart">{children}</div>
  ),
  Line: () => null,
  XAxis: () => null,
  YAxis: () => null,
  CartesianGrid: () => null,
  Tooltip: () => null,
  ResponsiveContainer: ({ children }: { children: ReactNode }) => (
    <div data-testid="responsive-container">{children}</div>
  ),
  BarChart: ({ children }: { children: ReactNode }) => (
    <div data-testid="bar-chart">{children}</div>
  ),
  Bar: () => null,
}));

const chartData = [
  { period: '2024-01', avgPrice: 450000, medianPrice: 420000, volume: 120, currency: 'PLN' },
  { period: '2024-02', avgPrice: 460000, medianPrice: 430000, volume: 135, currency: 'PLN' },
];

describe('MarketTrendsCharts', () => {
  it('frames both charts with their titles', () => {
    render(<MarketTrendsCharts chartData={chartData} caption="12 months · Monthly" />);

    expect(screen.getByText('Average and Median Prices')).toBeInTheDocument();
    expect(screen.getByText('Listing Volume')).toBeInTheDocument();
  });

  it('holds the space of both charts open', () => {
    render(<MarketTrendsCharts chartData={chartData} />);

    const areas = screen.getAllByTestId('chart-frame-area');
    expect(areas).toHaveLength(2);
    expect(areas[0]).toHaveStyle({ minHeight: '280px' });
    expect(areas[1]).toHaveStyle({ minHeight: '200px' });
  });

  it('draws the note beside the title', () => {
    render(<MarketTrendsCharts chartData={chartData} caption="12 months · Monthly" />);

    expect(screen.getAllByText('12 months · Monthly')).toHaveLength(2);
  });

  it('draws the two charts', () => {
    render(<MarketTrendsCharts chartData={chartData} />);

    expect(screen.getByTestId('line-chart')).toBeInTheDocument();
    expect(screen.getByTestId('bar-chart')).toBeInTheDocument();
  });
});
