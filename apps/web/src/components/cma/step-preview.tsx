'use client';

import React, { useState, useEffect } from 'react';
import { useLocale } from 'next-intl';
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
      setError('No subject property selected');
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
      const message = err instanceof Error ? err.message : 'Failed to generate report';
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
    if (score >= 80) return 'High';
    if (score >= 60) return 'Medium';
    return 'Low';
  };

  if (isGenerating) {
    return (
      <div className="flex flex-col items-center justify-center py-12">
        <div
          className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mb-4"
          aria-hidden="true"
        ></div>
        <p className="text-muted-foreground">Generating CMA report...</p>
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
            Back
          </Button>
          <Button onClick={generateReport}>Try Again</Button>
        </div>
      </div>
    );
  }

  if (!report) {
    return (
      <div className="space-y-4">
        <div className="text-center py-8 text-muted-foreground">
          No report generated yet. Click Generate to create the CMA report.
        </div>
        <div className="flex justify-between">
          <Button variant="outline" onClick={onPrev}>
            Back
          </Button>
          <Button onClick={generateReport} disabled={!subjectProperty?.id}>
            Generate Report
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Executive Summary */}
      <div className="border rounded-lg p-4">
        <h3 className="font-semibold text-lg mb-4">Executive Summary</h3>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Estimated Value */}
          <div className="bg-primary/5 rounded-lg p-4">
            <p className="text-sm text-muted-foreground">Estimated Market Value</p>
            <p className="text-3xl font-bold text-primary mt-1">
              {formatCurrency(report.valuation.estimated_value)}
            </p>
            <div className="flex items-center gap-2 mt-2">
              <span className="text-sm text-muted-foreground">Range:</span>
              <span className="text-sm font-medium">
                {formatCurrency(report.valuation.value_range_low)} -{' '}
                {formatCurrency(report.valuation.value_range_high)}
              </span>
            </div>
          </div>

          {/* Confidence Score */}
          <div className="bg-muted/30 rounded-lg p-4">
            <p className="text-sm text-muted-foreground">Confidence Score</p>
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
            <span className="text-sm text-muted-foreground">Price per m²</span>
            <span className="font-semibold">
              {formatCurrency(report.valuation.price_per_sqm)}/m²
            </span>
          </div>
        </div>
      </div>

      {/* Subject Property Summary */}
      <div className="border rounded-lg p-4">
        <h3 className="font-semibold mb-3">Subject Property</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          <div>
            <span className="text-muted-foreground">Location</span>
            <p className="font-medium mt-1">{subjectProperty?.address || subjectProperty?.city}</p>
          </div>
          <div>
            <span className="text-muted-foreground">Area</span>
            <p className="font-medium mt-1">
              {subjectProperty?.area_sqm ? `${subjectProperty.area_sqm} m²` : 'N/A'}
            </p>
          </div>
          <div>
            <span className="text-muted-foreground">Rooms</span>
            <p className="font-medium mt-1">{subjectProperty?.rooms || 'N/A'}</p>
          </div>
          <div>
            <span className="text-muted-foreground">Type</span>
            <p className="font-medium mt-1 capitalize">{subjectProperty?.property_type}</p>
          </div>
        </div>
      </div>

      {/* Comparables Summary */}
      <div className="border rounded-lg p-4">
        <h3 className="font-semibold mb-3">Comparables ({report.comparables.length})</h3>
        <div className="space-y-2">
          {report.comparables.map((comp, index) => (
            <div
              key={comp.property_id}
              className="flex items-center justify-between p-2 bg-muted/30 rounded text-sm"
            >
              <div className="flex items-center gap-3">
                <span className="text-muted-foreground w-6">#{index + 1}</span>
                <span>Property {comp.property_id.slice(0, 8)}...</span>
                <span className="text-xs text-muted-foreground">
                  Score: {comp.similarity_score.toFixed(1)}
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
          <h3 className="font-semibold mb-3">Market Context</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div>
              <span className="text-muted-foreground">Avg Price/m²</span>
              <p className="font-medium mt-1">
                {formatCurrency((report.market_context.avg_price_per_sqm as number) || 0)}
              </p>
            </div>
            <div>
              <span className="text-muted-foreground">Median Price</span>
              <p className="font-medium mt-1">
                {formatCurrency((report.market_context.median_price as number) || 0)}
              </p>
            </div>
            <div>
              <span className="text-muted-foreground">Trend</span>
              <p className="font-medium mt-1 capitalize">
                {(report.market_context.trend as string) || 'N/A'}
              </p>
            </div>
            <div>
              <span className="text-muted-foreground">Inventory</span>
              <p className="font-medium mt-1">
                {(report.market_context.inventory_count as number) || 0} listings
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Navigation */}
      <div className="flex justify-between pt-4">
        <Button variant="outline" onClick={onPrev}>
          Back
        </Button>
        <Button onClick={onNext}>Next: Export Options</Button>
      </div>
    </div>
  );
}
