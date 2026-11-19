/**
 * Tests for the TCO projection chart (Task #96).
 *
 * The chart prints the milestone years under the line: the cumulative cost, the
 * equity built and the property value, each in the short money shape the chart
 * uses (thousands below a million, millions above it).
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import { TCOProjectionChart } from '../tco-projection-chart';
import type { TCOProjection } from '@/lib/types';
import en from '../../../../../messages/en.json';

/**
 * Resolve a message from the English catalogue. The key is the fallback: that is
 * exactly what the next-intl mock renders when the catalogue does not carry the
 * message yet.
 */
const copy = (namespace: string, key: string): string => {
  const value = [namespace, key]
    .join('.')
    .split('.')
    .reduce<unknown>((acc, part) => (acc as Record<string, unknown> | undefined)?.[part], en);
  return typeof value === 'string' ? value : key;
};

/** The short money shape the chart prints. */
const short = (value: number): string =>
  value >= 1000000 ? `$${(value / 1000000).toFixed(1)}M` : `$${(value / 1000).toFixed(0)}K`;

const projection = (year: number, overrides: Partial<TCOProjection> = {}): TCOProjection => ({
  year,
  cumulative_cost: 50000 * year,
  cumulative_principal_paid: 10000 * year,
  cumulative_interest_paid: 40000 * year,
  cumulative_equity: 20000 * year,
  property_value_estimate: 400000 + year * 1000,
  loan_balance: 320000 - year * 15000,
  annual_cost: 50000,
  ...overrides,
});

const projections: TCOProjection[] = [
  projection(1),
  projection(5, {
    cumulative_cost: 250000,
    cumulative_equity: 80000,
    property_value_estimate: 450000,
    loan_balance: 280000,
  }),
  projection(10, {
    cumulative_cost: 600000,
    cumulative_equity: 220000,
    property_value_estimate: 520000,
    loan_balance: 190000,
  }),
  projection(20, {
    cumulative_cost: 1400000,
    cumulative_equity: 700000,
    property_value_estimate: 750000,
    loan_balance: 40000,
  }),
];

describe('TCOProjectionChart', () => {
  it('renders the title, the description and the accessible label of the chart', () => {
    render(<TCOProjectionChart projections={projections} />);

    expect(screen.getByText(copy('mortgage', 'charts.projection.title'))).toBeInTheDocument();
    expect(
      screen.getByText(copy('mortgage', 'charts.projection.description'))
    ).toBeInTheDocument();
    expect(screen.getByRole('img')).toHaveAttribute(
      'aria-label',
      copy('mortgage', 'charts.projection.ariaLabel')
    );
  });

  it('prints the milestone numbers of the highlighted years', () => {
    render(<TCOProjectionChart projections={projections} />);

    // Year 5.
    expect(screen.getByText('Year 5')).toBeInTheDocument();
    expect(screen.getByText(`Cost: ${short(250000)}`)).toBeInTheDocument();
    expect(screen.getByText(`Equity: ${short(80000)}`)).toBeInTheDocument();
    expect(screen.getByText(`Value: ${short(450000)}`)).toBeInTheDocument();

    // Year 10.
    expect(screen.getByText('Year 10')).toBeInTheDocument();
    expect(screen.getByText(`Cost: ${short(600000)}`)).toBeInTheDocument();
    expect(screen.getByText(`Equity: ${short(220000)}`)).toBeInTheDocument();
    expect(screen.getByText(`Value: ${short(520000)}`)).toBeInTheDocument();

    // Year 20 - a million and above is printed in millions.
    expect(screen.getByText('Year 20')).toBeInTheDocument();
    expect(screen.getByText(`Cost: ${short(1400000)}`)).toBeInTheDocument();
    expect(screen.getByText(`Cost: $1.4M`)).toBeInTheDocument();
    expect(screen.getByText(`Equity: ${short(700000)}`)).toBeInTheDocument();
    expect(screen.getByText(`Value: ${short(750000)}`)).toBeInTheDocument();

    // A year that is not highlighted carries no milestone.
    expect(screen.queryByText('Year 1')).not.toBeInTheDocument();
  });

  it('honours the highlighted years it is given', () => {
    render(<TCOProjectionChart projections={projections} highlightYears={[10]} />);

    expect(screen.getByText('Year 10')).toBeInTheDocument();
    expect(screen.queryByText('Year 5')).not.toBeInTheDocument();
    expect(screen.queryByText('Year 20')).not.toBeInTheDocument();
  });

  it('renders an empty chart without a blank', () => {
    render(<TCOProjectionChart projections={[]} />);

    expect(screen.getByText(copy('mortgage', 'charts.projection.title'))).toBeInTheDocument();
    expect(
      screen.getByText(copy('mortgage', 'charts.projection.description'))
    ).toBeInTheDocument();
    expect(screen.getByRole('img')).toBeInTheDocument();

    // No milestone, and no leftover year either.
    expect(screen.queryByText(/^Year /)).not.toBeInTheDocument();
  });
});
