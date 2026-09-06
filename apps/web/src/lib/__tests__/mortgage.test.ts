import { calculateMortgage, formatMonthlyPayment } from '../mortgage';

describe('calculateMortgage', () => {
  it('matches the backend formula for the canonical 30y/20%/4.5% case', () => {
    const res = calculateMortgage({ propertyPrice: 500_000 });
    // 500k * 80% = 400k loan, 4.5% / 12 monthly, 360 months
    // Standard formula yields ~$2,027/month on a 400k loan
    expect(res.loanAmount).toBeCloseTo(400_000, 0);
    expect(res.downPayment).toBeCloseTo(100_000, 0);
    expect(res.monthlyPayment).toBeGreaterThan(2_000);
    expect(res.monthlyPayment).toBeLessThan(2_050);
  });

  it('handles zero-interest edge case', () => {
    const res = calculateMortgage({
      propertyPrice: 120_000,
      downPaymentPercent: 0,
      interestRate: 0,
      loanYears: 10,
    });
    expect(res.monthlyPayment).toBe(1_000); // 120k / 120 months
    expect(res.totalInterest).toBe(0);
  });

  it('throws on invalid input', () => {
    expect(() => calculateMortgage({ propertyPrice: 0 })).toThrow(/positive/);
    expect(() =>
      calculateMortgage({ propertyPrice: 100_000, downPaymentPercent: 150 })
    ).toThrow(/Down payment/);
    expect(() =>
      calculateMortgage({ propertyPrice: 100_000, interestRate: -1 })
    ).toThrow(/Interest rate/);
    expect(() =>
      calculateMortgage({ propertyPrice: 100_000, loanYears: 0 })
    ).toThrow(/Loan term/);
  });

  it('respects custom down payment', () => {
    const res = calculateMortgage({
      propertyPrice: 300_000,
      downPaymentPercent: 10,
      interestRate: 4.5,
      loanYears: 30,
    });
    expect(res.downPayment).toBe(30_000);
    expect(res.loanAmount).toBe(270_000);
  });
});

describe('formatMonthlyPayment', () => {
  it('returns null for missing or invalid price', () => {
    expect(formatMonthlyPayment(null)).toBeNull();
    expect(formatMonthlyPayment(undefined)).toBeNull();
    expect(formatMonthlyPayment(0)).toBeNull();
    expect(formatMonthlyPayment(-100)).toBeNull();
  });

  it('produces a USD-formatted string for valid input', () => {
    const out = formatMonthlyPayment(500_000, { currency: 'USD', locale: 'en-US' });
    expect(out).not.toBeNull();
    expect(out!.display).toMatch(/\/mo$/);
    expect(out!.display).toContain('$');
    expect(out!.raw).toBeGreaterThan(2_000);
  });

  it('respects EUR currency', () => {
    const out = formatMonthlyPayment(400_000, { currency: 'EUR', locale: 'de-DE' });
    expect(out).not.toBeNull();
    expect(out!.display).toContain('€');
  });
});