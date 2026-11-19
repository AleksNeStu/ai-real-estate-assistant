/**
 * Tests for the TCO comparison component (Task #96).
 *
 * The component owns two things the API client does not: it turns the two
 * scenario forms into one `compareTCO` call, and it prints the answer - the
 * summary rows, the recommendation and the two scenario cards.
 */

import React from 'react';
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import { TCOComparison } from '../tco-comparison';
import { compareTCO, ApiError } from '@/lib/api';
import type { EnhancedTCOResult, TCOComparisonResult } from '@/lib/types';
import en from '../../../../messages/en.json';

// Only the client call is replaced; the rest of the barrel (the real `ApiError`
// the component branches on) stays the real thing.
jest.mock('@/lib/api', () => ({
  ...jest.requireActual('@/lib/api'),
  compareTCO: jest.fn(),
}));

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

/** The currency shape the component prints: whole dollars, no cents. */
const usd = (value: number): string =>
  `$${value.toLocaleString(undefined, { maximumFractionDigits: 0 })}`;

const scenarioA: EnhancedTCOResult = {
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
  projections: [
    {
      year: 1,
      cumulative_cost: 45000,
      cumulative_principal_paid: 12000,
      cumulative_interest_paid: 33000,
      cumulative_equity: 10000,
      property_value_estimate: 410000,
      loan_balance: 308000,
      annual_cost: 45000,
    },
    {
      year: 5,
      cumulative_cost: 250000,
      cumulative_principal_paid: 70000,
      cumulative_interest_paid: 180000,
      cumulative_equity: 80000,
      property_value_estimate: 450000,
      loan_balance: 280000,
      annual_cost: 46000,
    },
    {
      year: 10,
      cumulative_cost: 600000,
      cumulative_principal_paid: 190000,
      cumulative_interest_paid: 410000,
      cumulative_equity: 220000,
      property_value_estimate: 520000,
      loan_balance: 190000,
      annual_cost: 52000,
    },
  ],
  percentage_breakdown: { mortgage: 66.5, property_tax: 8.7 },
  fixed_costs_monthly: 3266.76,
  variable_costs_monthly: 483.33,
  discretionary_costs_monthly: 60,
};

const scenarioB: EnhancedTCOResult = {
  monthly_payment: 3200,
  total_interest: 640000,
  down_payment: 110000,
  loan_amount: 440000,
  monthly_mortgage: 3200,
  monthly_property_tax: 458.33,
  monthly_insurance: 125,
  monthly_hoa: 150,
  monthly_utilities: 200,
  monthly_internet: 60,
  monthly_parking: 100,
  monthly_maintenance: 458.33,
  monthly_tco: 4751.66,
  annual_mortgage: 38400,
  annual_property_tax: 5500,
  annual_insurance: 1500,
  annual_hoa: 1800,
  annual_utilities: 2400,
  annual_internet: 720,
  annual_parking: 1200,
  annual_maintenance: 5500,
  annual_tco: 57019.92,
  total_ownership_cost: 1800150,
  total_all_costs: 1910150,
  breakdown: {
    mortgage: 3200,
    property_tax: 458.33,
    insurance: 125,
    hoa: 150,
    utilities: 200,
    internet: 60,
    parking: 100,
    maintenance: 458.33,
  },
  // No projections for B: the component only charts the first scenario.
  projections: [],
  percentage_breakdown: { mortgage: 67.3, property_tax: 9.6 },
  fixed_costs_monthly: 3933.33,
  variable_costs_monthly: 658.33,
  discretionary_costs_monthly: 160,
};

const comparisonResult: TCOComparisonResult = {
  scenario_a: scenarioA,
  scenario_b: scenarioB,
  scenario_a_name: 'Central Apartment',
  scenario_b_name: 'Suburban House',
  monthly_cost_difference: 690.41,
  total_cost_difference: 657121,
  equity_difference: 2500,
  break_even_years: 7.5,
  a_advantages: ['Lower monthly cost'],
  b_advantages: ['More space for the money'],
  recommendation: 'scenario_a',
  recommendation_reason: 'Scenario A costs less per month.',
  priority_score_a: 0.8,
  priority_score_b: 0.7,
};

