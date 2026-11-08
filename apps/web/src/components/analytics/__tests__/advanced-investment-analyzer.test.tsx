/**
 * Tests for Advanced Investment Analyzer component
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { AdvancedInvestmentAnalyzer } from '../advanced-investment-analyzer';
import { calculateAdvancedInvestment } from '@/lib/api';
import { exportInvestmentToPDF } from '@/lib/investment-pdf-export';
import en from '../../../../messages/en.json';

// Mock API
jest.mock('@/lib/api');
jest.mock('@/lib/investment-pdf-export');

/**
 * Resolve a message from the English catalogue. The key is the fallback: that is
 * exactly what the next-intl mock renders when the catalogue does not carry the
 * message yet - the translation fragments are merged into the catalogues once
 * the translation work lands.
 */
const copy = (namespace: string, key: string): string => {
  const value = [namespace, key]
    .join('.')
    .split('.')
    .reduce<unknown>((acc, part) => (acc as Record<string, unknown> | undefined)?.[part], en);
  return typeof value === 'string' ? value : key;
};

const mockAdvancedResult = {
  // Basic metrics
  monthly_cash_flow: 250.5,
  annual_cash_flow: 3006,
  cash_on_cash_roi: 8.55,
  cap_rate: 7.2,
  gross_yield: 12.0,
  net_yield: 6.01,
  total_investment: 35000,
  monthly_income: 1800,
  monthly_expenses: 1549.5,
  annual_income: 21600,
  annual_expenses: 18594,
  monthly_mortgage: 1079.5,
  investment_score: 75,
  score_breakdown: { cash_flow: 80, roi: 70, risk: 75 },

  // Advanced metrics
  risk_score: 72,
  total_projected_cash_flow: 35000,
  final_equity: 285000,
  irr: 12.5,
  annual_depreciation: 5236,
  tax_benefit: 1257,
  total_tax_deductions: 15000,

  // Lists
  risk_factors: ['High vacancy rate in area'],
  recommendations: ['Consider property management'],

  // Projections
  cash_flow_projection: [
    {
      year: 1,
      cash_flow: 3006,
      cumulative_cash_flow: 3006,
      equity: 50000,
      noi: 12000,
      gross_income: 21600,
      operating_expenses: 9600,
      mortgage_payment: 12954,
      property_value: 206000,
      loan_balance: 156000,
    },
    {
      year: 2,
      cash_flow: 3150,
      cumulative_cash_flow: 6156,
      equity: 56000,
      noi: 12480,
      gross_income: 22032,
      operating_expenses: 9552,
      mortgage_payment: 12954,
      property_value: 212180,
      loan_balance: 154000,
    },
  ],
  appreciation_scenarios: [
    {
      name: 'pessimistic',
      annual_rate: 1,
      projected_values: { 1: 202000, 2: 204020 },
      total_appreciation_percent: 2,
      total_appreciation_amount: 4000,
    },
    {
      name: 'realistic',
      annual_rate: 3,
      projected_values: { 1: 206000, 2: 212180 },
      total_appreciation_percent: 6,
      total_appreciation_amount: 12180,
    },
    {
      name: 'optimistic',
      annual_rate: 5,
      projected_values: { 1: 210000, 2: 220500 },
      total_appreciation_percent: 10,
      total_appreciation_amount: 20500,
    },
  ],
};

