import { fireEvent, render, screen, waitFor } from '@testing-library/react';

import { AnalyticsConsole } from '../analytics-console';

/**
 * The tools of the assistant, in one console.
 *
 * The console shows one tool at a time - the prototype puts the five
 * calculators behind a row of tabs - so the test covers the tab row and the
 * switch between two tools.
 */
jest.mock('@/components/analytics/mortgage-calculator', () => ({
  MortgageCalculator: () => <div data-testid="mortgage-calculator">Mortgage</div>,
}));

jest.mock('@/components/analytics/investment-analyzer', () => ({
  InvestmentAnalyzer: () => <div data-testid="investment-analyzer">Investment</div>,
}));

jest.mock('@/components/analytics/advanced-investment-analyzer', () => ({
  AdvancedInvestmentAnalyzer: () => <div data-testid="advanced-analyzer">Advanced</div>,
}));

jest.mock('@/components/analytics/portfolio-analyzer', () => ({
  PortfolioAnalyzer: () => <div data-testid="portfolio-analyzer">Portfolio</div>,
}));

jest.mock('@/components/analytics/rent-vs-buy-calculator', () => ({
  RentVsBuyCalculator: () => <div data-testid="rent-vs-buy-calculator">Rent vs buy</div>,
}));

describe('AnalyticsConsole', () => {
  it('names the five tools in the tab row', () => {
    render(<AnalyticsConsole />);

    expect(screen.getByRole('tab', { name: 'Mortgage' })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: 'Investment analyzer' })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: 'Advanced analyzer' })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: 'Portfolio analyzer' })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: 'Rent vs buy' })).toBeInTheDocument();
  });

  it('opens on the first tool', async () => {
    render(<AnalyticsConsole />);

    await waitFor(() => {
      expect(screen.getByTestId('mortgage-calculator')).toBeInTheDocument();
    });
    expect(screen.getByRole('tab', { name: 'Mortgage' })).toHaveAttribute(
      'aria-selected',
      'true'
    );
  });

  it('shows one tool at a time', async () => {
    render(<AnalyticsConsole />);

    await waitFor(() => {
      expect(screen.getByTestId('mortgage-calculator')).toBeInTheDocument();
    });
    expect(screen.queryByTestId('investment-analyzer')).not.toBeInTheDocument();
  });

  it('switches to the tool the tab names', async () => {
    render(<AnalyticsConsole />);

    await waitFor(() => {
      expect(screen.getByTestId('mortgage-calculator')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('tab', { name: 'Investment analyzer' }));

    await waitFor(() => {
      expect(screen.getByTestId('investment-analyzer')).toBeInTheDocument();
    });
    expect(screen.queryByTestId('mortgage-calculator')).not.toBeInTheDocument();
    expect(screen.getByRole('tab', { name: 'Investment analyzer' })).toHaveAttribute(
      'aria-selected',
      'true'
    );
  });

  it('says that the tools are deterministic', () => {
    render(<AnalyticsConsole />);

    expect(
      screen.getAllByText('deterministic · no model needed · currency follows the listing').length
    ).toBeGreaterThan(0);
  });
});
