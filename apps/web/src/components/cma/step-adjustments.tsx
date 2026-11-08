'use client';

import React from 'react';
import { useLocale, useTranslations } from 'next-intl';
import { Button } from '@/components/ui/button';
import { formatPrice as formatPriceInLocale } from '@/lib/format';
import type { CMAComparable } from '@/lib/types';

interface StepAdjustmentsProps {
  comparables: CMAComparable[];
  onComparablesChange: (comparables: CMAComparable[]) => void;
  onNext: () => void;
  onPrev: () => void;
}

export function StepAdjustments({
  comparables,
  onComparablesChange,
  onNext,
  onPrev,
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
      ...adjustments[adjIndex],
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

  const getCategoryColor = (category: string): string => {
    const colors: Record<string, string> = {
      location: 'text-info',
      size: 'text-success',
      age: 'text-warning',
      condition: 'text-critical',
      amenities: 'text-chart-6',
      floor: 'text-chart-5',
      market: 'text-warning',
    };
    return colors[category] || 'text-muted-foreground';
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
    <div className="space-y-6">
      <div className="text-sm text-muted-foreground mb-4">{t('description')}</div>

      {comparables.map((comp, compIndex) => (
        <div key={comp.property_id} className="border rounded-lg p-4">
          <div className="flex items-center justify-between mb-3">
            <h4 className="text-sm font-medium">{t('comparable', { index: compIndex + 1 })}</h4>
            <span className="text-sm text-muted-foreground">
              {t('similarity')} {comp.similarity_score.toFixed(1)}
            </span>
          </div>

          {/* Adjustments table */}
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b">
                  <th className="text-left py-2 px-2 font-medium text-muted-foreground">
                    {t('factor')}
                  </th>
                  <th className="text-left py-2 px-2 font-medium text-muted-foreground">
                    {t('subject')}
                  </th>
                  <th className="text-left py-2 px-2 font-medium text-muted-foreground">
                    {t('comparableLabel')}
                  </th>
                  <th className="text-center py-2 px-2 font-medium text-muted-foreground w-24">
                    {t('adjPercent')}
                  </th>
                  <th className="text-right py-2 px-2 font-medium text-muted-foreground">
                    {t('amount')}
                  </th>
                </tr>
              </thead>
              <tbody>
                {comp.adjustments.map((adj, adjIndex) => (
                  <tr key={adjIndex} className="border-b last:border-b-0">
                    <td className="py-2 px-2">
                      <span className={`text-xs font-medium ${getCategoryColor(adj.category)}`}>
                        {adj.category}
                      </span>
                      <p className="text-xs text-muted-foreground mt-0.5">{adj.description}</p>
                    </td>
                    <td className="py-2 px-2 text-xs">{adj.subject_value || '-'}</td>
                    <td className="py-2 px-2 text-xs">{adj.comp_value || '-'}</td>
                    <td className="py-2 px-2 text-center">
                      <input
                        type="number"
                        className="w-16 border rounded px-2 py-1 text-center text-xs"
                        value={adj.adjustment_percent}
                        onChange={(e) =>
                          handleAdjustmentChange(
                            compIndex,
                            adjIndex,
                            parseFloat(e.target.value) || 0
                          )
                        }
                      />
                      %
                    </td>
                    <td
                      className={`py-2 px-2 text-right text-xs font-medium ${
                        adj.adjustment_amount >= 1
                          ? 'text-success'
                          : adj.adjustment_amount < 1
                            ? 'text-destructive'
                            : ''
                      }`}
                    >
                      {adj.adjustment_amount >= 1 ? '+' : ''}
                      {formatCurrency(Math.abs(adj.adjustment_amount))}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Total */}
          <div className="flex justify-between items-center mt-3 pt-2 border-t bg-muted/30 rounded">
            <span className="text-sm font-medium">{t('totalAdjustments')}</span>
            <div className="text-right">
              <span
                className={`text-lg font-semibold ${
                  getTotalAdjustments(comp) >= 1 ? 'text-success' : 'text-destructive'
                }`}
              >
                {getTotalAdjustments(comp) >= 1 ? '+' : '-'}
                {formatCurrency(Math.abs(getTotalAdjustments(comp)))}
              </span>
              <p className="text-xs text-muted-foreground">
                {t('adjustedPrice')} {formatCurrency(comp.adjusted_price)}
              </p>
            </div>
          </div>
        </div>
      ))}

      {/* Summary */}
      <div className="mt-6 p-4 bg-muted/50 rounded-lg">
        <h4 className="text-sm font-medium mb-2">{t('adjustmentSummary')}</h4>
        <div className="grid grid-cols-3 gap-4 text-sm">
          <div>
            <p className="text-muted-foreground">{t('avgAdjustment')}</p>
            <p className="font-medium">{formatCurrency(getAverageAdjustment(comparables))}</p>
          </div>
          <div>
            <p className="text-muted-foreground">{t('priceRange')}</p>
            <p className="font-medium">
              {formatCurrency(getLowestPrice(comparables))} -{' '}
              {formatCurrency(getHighestPrice(comparables))}
            </p>
          </div>
          <div>
            <p className="text-muted-foreground">{t('medianPrice')}</p>
            <p className="font-medium">{formatCurrency(getMedianPrice(comparables))}</p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <div className="flex justify-between pt-4">
        <Button variant="outline" onClick={onPrev}>
          {t('back')}
        </Button>
        <Button onClick={onNext}>{t('nextPreview')}</Button>
      </div>
    </div>
  );
}
