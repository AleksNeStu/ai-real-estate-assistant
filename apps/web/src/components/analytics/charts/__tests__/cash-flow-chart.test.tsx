/**
 * Tests for the cash-flow chart.
 *
 * The chart draws the years of an investment and prints the two totals under
 * it. Both totals can be negative - a year that costs more than it earns is
 * the case the chart exists for - so the money shape has to hold when the
 * sign is a minus.
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import { CashFlowChart } from '../cash-flow-chart';
import type { YearlyCashFlow } from '@/lib/types';
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

const year = (overrides: Partial<YearlyCashFlow> = {}): YearlyCashFlow => ({
  year: 1,
  gross_income: 24000,
  operating_expenses: 6000,
  mortgage_payment: 14000,
  noi: 18000,
  cash_flow: 4000,
  cumulative_cash_flow: 4000,
  property_value: 320000,
  equity: 80000,
  loan_balance: 240000,
  ...overrides,
});

describe('CashFlowChart', () => {
  it('renders the title, the description and the accessible label of the chart', () => {
    render(<CashFlowChart data={[year()]} />);

    expect(screen.getByText(copy('investment', 'charts.cashFlow.title'))).toBeInTheDocument();
    expect(
      screen.getByText(copy('investment', 'charts.cashFlow.description'))
    ).toBeInTheDocument();
    expect(screen.getByRole('img')).toHaveAttribute(
      'aria-label',
      copy('investment', 'charts.cashFlow.ariaLabel')
    );
  });

  it('prints a negative total with the sign outside the currency symbol', () => {
    // "$-5,000" is a shape no locale prints.
    render(
      <CashFlowChart
        data={[year({ cumulative_cash_flow: -5000, equity: -12000 })]}
      />
    );

    expect(screen.getByText('-$5,000')).toBeInTheDocument();
    expect(screen.getByText('-$12,000')).toBeInTheDocument();
  });

  it('prints a positive total the way it always has', () => {
    render(<CashFlowChart data={[year({ cumulative_cash_flow: 5000, equity: 12000 })]} />);

    expect(screen.getByText('$5,000')).toBeInTheDocument();
    expect(screen.getByText('$12,000')).toBeInTheDocument();
  });

  it('renders an empty chart without a blank', () => {
    render(<CashFlowChart data={[]} />);

    expect(screen.getByText(copy('investment', 'charts.cashFlow.title'))).toBeInTheDocument();
    expect(screen.getByRole('img')).toBeInTheDocument();

    // Without a year to summarise, the totals read zero - not a leftover
    // number and not a blank.
    expect(screen.getAllByText('$0')).toHaveLength(2);
  });
});
