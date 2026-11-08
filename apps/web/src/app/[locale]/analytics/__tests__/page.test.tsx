import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect, jest, beforeEach } from '@jest/globals';
import AnalyticsPage from '../page';
import en from '../../../../../messages/en.json';

/**
 * The "advanced investment" heading is page copy of its own, so it travels in
 * the message fragments and lands in the catalogue with the central merge.
 * Until it is there, the next-intl mock renders the key itself — the
 * expectation follows the catalogue and falls back to that key.
 */
const advancedInvestmentHeading =
  (en.pages.analytics as { sections?: { advancedInvestment?: string } }).sections
    ?.advancedInvestment ?? 'sections.advancedInvestment';

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
  PortfolioAnalyzer: () => <div data-testid="portfolio-analyzer">Portfolio Analyzer Component</div>,
}));

jest.mock('@/components/analytics/rent-vs-buy-calculator', () => ({
  RentVsBuyCalculator: () => (
    <div data-testid="rent-vs-buy-calculator">Rent vs Buy Calculator Component</div>
  ),
}));

describe('AnalyticsPage', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders the page title and description', () => {
    render(<AnalyticsPage />);
    expect(screen.getByText('Analytics & Tools')).toBeInTheDocument();
    expect(
      screen.getByText('Market insights and financial tools to help you make informed decisions.')
    ).toBeInTheDocument();
  });

  it('renders all section headings', () => {
    render(<AnalyticsPage />);
    expect(screen.getByText('Mortgage Calculator')).toBeInTheDocument();
    expect(screen.getByText('Investment Property Analyzer')).toBeInTheDocument();
    expect(screen.getByText(advancedInvestmentHeading)).toBeInTheDocument();
    expect(screen.getByText('Portfolio Analyzer')).toBeInTheDocument();
    expect(screen.getByText('Rent vs Buy Calculator')).toBeInTheDocument();
  });

  it('renders the MortgageCalculator component', () => {
    render(<AnalyticsPage />);
    expect(screen.getByTestId('mortgage-calculator')).toBeInTheDocument();
  });

  it('renders the InvestmentAnalyzer component', () => {
    render(<AnalyticsPage />);
    expect(screen.getByTestId('investment-analyzer')).toBeInTheDocument();
  });

  it('renders the AdvancedInvestmentAnalyzer component', () => {
    render(<AnalyticsPage />);
    expect(screen.getByTestId('advanced-investment-analyzer')).toBeInTheDocument();
  });

  it('renders the PortfolioAnalyzer component', () => {
    render(<AnalyticsPage />);
    expect(screen.getByTestId('portfolio-analyzer')).toBeInTheDocument();
  });

  it('renders the RentVsBuyCalculator component', () => {
    render(<AnalyticsPage />);
    expect(screen.getByTestId('rent-vs-buy-calculator')).toBeInTheDocument();
  });

  it('renders section icons as SVG elements', () => {
    const { container } = render(<AnalyticsPage />);
    // Lucide icons render as SVG elements with class containing "lucide"
    const svgs = container.querySelectorAll('svg[class*="lucide"]');
    // 5 sections = 5 icons
    expect(svgs.length).toBeGreaterThanOrEqual(5);
  });

  it('renders correct page structure with sections', () => {
    const { container } = render(<AnalyticsPage />);
    const sections = container.querySelectorAll('section');
    expect(sections.length).toBe(5);
  });
});
