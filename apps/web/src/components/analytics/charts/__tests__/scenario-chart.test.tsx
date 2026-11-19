/**
 * Tests for the appreciation scenario chart.
 *
 * The chart draws the three market scenarios over the years and names each of
 * them under the line: the rate it grows at and the total it grows by.
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import { ScenarioChart } from '../scenario-chart';
import type { AppreciationScenario } from '@/lib/types';
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

const scenario = (
  name: string,
  annualRate: number,
  projectedValues: Record<number, number>,
  totalPercent: number
): AppreciationScenario => ({
  name,
  annual_rate: annualRate,
  projected_values: projectedValues,
  total_appreciation_percent: totalPercent,
  total_appreciation_amount: 40000,
});

const scenarios: AppreciationScenario[] = [
  scenario('Pessimistic', -2, { 1: 294000, 2: 288120 }, -9.8),
  scenario('Realistic', 3, { 1: 329600, 2: 339488 }, 12.5),
];

describe('ScenarioChart', () => {
  it('renders the title, the description and the accessible label of the chart', () => {
    render(<ScenarioChart scenarios={scenarios} initialPrice={320000} />);

    expect(screen.getByText(copy('investment', 'charts.scenario.title'))).toBeInTheDocument();
    expect(
      screen.getByText(copy('investment', 'charts.scenario.description'))
    ).toBeInTheDocument();
    expect(screen.getByRole('img')).toHaveAttribute(
      'aria-label',
      copy('investment', 'charts.scenario.ariaLabel')
    );
  });

  it('names every scenario with its rate and its total', () => {
    render(<ScenarioChart scenarios={scenarios} initialPrice={320000} />);

    expect(screen.getByText(copy('investment', 'charts.scenario.pessimistic'))).toBeInTheDocument();
    expect(screen.getByText(copy('investment', 'charts.scenario.realistic'))).toBeInTheDocument();

    // The rate carries its own sign.
    expect(screen.getByText('-2%/year')).toBeInTheDocument();
    expect(screen.getByText('+3%/year')).toBeInTheDocument();
    expect(screen.getByText(`${copy('investment', 'charts.scenario.total')} +12.5%`)).toBeInTheDocument();
  });

  it('renders an empty chart without a blank', () => {
    render(<ScenarioChart scenarios={[]} initialPrice={320000} />);

    expect(screen.getByText(copy('investment', 'charts.scenario.title'))).toBeInTheDocument();
    expect(screen.getByRole('img')).toBeInTheDocument();
  });
});
