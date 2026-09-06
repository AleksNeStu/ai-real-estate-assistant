/**
 * Client-side mortgage math.
 *
 * Pure-function mirror of apps/api/tools/mortgage_tools.py:MortgageCalculatorTool.calculate().
 * Kept identical to avoid drift; used by inline PropertyCard estimates so we
 * don't need a network round-trip per card.
 */

export interface MortgageCalcInput {
  propertyPrice: number;
  downPaymentPercent?: number; // default 20
  interestRate?: number; // annual %, default 4.5
  loanYears?: number; // default 30
}

export interface MortgageCalcResult {
  monthlyPayment: number;
  totalInterest: number;
  totalCost: number;
  downPayment: number;
  loanAmount: number;
}

const DEFAULTS = {
  downPaymentPercent: 20,
  interestRate: 4.5,
  loanYears: 30,
};

/**
 * Calculate mortgage payments.
 *
 * Pure function — no side effects. Throws on invalid input to surface
 * bugs early; the caller should guard with a price > 0 check.
 */
export function calculateMortgage(input: MortgageCalcInput): MortgageCalcResult {
  const downPaymentPercent = input.downPaymentPercent ?? DEFAULTS.downPaymentPercent;
  const interestRate = input.interestRate ?? DEFAULTS.interestRate;
  const loanYears = input.loanYears ?? DEFAULTS.loanYears;
  const price = input.propertyPrice;

  if (!(price > 0)) {
    throw new Error("Property price must be positive");
  }
  if (downPaymentPercent < 0 || downPaymentPercent > 100) {
    throw new Error("Down payment must be between 0 and 100%");
  }
  if (interestRate < 0) {
    throw new Error("Interest rate cannot be negative");
  }
  if (!(loanYears > 0)) {
    throw new Error("Loan term must be positive");
  }

  const downPayment = price * (downPaymentPercent / 100);
  const loanAmount = price - downPayment;
  const monthlyRate = interestRate / 100 / 12;
  const numPayments = loanYears * 12;
  const monthlyPayment =
    monthlyRate === 0
      ? loanAmount / numPayments
      : (loanAmount * monthlyRate * Math.pow(1 + monthlyRate, numPayments)) /
        (Math.pow(1 + monthlyRate, numPayments) - 1);
  const totalPaid = monthlyPayment * numPayments;
  const totalInterest = totalPaid - loanAmount;
  const totalCost = totalPaid + downPayment;

  return {
    monthlyPayment,
    totalInterest,
    totalCost,
    downPayment,
    loanAmount,
  };
}

/**
 * Format a monthly payment for display in the listing card.
 * Returns null if price is missing or invalid.
 */
export function formatMonthlyPayment(
  price: number | null | undefined,
  options?: {
    locale?: string;
    currency?: string;
    downPaymentPercent?: number;
    interestRate?: number;
    loanYears?: number;
  }
): { display: string; raw: number } | null {
  if (price === null || price === undefined || !(price > 0)) {
    return null;
  }
  let result: MortgageCalcResult;
  try {
    result = calculateMortgage({
      propertyPrice: price,
      downPaymentPercent: options?.downPaymentPercent,
      interestRate: options?.interestRate,
      loanYears: options?.loanYears,
    });
  } catch {
    return null;
  }
  const currency = options?.currency ?? "USD";
  const locale = options?.locale ?? "en-US";
  const formatter = new Intl.NumberFormat(locale, {
    style: "currency",
    currency,
    maximumFractionDigits: 0,
  });
  return {
    display: `${formatter.format(Math.round(result.monthlyPayment))}/mo`,
    raw: result.monthlyPayment,
  };
}