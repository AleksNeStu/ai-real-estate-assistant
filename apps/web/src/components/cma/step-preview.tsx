'use client';

import React, { useState, useEffect } from 'react';
import { useLocale, useTranslations } from 'next-intl';
import { Button } from '@/components/ui/button';
import { MonoAnnotation } from '@/components/ui/mono-annotation';
import { formatPrice as formatPriceInLocale } from '@/lib/format';
import { generateCMAReport } from '@/lib/api';
import type { Property, CMAComparable } from '@/lib/types';

import { subjectPriceOf, type CMAReportResponse } from './report';

interface StepPreviewProps {
  subjectProperty: Property | null;
  comparables: CMAComparable[];
  report: CMAReportResponse | null;
  onReportGenerated: (report: CMAReportResponse) => void;
}

/**
 * The report.
 *
 * The design draws it as a card with a rule under its title and four
 * numbers under that: the indicated value, the range it sits in, the
 * adjusted price per m² and what the asking price is against it.
 *
 * Every number comes from the report the API generated. The asking price
 * is the one the report carries - the forecast route cannot compare
 * against an asking price, because the forecast never returns one.
 */
export function StepPreview({
  subjectProperty,
  comparables,
  report,
  onReportGenerated,
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
    // The report carries no currency of its own - the subject's is the one
    // every number in it is in.
    return formatPriceInLocale(value, currency || subjectProperty?.currency || 'EUR', locale);
  };

  if (isGenerating) {
    return (
      <p className="text-[14px] text-muted-foreground" role="status">
        {t('generating')}
      </p>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col gap-3">
        <p className="text-[14px] text-destructive" role="alert">
          {error}
        </p>
        <Button onClick={generateReport} className="self-start">
          {t('tryAgain')}
        </Button>
      </div>
    );
  }

  if (!report) {
    return (
      <div className="flex flex-col gap-3">
        <p className="text-[14px] text-muted-foreground">{t('noReport')}</p>
        <Button onClick={generateReport} disabled={!subjectProperty?.id} className="self-start">
          {t('generateReport')}
        </Button>
      </div>
    );
  }

  const askingPrice = subjectPriceOf(report, subjectProperty?.price ?? null);
  const versusAsking =
    askingPrice && report.valuation.estimated_value
      ? (askingPrice / report.valuation.estimated_value - 1) * 100
      : null;

  return (
    <div className="flex flex-col gap-5">
      <section className="rounded-lg border border-border p-6">
        <div className="flex flex-wrap items-baseline justify-between gap-3">
          <h3 className="text-[18px] font-semibold text-foreground">
            {t('reportTitle', {
              subject:
                subjectProperty?.address ||
                subjectProperty?.district ||
                subjectProperty?.city ||
                t('report'),
            })}
          </h3>
          <MonoAnnotation>
            {t('prepared', { date: new Date(report.created_at).toLocaleDateString(locale) })}
          </MonoAnnotation>
        </div>

        <dl className="mt-4 grid grid-cols-2 gap-x-4 gap-y-3 border-t border-foreground pt-3 sm:grid-cols-4">
          <div className="flex flex-col gap-0.5">
            <dt className="text-[12px] leading-4 text-muted-foreground">
              {t('estimatedValue')}
            </dt>
            <dd className="font-mono text-[20px] font-semibold leading-6 text-foreground">
              {formatCurrency(report.valuation.estimated_value)}
            </dd>
          </div>
          <div className="flex flex-col gap-0.5">
            <dt className="text-[12px] leading-4 text-muted-foreground">
              {t('rangeLabel')}
            </dt>
            <dd className="font-mono text-[16px] font-semibold leading-6 text-foreground">
              {formatCurrency(report.valuation.value_range_low)} –{' '}
              {formatCurrency(report.valuation.value_range_high)}
            </dd>
          </div>
          <div className="flex flex-col gap-0.5">
            <dt className="text-[12px] leading-4 text-muted-foreground">
              {t('pricePerSqm')}
            </dt>
            <dd className="font-mono text-[16px] font-semibold leading-6 text-foreground">
              {formatCurrency(report.valuation.price_per_sqm)}/m²
            </dd>
          </div>
          <div className="flex flex-col gap-0.5">
            <dt className="text-[12px] leading-4 text-muted-foreground">
              {t('askingVsValue')}
            </dt>
            <dd className="font-mono text-[16px] font-semibold leading-6 text-foreground">
              {versusAsking === null ? '—' : `${versusAsking > 0 ? '+' : ''}${versusAsking.toFixed(1)}%`}
            </dd>
          </div>
        </dl>

        <p className="mt-4 text-[14px] leading-5 text-muted-foreground">
          {t('summary', { count: report.comparables.length })}
        </p>
      </section>

      <section className="flex flex-col">
        <div className="flex items-baseline justify-between gap-3">
          <h3 className="text-[14px] font-semibold text-foreground">
            {t('comparables', { count: report.comparables.length })}
          </h3>
          <MonoAnnotation>{t('similarity')}</MonoAnnotation>
        </div>

        <div className="mt-1 border-t border-foreground">
          {report.comparables.map((comp, index) => (
            <div
              key={comp.property_id}
              className="grid grid-cols-[28px_minmax(0,1fr)_auto_auto] items-baseline gap-x-4 border-b border-border py-2.5"
            >
              <span className="font-mono text-[12px] text-muted-foreground">
                #{index + 1}
              </span>
              <span className="truncate text-[14px] text-foreground">
                {t('property')} {comp.property_id.slice(0, 8)}
              </span>
              <span className="font-mono text-[12px] text-muted-foreground">
                {comp.similarity_score.toFixed(1)}
              </span>
              <span className="text-right font-mono text-[14px] text-foreground">
                {formatCurrency(comp.adjusted_price)}
              </span>
            </div>
          ))}
        </div>
      </section>

      {report.market_trend || report.market_avg_price_per_sqm ? (
        <section className="grid grid-cols-1 gap-4 border-t border-foreground pt-3 sm:grid-cols-3">
          <div className="flex flex-col gap-0.5">
            <span className="text-[12px] leading-4 text-muted-foreground">{t('trend')}</span>
            <span className="font-mono text-[14px] text-foreground">
              {report.market_trend ?? '—'}
            </span>
          </div>
          <div className="flex flex-col gap-0.5">
            <span className="text-[12px] leading-4 text-muted-foreground">
              {t('avgPricePerSqm')}
            </span>
            <span className="font-mono text-[14px] text-foreground">
              {report.market_avg_price_per_sqm
                ? formatCurrency(report.market_avg_price_per_sqm)
                : '—'}
            </span>
          </div>
          <div className="flex flex-col gap-0.5">
            <span className="text-[12px] leading-4 text-muted-foreground">
              {t('inventoryDays')}
            </span>
            <span className="font-mono text-[14px] text-foreground">
              {report.market_inventory_days ?? '—'}
            </span>
          </div>
        </section>
      ) : null}
    </div>
  );
}