// The ResizeObserver polyfill lives in jest.setup.ts, so the recharts-based
// charts (cash flow, scenarios, risk gauge) render in jsdom.
describe('AdvancedInvestmentAnalyzer', () => {
  beforeEach(() => {
    (calculateAdvancedInvestment as jest.Mock).mockReset();
    (exportInvestmentToPDF as jest.Mock).mockReset();
  });

  it('renders the form with default values', () => {
    render(<AdvancedInvestmentAnalyzer />);

    expect(screen.getByLabelText(/Purchase Price/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Monthly Rent/i)).toBeInTheDocument();
    expect(
      screen.getByRole('button', {
        name: copy('investment', 'advancedAnalyzer.runAnalysis'),
      })
    ).toBeInTheDocument();
  });

  it('shows advanced options when toggled', () => {
    render(<AdvancedInvestmentAnalyzer />);

    expect(screen.queryByLabelText(/Projection Years/i)).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: en.rentVsBuy.form.showAdvanced }));

    expect(screen.getByLabelText(/Projection Years/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Expected Appreciation/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Rent Growth Rate/i)).toBeInTheDocument();
  });

  it('calculates investment analysis on submit', async () => {
    (calculateAdvancedInvestment as jest.Mock).mockResolvedValueOnce(mockAdvancedResult);

    render(<AdvancedInvestmentAnalyzer />);

    fireEvent.click(
      screen.getByRole('button', {
        name: copy('investment', 'advancedAnalyzer.runAnalysis'),
      })
    );

    await waitFor(() => {
      expect(screen.getByText('Investment Summary')).toBeInTheDocument();
    });
  });

  it('handles calculation errors', async () => {
    (calculateAdvancedInvestment as jest.Mock).mockRejectedValueOnce(new Error('API Error'));

    render(<AdvancedInvestmentAnalyzer />);

    fireEvent.click(
      screen.getByRole('button', {
        name: copy('investment', 'advancedAnalyzer.runAnalysis'),
      })
    );

    await waitFor(() => {
      expect(screen.getByText(/Analysis failed/i)).toBeInTheDocument();
    });
  });

  it('displays risk score with correct color coding', async () => {
    (calculateAdvancedInvestment as jest.Mock).mockResolvedValueOnce(mockAdvancedResult);

    render(<AdvancedInvestmentAnalyzer />);

    fireEvent.click(
      screen.getByRole('button', {
        name: copy('investment', 'advancedAnalyzer.runAnalysis'),
      })
    );

    await waitFor(() => {
      expect(screen.getByText('72')).toBeInTheDocument(); // Risk score
    });
  });

  it('displays IRR when available', async () => {
    (calculateAdvancedInvestment as jest.Mock).mockResolvedValueOnce(mockAdvancedResult);

    render(<AdvancedInvestmentAnalyzer />);

    fireEvent.click(
      screen.getByRole('button', {
        name: copy('investment', 'advancedAnalyzer.runAnalysis'),
      })
    );

    await waitFor(() => {
      expect(screen.getByText('12.5%')).toBeInTheDocument(); // IRR
    });
  });

  it('displays N/A for null IRR', async () => {
    (calculateAdvancedInvestment as jest.Mock).mockResolvedValueOnce({
      ...mockAdvancedResult,
      irr: null,
    });

    render(<AdvancedInvestmentAnalyzer />);

    fireEvent.click(
      screen.getByRole('button', {
        name: copy('investment', 'advancedAnalyzer.runAnalysis'),
      })
    );

    await waitFor(() => {
      expect(screen.getByText('N/A')).toBeInTheDocument();
    });
  });

  describe('Export Report Button', () => {
    it('does not render export button when no results', () => {
      render(<AdvancedInvestmentAnalyzer />);

      expect(
        screen.queryByRole('button', {
          name: copy('investment', 'advancedAnalyzer.exportReport'),
        })
      ).not.toBeInTheDocument();
    });

    it('renders export button after successful calculation', async () => {
      (calculateAdvancedInvestment as jest.Mock).mockResolvedValueOnce(mockAdvancedResult);

      render(<AdvancedInvestmentAnalyzer />);

      fireEvent.click(
        screen.getByRole('button', {
          name: copy('investment', 'advancedAnalyzer.runAnalysis'),
        })
      );

      await waitFor(() => {
        expect(
          screen.getByRole('button', {
            name: copy('investment', 'advancedAnalyzer.exportReport'),
          })
        ).toBeInTheDocument();
      });
    });

    it('calls exportInvestmentToPDF when export button clicked', async () => {
      (calculateAdvancedInvestment as jest.Mock).mockResolvedValueOnce(mockAdvancedResult);
      (exportInvestmentToPDF as jest.Mock).mockResolvedValueOnce(undefined);

      render(<AdvancedInvestmentAnalyzer />);

      // Run calculation first
      fireEvent.click(
        screen.getByRole('button', {
          name: copy('investment', 'advancedAnalyzer.runAnalysis'),
        })
      );

      await waitFor(() => {
        expect(
          screen.getByRole('button', {
            name: copy('investment', 'advancedAnalyzer.exportReport'),
          })
        ).toBeInTheDocument();
      });

      // Click export button
      fireEvent.click(
        screen.getByRole('button', {
          name: copy('investment', 'advancedAnalyzer.exportReport'),
        })
      );

      await waitFor(() => {
        expect(exportInvestmentToPDF).toHaveBeenCalledWith(
          mockAdvancedResult,
          expect.objectContaining({
            filename: expect.stringContaining('investment-analysis'),
          })
        );
      });
    });

    it('shows loading state during export', async () => {
      (calculateAdvancedInvestment as jest.Mock).mockResolvedValueOnce(mockAdvancedResult);
      // Make export hang to test loading state
      (exportInvestmentToPDF as jest.Mock).mockImplementationOnce(
        () => new Promise((resolve) => setTimeout(resolve, 1000))
      );

      render(<AdvancedInvestmentAnalyzer />);

      // Run calculation
      fireEvent.click(
        screen.getByRole('button', {
          name: copy('investment', 'advancedAnalyzer.runAnalysis'),
        })
      );

      await waitFor(() => {
        expect(
          screen.getByRole('button', {
            name: copy('investment', 'advancedAnalyzer.exportReport'),
          })
        ).toBeInTheDocument();
      });

      // Click export button
      fireEvent.click(
        screen.getByRole('button', {
          name: copy('investment', 'advancedAnalyzer.exportReport'),
        })
      );

      // Button should be disabled during export
      await waitFor(() => {
        const exportButton = screen.getByRole('button', {
          name: copy('investment', 'advancedAnalyzer.exportReport'),
        });
        expect(exportButton).toBeDisabled();
      });
    });

    it('handles export errors gracefully', async () => {
      (calculateAdvancedInvestment as jest.Mock).mockResolvedValueOnce(mockAdvancedResult);
      (exportInvestmentToPDF as jest.Mock).mockRejectedValueOnce(new Error('Export failed'));

      // Spy on console.error
      const consoleSpy = jest.spyOn(console, 'error').mockImplementation();

      render(<AdvancedInvestmentAnalyzer />);

      // Run calculation
      fireEvent.click(
        screen.getByRole('button', {
          name: copy('investment', 'advancedAnalyzer.runAnalysis'),
        })
      );

      await waitFor(() => {
        expect(
          screen.getByRole('button', {
            name: copy('investment', 'advancedAnalyzer.exportReport'),
          })
        ).toBeInTheDocument();
      });

      // Click export button
      fireEvent.click(
        screen.getByRole('button', {
          name: copy('investment', 'advancedAnalyzer.exportReport'),
        })
      );

      await waitFor(() => {
        expect(console.error).toHaveBeenCalledWith('Export failed:', expect.any(Error));
      });

      consoleSpy.mockRestore();
    });
  });

  describe('Tabs Navigation', () => {
    it('renders all tab options after calculation', async () => {
      (calculateAdvancedInvestment as jest.Mock).mockResolvedValueOnce(mockAdvancedResult);

      render(<AdvancedInvestmentAnalyzer />);

      fireEvent.click(
        screen.getByRole('button', {
          name: copy('investment', 'advancedAnalyzer.runAnalysis'),
        })
      );

      await waitFor(() => {
        expect(screen.getByRole('tab', { name: /Cash Flow/i })).toBeInTheDocument();
        expect(screen.getByRole('tab', { name: /Scenarios/i })).toBeInTheDocument();
        expect(screen.getByRole('tab', { name: /Tax/i })).toBeInTheDocument();
        expect(screen.getByRole('tab', { name: /Risk/i })).toBeInTheDocument();
      });
    });

    it('switches between tabs', async () => {
      (calculateAdvancedInvestment as jest.Mock).mockResolvedValueOnce(mockAdvancedResult);

      render(<AdvancedInvestmentAnalyzer />);

      fireEvent.click(
        screen.getByRole('button', {
          name: copy('investment', 'advancedAnalyzer.runAnalysis'),
        })
      );

      await waitFor(() => {
        expect(screen.getByRole('tab', { name: /Tax/i })).toBeInTheDocument();
      });

      // Radix Tabs activates a tab on mousedown (not click), so the trigger
      // needs a mouseDown event to switch the active panel.
      fireEvent.mouseDown(screen.getByRole('tab', { name: /Tax/i }));

      await waitFor(() => {
        expect(screen.getByText('Tax Implications')).toBeInTheDocument();
      });
    });
  });
});
