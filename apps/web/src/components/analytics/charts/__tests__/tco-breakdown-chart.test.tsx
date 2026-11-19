/**
 * Tests for the TCO breakdown chart (Task #96).
 *
 * The chart prints the category split twice: once as the accessible label of
 * the pie (`role="img"`, the categories that are not zero) and once as the
 * three cost groups under it. Both are asserted here.
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import { TCOBreakdownChart } from '../tco-breakdown-chart';
import type { TCOResult } from '@/lib/types';
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

/** The currency shape the chart prints: whole dollars, no cents. */
const usd = (value: number): string =>
  `$${value.toLocaleString(undefined, { maximumFractionDigits: 0 })}`;

const tcoResult: TCOResult = {
  monthly_payment: 2533.43,
  total_interest: 412033.64,
  down_payment: 80000,
  loan_amount: 320000,
  monthly_mortgage: 2533.43,
  monthly_property_tax: 333.33,
  monthly_insurance: 100,
  monthly_hoa: 300,
  monthly_utilities: 150,
  monthly_internet: 60,
  monthly_parking: 0,
  monthly_maintenance: 333.33,
  monthly_tco: 3810.09,
  annual_mortgage: 30401.16,
  annual_property_tax: 4000,
  annual_insurance: 1200,
  annual_hoa: 3600,
  annual_utilities: 1800,
  annual_internet: 720,
  annual_parking: 0,
  annual_maintenance: 4000,
  annual_tco: 45721.16,
  total_ownership_cost: 1143029,
  total_all_costs: 1223029,
  breakdown: {
    mortgage: 2533.43,
    property_tax: 333.33,
    insurance: 100,
    hoa: 300,
    utilities: 150,
    internet: 60,
    parking: 0,
    maintenance: 333.33,
  },
};

describe('TCOBreakdownChart', () => {
  it('renders the default title and description', () => {
    render(<TCOBreakdownChart tcoResult={tcoResult} />);

    expect(screen.getByText(copy('mortgage', 'charts.breakdown.title'))).toBeInTheDocument();
    expect(
      screen.getByText(copy('mortgage', 'charts.breakdown.description'))
    ).toBeInTheDocument();
  });

  it('uses the title and the description it is given', () => {
    render(<TCOBreakdownChart tcoResult={tcoResult} title="Monthly spend" description="By category" />);

    expect(screen.getByText('Monthly spend')).toBeInTheDocument();
    expect(screen.getByText('By category')).toBeInTheDocument();
    expect(
      screen.queryByText(copy('mortgage', 'charts.breakdown.title'))
    ).not.toBeInTheDocument();
  });

  it('renders no heading when the title and the description are empty', () => {
    // The card around the chart carries the title. An empty heading is
    // still a heading, and a screen reader reads it as one.
    const { container } = render(
      <TCOBreakdownChart tcoResult={tcoResult} title="" description="" />
    );

    expect(container.querySelector('h3')).toBeNull();
    expect(
      screen.queryByText(copy('mortgage', 'charts.breakdown.title'))
    ).not.toBeInTheDocument();
  });

  it('names every non-zero category in the accessible label of the pie', () => {
    render(<TCOBreakdownChart tcoResult={tcoResult} />);

    const label = screen.getByRole('img').getAttribute('aria-label') ?? '';

    expect(label).toContain(copy('mortgage', 'charts.breakdown.categories.mortgage'));
    expect(label).toContain(usd(tcoResult.monthly_mortgage));
    expect(label).toContain(usd(tcoResult.monthly_property_tax));
    expect(label).toContain(usd(tcoResult.monthly_hoa));
    expect(label).toContain(usd(tcoResult.monthly_utilities));
    expect(label).toContain(usd(tcoResult.monthly_internet));
    expect(label).toContain(usd(tcoResult.monthly_maintenance));

    // A category that costs nothing is not in the pie.
    expect(label).not.toContain(copy('mortgage', 'charts.breakdown.categories.parking'));
  });

  it('prints the three cost groups with the numbers from the props', () => {
    render(<TCOBreakdownChart tcoResult={tcoResult} />);

    const fixed =
      tcoResult.monthly_mortgage +
      tcoResult.monthly_property_tax +
      tcoResult.monthly_insurance +
      tcoResult.monthly_hoa;
    const variable = tcoResult.monthly_utilities + tcoResult.monthly_maintenance;
    const discretionary = tcoResult.monthly_internet + tcoResult.monthly_parking;

    expect(screen.getByText(copy('mortgage', 'charts.breakdown.fixedCosts'))).toBeInTheDocument();
    expect(screen.getByText(usd(fixed))).toBeInTheDocument();

    expect(screen.getByText(copy('mortgage', 'charts.breakdown.variableCosts'))).toBeInTheDocument();
    expect(screen.getByText(usd(variable))).toBeInTheDocument();

    expect(screen.getByText(copy('mortgage', 'charts.breakdown.discretionary'))).toBeInTheDocument();
    expect(screen.getByText(usd(discretionary))).toBeInTheDocument();
  });

  it('renders an empty chart without a blank', () => {
    const empty: TCOResult = {
      ...tcoResult,
      monthly_mortgage: 0,
      monthly_property_tax: 0,
      monthly_insurance: 0,
      monthly_hoa: 0,
      monthly_utilities: 0,
      monthly_internet: 0,
      monthly_parking: 0,
      monthly_maintenance: 0,
      monthly_tco: 0,
    };

    render(<TCOBreakdownChart tcoResult={empty} />);

    // The card, its title and the three groups are still there.
    expect(screen.getByText(copy('mortgage', 'charts.breakdown.title'))).toBeInTheDocument();
    expect(screen.getAllByText(usd(0))).toHaveLength(3);

    // The pie carries no category, and it says so rather than staying blank.
    const label = screen.getByRole('img').getAttribute('aria-label') ?? '';
    expect(label.trim()).toBe(
      copy('mortgage', 'charts.breakdown.ariaLabel').replace('{categories}', '').trim()
    );
  });
});