describe('TCOComparison', () => {
  beforeEach(() => {
    (compareTCO as jest.Mock).mockReset();
  });

  const clickCompare = () =>
    fireEvent.click(
      screen.getByRole('button', { name: copy('investment', 'tcoComparison.compareScenarios') })
    );

  it('renders both scenario forms and no result before a comparison', () => {
    render(<TCOComparison />);

    // Two forms, one per scenario.
    expect(screen.getAllByLabelText(copy('mortgage', 'propertyPrice'))).toHaveLength(2);
    expect(screen.getByText(copy('mortgage', 'tco.scenarios.scenarioA'))).toBeInTheDocument();
    expect(screen.getByText(copy('mortgage', 'tco.scenarios.scenarioB'))).toBeInTheDocument();

    // The empty state: the form is there, the answer is not.
    expect(screen.queryByText(copy('mortgage', 'tco.comparisonSummary'))).not.toBeInTheDocument();
    expect(
      screen.queryByText(copy('mortgage', 'charts.projection.title'))
    ).not.toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: copy('investment', 'tcoComparison.compareScenarios') })
    ).toBeEnabled();
  });

  it('sends both scenarios to the API and renders the answer', async () => {
    (compareTCO as jest.Mock).mockResolvedValueOnce(comparisonResult);

    render(<TCOComparison />);
    clickCompare();

    await waitFor(() => {
      expect(screen.getByText(copy('mortgage', 'tco.comparisonSummary'))).toBeInTheDocument();
    });

    expect(compareTCO).toHaveBeenCalledWith(
      expect.objectContaining({
        scenario_a: expect.objectContaining({ property_price: 400000, monthly_hoa: 300 }),
        scenario_b: expect.objectContaining({ property_price: 550000, monthly_parking: 100 }),
        scenario_a_name: 'Central Apartment',
        scenario_b_name: 'Suburban House',
        comparison_years: 10,
        appreciation_rate: 3,
      })
    );

    // The summary rows carry the numbers the API returned.
    expect(screen.getByText('+$690')).toBeInTheDocument();
    expect(screen.getByText('+$2,500')).toBeInTheDocument();
    expect(screen.getByText('7.5 years')).toBeInTheDocument();

    // The recommendation and its reason.
    expect(screen.getByText('Recommendation: scenario_a')).toBeInTheDocument();
    expect(screen.getByText('Scenario A costs less per month.')).toBeInTheDocument();
    expect(screen.getByText(/Lower monthly cost/)).toBeInTheDocument();
    expect(screen.getByText(/More space for the money/)).toBeInTheDocument();

    // The scenario cards carry their own values.
    expect(screen.getByText(usd(scenarioA.monthly_tco))).toBeInTheDocument();
    expect(screen.getByText(usd(scenarioB.monthly_tco))).toBeInTheDocument();
    expect(screen.getByText(usd(scenarioA.annual_tco))).toBeInTheDocument();
    expect(screen.getByText(usd(scenarioB.annual_tco))).toBeInTheDocument();
    expect(screen.getByText(usd(scenarioA.total_ownership_cost))).toBeInTheDocument();
    expect(screen.getByText(usd(scenarioB.total_ownership_cost))).toBeInTheDocument();
    expect(screen.getByText(usd(scenarioA.down_payment))).toBeInTheDocument();
    expect(screen.getByText(usd(scenarioB.down_payment))).toBeInTheDocument();

    // The recommended scenario is marked as such.
    expect(screen.getByText(copy('mortgage', 'tco.recommended'))).toBeInTheDocument();
  });

  it('shows the projection chart for the first scenario', async () => {
    (compareTCO as jest.Mock).mockResolvedValueOnce(comparisonResult);

    render(<TCOComparison />);
    clickCompare();

    await waitFor(() => {
      expect(screen.getByText(copy('mortgage', 'charts.projection.title'))).toBeInTheDocument();
    });

    // The milestone numbers come from the projections of scenario A.
    expect(screen.getByText('Cost: $250K')).toBeInTheDocument();
    expect(screen.getByText('Equity: $80K')).toBeInTheDocument();
    expect(screen.getByText('Value: $450K')).toBeInTheDocument();

    // The chart says whose projections it draws.
    const header = screen
      .getByText(copy('mortgage', 'charts.projection.title'))
      .closest('div');
    expect(header).not.toBeNull();
    expect(within(header as HTMLElement).getByText('Central Apartment')).toBeInTheDocument();
  });

  it('prints a negative difference with the sign outside the currency symbol', async () => {
    (compareTCO as jest.Mock).mockResolvedValueOnce({
      ...comparisonResult,
      monthly_cost_difference: -1200.41,
      equity_difference: -2500,
    });

    render(<TCOComparison />);
    clickCompare();

    await waitFor(() => {
      expect(screen.getByText(copy('mortgage', 'tco.comparisonSummary'))).toBeInTheDocument();
    });

    // "$-1,200" is not a shape any locale prints.
    expect(screen.getByText('-$1,200')).toBeInTheDocument();
    expect(screen.getByText('-$2,500')).toBeInTheDocument();
  });

  it('renders no projection chart when the scenario carries no projections', async () => {
    (compareTCO as jest.Mock).mockResolvedValueOnce({
      ...comparisonResult,
      scenario_a: { ...scenarioA, projections: [] },
    });

    render(<TCOComparison />);
    clickCompare();

    await waitFor(() => {
      expect(screen.getByText(copy('mortgage', 'tco.comparisonSummary'))).toBeInTheDocument();
    });

    expect(
      screen.queryByText(copy('mortgage', 'charts.projection.title'))
    ).not.toBeInTheDocument();
    // The rest of the answer is still there.
    expect(screen.getByText('+$690')).toBeInTheDocument();
  });

  it('shows the error state when the comparison fails', async () => {
    const errorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
    (compareTCO as jest.Mock).mockRejectedValueOnce(new Error('Comparison service down'));

    render(<TCOComparison />);
    clickCompare();

    await waitFor(() => {
      expect(screen.getByText('Comparison service down')).toBeInTheDocument();
    });

    // The error state replaces the answer; it never leaves a blank behind.
    expect(screen.queryByText(copy('mortgage', 'tco.comparisonSummary'))).not.toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: copy('investment', 'tcoComparison.compareScenarios') })
    ).toBeEnabled();

    errorSpy.mockRestore();
  });

  it('shows the API error message when the client raises an ApiError', async () => {
    const errorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
    (compareTCO as jest.Mock).mockRejectedValueOnce(new ApiError('TCO comparison failed', 500));

    render(<TCOComparison />);
    clickCompare();

    await waitFor(() => {
      expect(screen.getByText('TCO comparison failed')).toBeInTheDocument();
    });

    errorSpy.mockRestore();
  });
});
