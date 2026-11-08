'use client';

import React from 'react';
import { TrendingUp } from 'lucide-react';
import { useTranslations } from 'next-intl';
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
  const t = useTranslations('property');
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
        'bg-success/10 text-success dark:bg-chart-7/40 dark:text-chart-7',
        'px-2.5 py-1 text-xs font-medium border border-chart-7/60',
        'dark:border-chart-7/40',
        className ?? '',
      ]
        .filter(Boolean)
        .join(' ')}
      aria-label={t('estimateLabel', { value: estimate.display })}
      title={t('estimateTitle', {
        down: downPaymentPercent,
        years: loanYears,
        rate: interestRate,
      })}
    >
      <TrendingUp className="h-3 w-3" aria-hidden />
      <span>{estimate.display}</span>
      <span className="text-success/70 dark:text-chart-7/60 font-normal">{t('estimate.abbr')}</span>
    </div>
  );
}

export default MortgageEstimate;
