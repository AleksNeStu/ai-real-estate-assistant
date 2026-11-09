import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, jest } from '@jest/globals';
import AnalyticsPage from '../page';

/**
 * The tools of the assistant.
 *
 * The route is the console: one screen, the five calculators behind a row of
 * tabs. The test covers the heading, the tab row and the tool that is open.
 */

// Mock next/dynamic to render components directly instead of lazy-loading
jest.mock('next/dynamic', () => {
  return (loader: () => Promise<{ default: React.ComponentType }>) => {
    // Return a component that resolves the dynamic import synchronously for tests
    let Comp: React.ComponentType | null = null;
    loader().then((mod) => {
      Comp = mod.default;
    });
    return function DynamicMock(props: Record<string, unknown>) {
      if (Comp) return React.createElement(Comp, props);
      return React.createElement('div', { 'data-testid': 'dynamic-loading' });
    };
  };
});

// Mock all dynamic analytics components
jest.mock('@/components/analytics/mortgage-calculator', () => ({
  MortgageCalculator: () => (
    <div data-testid="mortgage-calculator">Mortgage Calculator Component</div>
  ),
}));

jest.mock('@/components/analytics/investment-analyzer', () => ({
  InvestmentAnalyzer: () => (
    <div data-testid="investment-analyzer">Investment Analyzer Component</div>
  ),
}));

jest.mock('@/components/analytics/advanced-investment-analyzer', () => ({
  AdvancedInvestmentAnalyzer: () => (
    <div data-testid="advanced-investment-analyzer">Advanced Investment Analyzer Component</div>
  ),
}));

jest.mock('@/components/analytics/portfolio-analyzer', () => ({
  PortfolioAnalyzer: () => (
    <div data-testid="portfolio-analyzer">Portfolio Analyzer Component</div>
  ),
}));

jest.mock('@/components/analytics/rent-vs-buy-calculator', () => ({
  RentVsBuyCalculator: () => (
    <div data-testid="rent-vs-buy-calculator">Rent vs Buy Calculator Component</div>
  ),
}));

describe('AnalyticsPage', () => {
  it('renders the page title and description', () => {
    render(<AnalyticsPage />);
    expect(screen.getByText('Analytics')).toBeInTheDocument();
    expect(
      screen.getByText('Five calculators — the same ones the assistant calls in chat.')
    ).toBeInTheDocument();
  });

  it('names the five tools in the tab row', () => {
    render(<AnalyticsPage />);
    expect(screen.getByRole('tab', { name: 'Mortgage' })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: 'Investment analyzer' })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: 'Advanced analyzer' })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: 'Portfolio analyzer' })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: 'Rent vs buy' })).toBeInTheDocument();
  });

  it('opens on the mortgage calculator', async () => {
    render(<AnalyticsPage />);
    await waitFor(() => {
      expect(screen.getByTestId('mortgage-calculator')).toBeInTheDocument();
    });
  });

  it('says that the tools are deterministic', () => {
    render(<AnalyticsPage />);
    expect(
      screen.getAllByText('deterministic · no model needed · currency follows the listing').length
    ).toBeGreaterThan(0);
  });
});
