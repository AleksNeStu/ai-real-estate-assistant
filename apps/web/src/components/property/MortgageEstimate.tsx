'use client';

import React from 'react';
import { TrendingUp } from 'lucide-react';
import { formatMonthlyPayment } from '@/lib/mortgage';

interface MortgageEstimateProps {
  /** Listing price. Component hides itself if invalid. */
  price?: number | null;
  /** Currency code (defaults to USD). */
  currency?: string;
  /** Locale used by Intl.NumberFormat. */
  locale?: string;
  /** Annual interest rate percent (default 6.5% to match a realistic EU/US average). */
  interestRate?: number;
  /** Down payment percent (default 20). */
  downPaymentPercent?: number;
  /** Loan term in years (default 30). */
  loanYears?: number;
  /** Optional className for layout tweaks. */
  className?: string;
}

/**
 * Tiny inline monthly-payment estimate for property cards.
 *
 * Pure client-side math — no network call. Renders nothing when the
 * price is missing or invalid so it stays safe to drop into any card.
 */
export function MortgageEstimate({
  price,
  currency = 'USD',
  locale = 'en-US',
  interestRate = 6.5,
  downPaymentPercent = 20,
  loanYears = 30,
  className,
}: MortgageEstimateProps) {
  const estimate = formatMonthlyPayment(price, {
    currency,
    locale,
    interestRate,
    downPaymentPercent,
    loanYears,
  });
  if (!estimate) return null;

  return (
    <div
      data-testid="mortgage-estimate"
      className={[
        'inline-flex items-center gap-1.5 rounded-full',
        'bg-emerald-50 text-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-200',
        'px-2.5 py-1 text-xs font-medium border border-emerald-200/60',
        'dark:border-emerald-800/40',
        className ?? '',
      ]
        .filter(Boolean)
        .join(' ')}
      aria-label={`Estimated monthly payment ${estimate.display}`}
      title={`Estimated monthly payment with ${downPaymentPercent}% down, ${loanYears}-year fixed at ${interestRate}% APR. Not a lending offer.`}
    >
      <TrendingUp className="h-3 w-3" aria-hidden />
      <span>{estimate.display}</span>
      <span className="text-emerald-700/70 dark:text-emerald-300/60 font-normal">est.</span>
    </div>
  );
}

export default MortgageEstimate;