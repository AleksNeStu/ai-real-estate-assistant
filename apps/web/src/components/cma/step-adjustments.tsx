'use client';

import React from 'react';
import { useLocale, useTranslations } from 'next-intl';
import { formatPrice as formatPriceInLocale } from '@/lib/format';
import { StatTile } from '@/components/ui/stat-tile';
import type { CMAComparable } from '@/lib/types';

interface StepAdjustmentsProps {
  comparables: CMAComparable[];
  onComparablesChange: (comparables: CMAComparable[]) => void;
}

/**
 * The adjustments.
 *
 * One comparable is one block under a rule: the factors it differs by, the
 * percentage each one carries and what it adds up to. The numbers are the
 * API's own - a factor the reader changes is changed in place, and the
 * adjusted price follows.
 */
export function StepAdjustments({
  comparables,
  onComparablesChange,
}: StepAdjustmentsProps) {
  const locale = useLocale();
  const t = useTranslations('cma.adjustments');

  const handleAdjustmentChange = (compIndex: number, adjIndex: number, newPercent: number) => {
    const updatedComparables = [...comparables];
    const adjustments = [...updatedComparables[compIndex].adjustments];
    const oldAdjustment = adjustments[adjIndex];
    const oldAmount = oldAdjustment.adjustment_amount;

    // Calculate new amount based on percentage change
    const basePrice = calculateBasePrice(comparables[compIndex]);
    const newAmount = Math.round((basePrice * newPercent) / 100);

    adjustments[adjIndex] = {
      ...oldAdjustment,
      adjustment_percent: newPercent,
      adjustment_amount: newAmount - oldAmount + oldAdjustment.adjustment_amount,
    };

    updatedComparables[compIndex] = {
      ...updatedComparables[compIndex],
      adjustments,
      adjusted_price: calculateAdjustedPrice(
        updatedComparables[compIndex].adjusted_price,
        oldAmount,
        newAmount
      ),
    };

    onComparablesChange(updatedComparables);
  };

  const calculateBasePrice = (comp: CMAComparable): number => {
    // Base price is the adjusted price minus all current adjustments
    return comp.adjusted_price;
  };

  const calculateAdjustedPrice = (
    currentAdjusted: number,
    oldAmount: number,
    newAmount: number
  ): number => {
    return currentAdjusted - oldAmount + newAmount;
  };

  const formatCurrency = (value: number, currency?: string) => {
    // The wizard used to force every price into euros with German separators,
    // whatever the listing said and whatever language the reader picked.
    return formatPriceInLocale(value, currency || 'EUR', locale);
  };

  const getTotalAdjustments = (comp: CMAComparable): number => {
    return comp.adjustments.reduce((sum, adj) => sum + adj.adjustment_amount, 0);
  };

  const getAverageAdjustment = (comparables: CMAComparable[]): number => {
    if (comparables.length === 0) return 0;
    const total = comparables.reduce((sum, comp) => sum + getTotalAdjustments(comp), 0);
    return total / comparables.length;
  };

  const getLowestPrice = (comparables: CMAComparable[]): number => {
    if (comparables.length === 0) return 0;
    return Math.min(...comparables.map((c) => c.adjusted_price));
  };

  const getHighestPrice = (comparables: CMAComparable[]): number => {
    if (comparables.length === 0) return 0;
    return Math.max(...comparables.map((c) => c.adjusted_price));
  };

  const getMedianPrice = (comparables: CMAComparable[]): number => {
    if (comparables.length === 0) return 0;
    const sorted = [...comparables].map((c) => c.adjusted_price).sort((a, b) => a - b);
    const mid = Math.floor(sorted.length / 2);
    return sorted.length % 2 !== 0 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
  };

  return (
    <div className="flex flex-col gap-6">
      <p className="text-[14px] leading-5 text-muted-foreground">{t('description')}</p>

      {comparables.map((comp, compIndex) => {
        const total = getTotalAdjustments(comp);
        return (
          <section key={comp.property_id} className="border-t border-foreground pt-2.5">
            <div className="flex items-baseline justify-between gap-3">
              <h3 className="text-[14px] font-semibold text-foreground">
                {t('comparable', { index: compIndex + 1 })}
              </h3>
              <span className="font-mono text-[12px] text-muted-foreground">
                {t('similarity')} {comp.similarity_score.toFixed(1)}
              </span>
            </div>

            <div className="mt-2 flex flex-col">
              <div className="grid grid-cols-[minmax(0,1.6fr)_minmax(0,1fr)_minmax(0,1fr)_64px_auto] items-baseline gap-x-4 border-b border-border py-2 text-[12px] text-muted-foreground">
                <span>{t('factor')}</span>
                <span>{t('subject')}</span>
                <span>{t('comparableLabel')}</span>
                <span className="text-right">{t('adjPercent')}</span>
                <span className="text-right">{t('amount')}</span>
              </div>

              {comp.adjustments.map((adj, adjIndex) => (
                <div
                  key={adjIndex}
                  className="grid grid-cols-[minmax(0,1.6fr)_minmax(0,1fr)_minmax(0,1fr)_64px_auto] items-baseline gap-x-4 border-b border-border py-2.5"
                >
                  <span className="min-w-0">
                    <span className="block text-[13px] font-medium text-foreground">
                      {adj.category}
                    </span>
                    <span className="mt-0.5 block truncate text-[12px] text-muted-foreground">
                      {adj.description}
                    </span>
                  </span>
                  <span className="font-mono text-[13px] text-foreground">
                    {adj.subject_value || '-'}
                  </span>
                  <span className="font-mono text-[13px] text-foreground">
                    {adj.comp_value || '-'}
                  </span>
                  <span className="text-right">
                    <input
                      type="number"
                      aria-label={t('adjPercentFor', {
                        category: adj.category,
                        index: compIndex + 1,
                      })}
                      className="w-16 rounded-sm border border-input bg-background px-1.5 py-1 text-right font-mono text-[12px] text-foreground outline-none focus-visible:outline-2 focus-visible:outline-ring/50"
                      value={adj.adjustment_percent}
                      onChange={(e) =>
                        handleAdjustmentChange(
                          compIndex,
                          adjIndex,
                          parseFloat(e.target.value) || 0
                        )
                      }
                    />
                  </span>
                  <span
                    className={`text-right font-mono text-[13px] ${
                      adj.adjustment_amount >= 1
                        ? 'text-success'
                        : adj.adjustment_amount < 1
                          ? 'text-destructive'
                          : ''
                    }`}
                  >
                    {adj.adjustment_amount >= 1 ? '+' : ''}
                    {formatCurrency(Math.abs(adj.adjustment_amount))}
                  </span>
                </div>
              ))}
            </div>

            <div className="flex items-baseline justify-between gap-4 pt-2.5">
              <span className="text-[13px] font-medium text-foreground">
                {t('totalAdjustments')}
              </span>
              <span className="text-right">
                <span
                  className={`font-mono text-[16px] font-semibold ${
                    total >= 1 ? 'text-success' : 'text-destructive'
                  }`}
                >
                  {total >= 1 ? '+' : '-'}
                  {formatCurrency(Math.abs(total))}
                </span>
                <span className="mt-0.5 block font-mono text-[12px] text-muted-foreground">
                  {t('adjustedPrice')} {formatCurrency(comp.adjusted_price)}
                </span>
              </span>
            </div>
          </section>
        );
      })}

      <section className="grid grid-cols-1 gap-4 border-t border-foreground pt-3 sm:grid-cols-3">
        <StatTile
          value={formatCurrency(getAverageAdjustment(comparables))}
          label={t('avgAdjustment')}
        />
        <StatTile
          value={`${formatCurrency(getLowestPrice(comparables))} – ${formatCurrency(
            getHighestPrice(comparables)
          )}`}
          label={t('priceRange')}
        />
        <StatTile
          value={formatCurrency(getMedianPrice(comparables))}
          label={t('medianPrice')}
        />
      </section>
    </div>
  );
}
