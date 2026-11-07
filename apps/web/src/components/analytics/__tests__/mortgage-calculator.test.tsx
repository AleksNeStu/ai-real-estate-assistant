import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MortgageCalculator } from '../mortgage-calculator';
import { calculateMortgage, calculateTCO } from '@/lib/api';

jest.mock('@/lib/api');

// jsPDF + html2canvas cannot run in jsdom - the export button is not what this
// suite covers, so the module is replaced by a stub.
jest.mock('@/lib/pdf-export', () => ({
  exportTCOToPDF: jest.fn(),
}));

// The global next-intl mock returns the raw translation key. The component
// renders user-visible English, so the mock resolves the real `en` messages
// (including `{placeholder}` interpolation).
jest.mock('next-intl', () => {
  const messages = jest.requireActual<Record<string, unknown>>('../../../../messages/en.json');
  const resolve = (path: string): unknown =>
    path.split('.').reduce<unknown>(
      (acc, part) =>
        acc && typeof acc === 'object' ? (acc as Record<string, unknown>)[part] : undefined,
      messages
    );
  const interpolate = (template: string, params?: Record<string, unknown>) =>
    params
      ? template.replace(/\{(\w+)\}/g, (match, name) =>
          name in params ? String(params[name]) : match
        )
      : template;
  return {
    useTranslations:
      (namespace?: string) =>
      (key: string, params?: Record<string, unknown>) => {
        const value = resolve(namespace ? `${namespace}.${key}` : key);
        return typeof value === 'string' ? interpolate(value, params) : key;
      },
    useLocale: () => 'en',
    useMessages: () => messages,
    NextIntlClientProvider: ({ children }: { children: React.ReactNode }) => children,
  };
});

describe('MortgageCalculator', () => {
  const mockResult = {
    monthly_payment: 2533.43,
    total_interest: 412033.64,
    total_cost: 912033.64,
    down_payment: 100000,
    loan_amount: 400000,
    breakdown: { principal: 1000, interest: 1533.43 },
  };

  const mockTCOResult = {
    // Mortgage components
    monthly_payment: 2533.43,
    total_interest: 412033.64,
    down_payment: 100000,
    loan_amount: 400000,
    // TCO components (monthly)
    monthly_mortgage: 2533.43,
    monthly_property_tax: 416.67,
    monthly_insurance: 125,
    monthly_hoa: 0,
    monthly_utilities: 0,
    monthly_internet: 0,
    monthly_parking: 0,
    monthly_maintenance: 416.67,
    monthly_tco: 3491.77,
    // TCO components (annual)
    annual_mortgage: 30401.16,
    annual_property_tax: 5000,
    annual_insurance: 1500,
    annual_hoa: 0,
    annual_utilities: 0,
    annual_internet: 0,
    annual_parking: 0,
    annual_maintenance: 5000,
    annual_tco: 41901.16,
    // Total over loan term
    total_ownership_cost: 1257034.8,
    total_all_costs: 1357034.8,
    breakdown: {
      mortgage: 2533.43,
      property_tax: 416.67,
      insurance: 125,
      hoa: 0,
      utilities: 0,
      internet: 0,
      parking: 0,
      maintenance: 416.67,
    },
  };

  beforeEach(() => {
    (calculateMortgage as jest.Mock).mockReset();
    (calculateTCO as jest.Mock).mockReset();
  });

  it('renders the form', () => {
    render(<MortgageCalculator />);
    expect(screen.getByLabelText(/Property Price/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Down Payment/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Interest Rate/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Loan Term/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Calculate/i })).toBeInTheDocument();
  });

  it('calculates mortgage on submit', async () => {
    (calculateMortgage as jest.Mock).mockResolvedValueOnce(mockResult);
    (calculateTCO as jest.Mock).mockResolvedValueOnce(mockTCOResult);

    render(<MortgageCalculator />);

    fireEvent.click(screen.getByRole('button', { name: /Calculate/i }));

    expect(screen.getByRole('button', { name: /Calculate/i })).toBeDisabled();

    await waitFor(() => {
      expect(screen.getByText('Mortgage Results')).toBeInTheDocument();
      expect(screen.getByText('$2,533.43')).toBeInTheDocument();
    });

    expect(calculateMortgage).toHaveBeenCalledWith({
      property_price: 500000,
      down_payment_percent: 20,
      interest_rate: 4.5,
      loan_years: 30,
      monthly_hoa: 0,
      annual_property_tax: 0,
      annual_insurance: 0,
      monthly_utilities: 0,
      monthly_internet: 0,
      monthly_parking: 0,
      maintenance_percent: 1,
    });
  });

  it('handles errors', async () => {
    const errorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
    (calculateMortgage as jest.Mock).mockRejectedValueOnce(new Error('API Error'));
    (calculateTCO as jest.Mock).mockRejectedValueOnce(new Error('API Error'));

    render(<MortgageCalculator />);

    fireEvent.click(screen.getByRole('button', { name: /Calculate/i }));

    await waitFor(() => {
      expect(screen.getByText('Calculation failed')).toBeInTheDocument();
    });
    expect(errorSpy).not.toHaveBeenCalled();
    errorSpy.mockRestore();
  });

  it('updates inputs', () => {
    render(<MortgageCalculator />);
    const priceInput = screen.getByLabelText(/Property Price/i);
    fireEvent.change(priceInput, { target: { value: '600000' } });
    expect(priceInput).toHaveValue(600000);
  });
});
