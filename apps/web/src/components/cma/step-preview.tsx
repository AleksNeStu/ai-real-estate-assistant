'use client';

import React, { useState, useEffect } from 'react';
import { useLocale, useTranslations } from 'next-intl';
import { Button } from '@/components/ui/button';
import { formatPrice as formatPriceInLocale } from '@/lib/format';
import { generateCMAReport } from '@/lib/api';
import type { Property, CMAComparable, CMAReport } from '@/lib/types';

interface StepPreviewProps {
  subjectProperty: Property | null;
  comparables: CMAComparable[];
  report: CMAReport | null;
  onReportGenerated: (report: CMAReport) => void;
  onNext: () => void;
  onPrev: () => void;
}

export function StepPreview({
  subjectProperty,
  comparables,
  report,
  onReportGenerated,
  onNext,
  onPrev,
}: StepPreviewProps) {
  const locale = useLocale();
  const t = useTranslations('cma.preview');
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!report && subjectProperty?.id && comparables.length >= 3) {
      generateReport();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const generateReport = async () => {
    if (!subjectProperty?.id) {
      setError(t('noSubject'));
      return;
    }

    setIsGenerating(true);
    setError(null);

    try {
      const result = await generateCMAReport({
        subject_property_id: subjectProperty.id,
        comparable_ids: comparables.map((c) => c.property_id),
        min_comparables: 3,
        max_comparables: 6,
      });
      onReportGenerated(result);
    } catch (err) {
      const message = err instanceof Error ? err.message : t('failedGenerate');
      setError(message);
    } finally {
      setIsGenerating(false);
    }
  };

  const formatCurrency = (value: number, currency?: string) => {
    // The wizard used to force every price into euros with German separators,
    // whatever the listing said and whatever language the reader picked.
    return formatPriceInLocale(value, currency || 'EUR', locale);
  };

  const getConfidenceColor = (score: number): string => {
    if (score >= 80) return 'text-success';
    if (score >= 60) return 'text-warning';
    return 'text-warning';
  };

  const getConfidenceLabel = (score: number): string => {
    if (score >= 80) return t('confidenceHigh');
    if (score >= 60) return t('confidenceMedium');
    return t('confidenceLow');
  };

  if (isGenerating) {
    return (
      <div className="flex flex-col items-center justify-center py-12">
        <div
          className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mb-4"
          aria-hidden="true"
        ></div>
        <p className="text-muted-foreground">{t('generating')}</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-4">
        <div className="text-sm text-destructive bg-destructive/10 px-4 py-3 rounded" role="alert">
          {error}
        </div>
        <div className="flex justify-between">
          <Button variant="outline" onClick={onPrev}>
            {t('back')}
          </Button>
          <Button onClick={generateReport}>{t('tryAgain')}</Button>
        </div>
      </div>
    );
  }

  if (!report) {
    return (
      <div className="space-y-4">
        <div className="text-center py-8 text-muted-foreground">{t('noReport')}</div>
        <div className="flex justify-between">
          <Button variant="outline" onClick={onPrev}>
            {t('back')}
          </Button>
          <Button onClick={generateReport} disabled={!subjectProperty?.id}>
            {t('generateReport')}
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Executive Summary */}
      <div className="border rounded-lg p-4">
        <h3 className="font-semibold text-lg mb-4">{t('executiveSummary')}</h3>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Estimated Value */}
          <div className="bg-primary/5 rounded-lg p-4">
            <p className="text-sm text-muted-foreground">{t('estimatedValue')}</p>
            <p className="text-3xl font-bold text-primary mt-1">
              {formatCurrency(report.valuation.estimated_value)}
            </p>
            <div className="flex items-center gap-2 mt-2">
              <span className="text-sm text-muted-foreground">{t('range')}</span>
              <span className="text-sm font-medium">
                {formatCurrency(report.valuation.value_range_low)} -{' '}
                {formatCurrency(report.valuation.value_range_high)}
              </span>
            </div>
          </div>

          {/* Confidence Score */}
          <div className="bg-muted/30 rounded-lg p-4">
            <p className="text-sm text-muted-foreground">{t('confidenceScore')}</p>
            <div className="flex items-baseline gap-2 mt-1">
              <span
                className={`text-3xl font-bold ${getConfidenceColor(
                  report.valuation.confidence_score
                )}`}
              >
                {report.valuation.confidence_score.toFixed(0)}%
              </span>
              <span className="text-sm text-muted-foreground">
                ({getConfidenceLabel(report.valuation.confidence_score)})
              </span>
            </div>
            <div className="w-full bg-muted rounded-full h-2 mt-3">
              <div
                className={`h-2 rounded-full ${
                  report.valuation.confidence_score >= 80
                    ? 'bg-success'
                    : report.valuation.confidence_score >= 60
                      ? 'bg-warning'
                      : 'bg-warning'
                }`}
                style={{ width: `${report.valuation.confidence_score}%` }}
              ></div>
            </div>
          </div>
        </div>

        {/* Price per sqm */}
        <div className="mt-4 p-3 bg-muted/20 rounded">
          <div className="flex justify-between items-center">
            <span className="text-sm text-muted-foreground">{t('pricePerSqm')}</span>
            <span className="font-semibold">
              {formatCurrency(report.valuation.price_per_sqm)}/m²
            </span>
          </div>
        </div>
      </div>

      {/* Subject Property Summary */}
      <div className="border rounded-lg p-4">
        <h3 className="font-semibold mb-3">{t('subjectProperty')}</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          <div>
            <span className="text-muted-foreground">{t('location')}</span>
            <p className="font-medium mt-1">{subjectProperty?.address || subjectProperty?.city}</p>
          </div>
          <div>
            <span className="text-muted-foreground">{t('area')}</span>
            <p className="font-medium mt-1">
              {subjectProperty?.area_sqm ? `${subjectProperty.area_sqm} m²` : 'N/A'}
            </p>
          </div>
          <div>
            <span className="text-muted-foreground">{t('rooms')}</span>
            <p className="font-medium mt-1">{subjectProperty?.rooms || 'N/A'}</p>
          </div>
          <div>
            <span className="text-muted-foreground">{t('type')}</span>
            <p className="font-medium mt-1 capitalize">{subjectProperty?.property_type}</p>
          </div>
        </div>
      </div>

      {/* Comparables Summary */}
      <div className="border rounded-lg p-4">
        <h3 className="font-semibold mb-3">
          {t('comparables', { count: report.comparables.length })}
        </h3>
        <div className="space-y-2">
          {report.comparables.map((comp, index) => (
            <div
              key={comp.property_id}
              className="flex items-center justify-between p-2 bg-muted/30 rounded text-sm"
            >
              <div className="flex items-center gap-3">
                <span className="text-muted-foreground w-6">#{index + 1}</span>
                <span>
                  {t('property')} {comp.property_id.slice(0, 8)}...
                </span>
                <span className="text-xs text-muted-foreground">
                  {t('score')} {comp.similarity_score.toFixed(1)}
                </span>
              </div>
              <span className="font-medium">{formatCurrency(comp.adjusted_price)}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Market Context */}
      {report.market_context && (
        <div className="border rounded-lg p-4">
          <h3 className="font-semibold mb-3">{t('marketContext')}</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div>
              <span className="text-muted-foreground">{t('avgPricePerSqm')}</span>
              <p className="font-medium mt-1">
                {formatCurrency((report.market_context.avg_price_per_sqm as number) || 0)}
              </p>
            </div>
            <div>
              <span className="text-muted-foreground">{t('medianPrice')}</span>
              <p className="font-medium mt-1">
                {formatCurrency((report.market_context.median_price as number) || 0)}
              </p>
            </div>
            <div>
              <span className="text-muted-foreground">{t('trend')}</span>
              <p className="font-medium mt-1 capitalize">
                {(report.market_context.trend as string) || 'N/A'}
              </p>
            </div>
            <div>
              <span className="text-muted-foreground">{t('inventory')}</span>
              <p className="font-medium mt-1">
                {t('listings', { count: (report.market_context.inventory_count as number) || 0 })}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Navigation */}
      <div className="flex justify-between pt-4">
        <Button variant="outline" onClick={onPrev}>
          {t('back')}
        </Button>
        <Button onClick={onNext}>{t('nextExport')}</Button>
      </div>
    </div>
  );
}
