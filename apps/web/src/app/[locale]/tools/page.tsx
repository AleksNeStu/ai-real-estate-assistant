'use client';
import React, { useEffect, useMemo, useState } from 'react';
import { useTranslations } from 'next-intl';
import {
  calculateMortgage,
  comparePropertiesApi,
  exportPropertiesByIds,
  priceAnalysisApi,
  locationAnalysisApi,
  neighborhoodQualityApi,
  valuationApi,
  legalCheckApi,
  enrichAddressApi,
  crmSyncContactApi,
  applyPromptTemplate,
  listPromptTemplates,
} from '@/lib/api';
import type { PromptTemplateInfo, NeighborhoodQualityResult } from '@/lib/types';

import { PageHeader } from '@/components/ui/page-header';

type ToolTranslator = (key: string) => string;

export default function ToolsPage() {
  const t = useTranslations('pages.tools');

  return (
    <div className="container mx-auto px-4 py-8 space-y-8">
      <PageHeader title={t('title')} description={t('description')} />
      <MortgageSection />
      <CompareSection />
      <PriceAnalysisSection />
      <LocationAnalysisSection />
      <NeighborhoodQualitySection />
      <PromptTemplatesSection />
      <hr className="my-4" />
      <ValuationSection />
      <LegalCheckSection />
      <EnrichAddressSection />
      <CrmSyncSection />
    </div>
  );
}

function MortgageSection() {
  const t = useTranslations('pages.tools');
  const [propertyPrice, setPropertyPrice] = useState<string>('');
  const [downPaymentPercent, setDownPaymentPercent] = useState<string>('20');
  const [interestRate, setInterestRate] = useState<string>('6.5');
  const [loanYears, setLoanYears] = useState<string>('30');
  const [result, setResult] = useState<null | { monthly_payment: number }>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const hint = error ? getToolHint(error, t) : null;
  return (
    <section>
      <h2 className="text-xl font-medium">{t('mortgage.title')}</h2>
      <div className="grid grid-cols-2 gap-2 my-2">
        <input
          className="border p-2"
          placeholder={t('propertyPrice')}
          value={propertyPrice}
          onChange={(e) => setPropertyPrice(e.target.value)}
        />
        <input
          className="border p-2"
          placeholder={t('mortgage.downPayment')}
          value={downPaymentPercent}
          onChange={(e) => setDownPaymentPercent(e.target.value)}
        />
        <input
          className="border p-2"
          placeholder={t('mortgage.interestRate')}
          value={interestRate}
          onChange={(e) => setInterestRate(e.target.value)}
        />
        <input
          className="border p-2"
          placeholder={t('mortgage.loanYears')}
          value={loanYears}
          onChange={(e) => setLoanYears(e.target.value)}
        />
      </div>
      <button
        type="button"
        className="bg-black text-white px-3 py-2 rounded focus-visible:outline-none focus-visible:outline-2 focus-visible:outline-ring/50"
        onClick={async () => {
          setError(null);
          setLoading(true);
          try {
            const res = await calculateMortgage({
              property_price: parseFloat(propertyPrice),
              down_payment_percent: parseFloat(downPaymentPercent),
              interest_rate: parseFloat(interestRate),
              loan_years: parseInt(loanYears, 10),
            });
            setResult(res);
          } catch (e: unknown) {
            const msg = e instanceof Error ? e.message : String(e);
            setError(msg || t('mortgage.failed'));
          } finally {
            setLoading(false);
          }
        }}
      >
        {loading ? t('mortgage.calculating') : t('mortgage.calculate')}
      </button>
      {error && <p className="text-destructive mt-2">{error}</p>}
      {hint && <p className="text-sm text-muted-foreground mt-1">{hint}</p>}
      {result && (
        <p className="mt-2">
          {t('mortgage.monthlyPayment', { amount: result.monthly_payment.toFixed(2) })}
        </p>
      )}
    </section>
  );
}

function CompareSection() {
  const t = useTranslations('pages.tools');
  const [ids, setIds] = useState<string>('');
  const [data, setData] = useState<Awaited<ReturnType<typeof comparePropertiesApi>> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [exportFormat, setExportFormat] = useState<string>('csv');
  const [exportColumns, setExportColumns] = useState<string>('');
  const [exportIncludeHeader, setExportIncludeHeader] = useState<boolean>(true);
  const [csvDelimiter, setCsvDelimiter] = useState<string>(',');
  const [csvDecimal, setCsvDecimal] = useState<string>('.');
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);
  const hint = error ? getToolHint(error, t) : null;
  return (
    <section>
      <h2 className="text-xl font-medium">{t('compare.title')}</h2>
      <input
        className="border p-2 w-full my-2"
        placeholder={t('compare.ids')}
        value={ids}
        onChange={(e) => setIds(e.target.value)}
      />
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          className="bg-black text-white px-3 py-2 rounded focus-visible:outline-none focus-visible:outline-2 focus-visible:outline-ring/50"
          onClick={async () => {
            setError(null);
            setLoading(true);
            try {
              const res = await comparePropertiesApi(
                ids
                  .split(',')
                  .map((p) => p.trim())
                  .filter(Boolean)
              );
              setData(res);
            } catch (e: unknown) {
              const msg = e instanceof Error ? e.message : String(e);
              setError(msg || t('compare.failed'));
            } finally {
              setLoading(false);
            }
          }}
        >
          {loading ? t('compare.comparing') : t('compare.compare')}
        </button>
        <select
          className="border p-2 rounded"
          value={exportFormat}
          onChange={(e) => setExportFormat(e.target.value)}
          aria-label={t('compare.exportFormat')}
        >
          <option value="csv">CSV</option>
          <option value="xlsx">Excel</option>
          <option value="json">JSON</option>
          <option value="md">Markdown</option>
          <option value="pdf">PDF</option>
        </select>
        <button
          type="button"
          className="bg-black text-white px-3 py-2 rounded focus-visible:outline-none focus-visible:outline-2 focus-visible:outline-ring/50"
          disabled={exporting}
          onClick={async () => {
            setExportError(null);
            setExporting(true);
            try {
              const propertyIds = ids
                .split(',')
                .map((p) => p.trim())
                .filter(Boolean);
              if (!propertyIds.length) {
                setExportError(t('compare.needIds'));
                return;
              }
              const columns = exportColumns
                .split(',')
                .map((c) => c.trim())
                .filter(Boolean);
              const { filename, blob } = await exportPropertiesByIds(
                propertyIds,
                exportFormat as 'csv' | 'xlsx' | 'json' | 'md' | 'pdf',
                {
                  columns: columns.length ? columns : undefined,
                  include_header: exportIncludeHeader,
                  csv_delimiter: exportFormat === 'csv' ? csvDelimiter : undefined,
                  csv_decimal: exportFormat === 'csv' ? csvDecimal : undefined,
                }
              );
              const url = window.URL.createObjectURL(blob);
              const a = document.createElement('a');
              a.href = url;
              a.download = filename;
              document.body.appendChild(a);
              a.click();
              a.remove();
              window.URL.revokeObjectURL(url);
            } catch (e: unknown) {
              const msg = e instanceof Error ? e.message : String(e);
              setExportError(msg || t('compare.exportFailed'));
            } finally {
              setExporting(false);
            }
          }}
        >
          {exporting ? t('compare.exporting') : t('compare.export')}
        </button>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-2 my-2">
        <input
          className="border p-2 w-full"
          placeholder={t('columnsHint')}
          value={exportColumns}
          onChange={(e) => setExportColumns(e.target.value)}
          aria-label={t('compare.exportColumns')}
        />
        {exportFormat === 'csv' ? (
          <div className="grid grid-cols-2 gap-2">
            <select
              className="border p-2 rounded"
              value={csvDelimiter}
              onChange={(e) => setCsvDelimiter(e.target.value)}
              aria-label={t('compare.csvDelimiter')}
            >
              <option value=",">{t('compare.comma')}</option>
              <option value=";">{t('compare.semicolon')}</option>
            </select>
            <select
              className="border p-2 rounded"
              value={csvDecimal}
              onChange={(e) => setCsvDecimal(e.target.value)}
              aria-label={t('compare.csvDecimal')}
            >
              <option value=".">{t('compare.dot')}</option>
              <option value=",">{t('compare.comma')}</option>
            </select>
            <label className="flex items-center gap-2 text-sm col-span-2">
              <input
                type="checkbox"
                checked={exportIncludeHeader}
                onChange={(e) => setExportIncludeHeader(e.target.checked)}
                aria-label={t('compare.includeHeader')}
              />
              {t('compare.includeHeader')}
            </label>
          </div>
        ) : null}
      </div>
      {error && <p className="text-destructive mt-2">{error}</p>}
      {hint && <p className="text-sm text-muted-foreground mt-1">{hint}</p>}
      {exportError && <p className="text-destructive mt-2">{exportError}</p>}
      {data && (
        <div className="mt-2">
          <p>{t('fields.count', { value: data.summary?.count })}</p>
          <p>{t('fields.minPrice', { value: data.summary?.min_price ?? '-' })}</p>
          <p>{t('fields.maxPrice', { value: data.summary?.max_price ?? '-' })}</p>
          <p>{t('fields.diff', { value: data.summary?.price_difference ?? '-' })}</p>
        </div>
      )}
    </section>
  );
}

function PriceAnalysisSection() {
  const t = useTranslations('pages.tools');
  const [query, setQuery] = useState<string>('');
  const [data, setData] = useState<Awaited<ReturnType<typeof priceAnalysisApi>> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const hint = error ? getToolHint(error, t) : null;
  return (
    <section>
      <h2 className="text-xl font-medium">{t('price.title')}</h2>
      <input
        className="border p-2 w-full my-2"
        placeholder={t('price.query')}
        value={query}
        onChange={(e) => setQuery(e.target.value)}
      />
      <button
        type="button"
        className="bg-black text-white px-3 py-2 rounded focus-visible:outline-none focus-visible:outline-2 focus-visible:outline-ring/50"
        onClick={async () => {
          setError(null);
          setLoading(true);
          try {
            const res = await priceAnalysisApi(query);
            setData(res);
          } catch (e: unknown) {
            const msg = e instanceof Error ? e.message : String(e);
            setError(msg || t('price.failed'));
          } finally {
            setLoading(false);
          }
        }}
      >
        {loading ? t('price.analyzing') : t('analyze')}
      </button>
      {error && <p className="text-destructive mt-2">{error}</p>}
      {hint && <p className="text-sm text-muted-foreground mt-1">{hint}</p>}
      {data && (
        <div className="mt-2">
          <p>{t('fields.count', { value: data.count })}</p>
          <p>{t('fields.averagePrice', { value: data.average_price ?? '-' })}</p>
          <p>{t('fields.medianPrice', { value: data.median_price ?? '-' })}</p>
        </div>
      )}
    </section>
  );
}

function LocationAnalysisSection() {
  const t = useTranslations('pages.tools');
  const [pid, setPid] = useState<string>('');
  const [data, setData] = useState<Awaited<ReturnType<typeof locationAnalysisApi>> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const hint = error ? getToolHint(error, t) : null;
  return (
    <section>
      <h2 className="text-xl font-medium">{t('location.title')}</h2>
      <input
        className="border p-2 w-full my-2"
        placeholder={t('propertyId')}
        value={pid}
        onChange={(e) => setPid(e.target.value)}
      />
      <button
        type="button"
        className="bg-black text-white px-3 py-2 rounded focus-visible:outline-none focus-visible:outline-2 focus-visible:outline-ring/50"
        onClick={async () => {
          setError(null);
          setLoading(true);
          try {
            const res = await locationAnalysisApi(pid);
            setData(res);
          } catch (e: unknown) {
            const msg = e instanceof Error ? e.message : String(e);
            setError(msg || t('location.failed'));
          } finally {
            setLoading(false);
          }
        }}
      >
        {loading ? t('location.analyzing') : t('analyze')}
      </button>
      {error && <p className="text-destructive mt-2">{error}</p>}
      {hint && <p className="text-sm text-muted-foreground mt-1">{hint}</p>}
      {data && (
        <div className="mt-2">
          <p>{t('fields.city', { value: data.city ?? '-' })}</p>
          <p>{t('fields.neighborhood', { value: data.neighborhood ?? '-' })}</p>
          <p>{t('fields.latLon', { lat: data.lat ?? '-', lon: data.lon ?? '-' })}</p>
        </div>
      )}
    </section>
  );
}

function NeighborhoodQualitySection() {
  const t = useTranslations('pages.tools');
  const [propertyId, setPropertyId] = useState<string>('');
  const [lat, setLat] = useState<string>('');
  const [lon, setLon] = useState<string>('');
  const [city, setCity] = useState<string>('');
  const [neighborhood, setNeighborhood] = useState<string>('');
  const [data, setData] = useState<NeighborhoodQualityResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const hint = error ? getToolHint(error, t) : null;

  const getScoreColor = (score: number): string => {
    if (score >= 85) return 'text-success';
    if (score >= 70) return 'text-chart-7';
    if (score >= 55) return 'text-warning';
    if (score >= 40) return 'text-warning';
    return 'text-destructive';
  };

  const getRatingLabel = (score: number): string => {
    if (score >= 85) return t('neighborhood.excellent');
    if (score >= 70) return t('neighborhood.good');
    if (score >= 55) return t('neighborhood.fair');
    if (score >= 40) return t('neighborhood.poor');
    return t('neighborhood.veryPoor');
  };

  return (
    <section>
      <h2 className="text-xl font-medium">{t('neighborhood.title')}</h2>
      <div className="grid grid-cols-2 gap-2 my-2">
        <input
          className="border p-2"
          placeholder={t('propertyId')}
          value={propertyId}
          onChange={(e) => setPropertyId(e.target.value)}
        />
        <input
          className="border p-2"
          placeholder={t('neighborhood.latitude')}
          value={lat}
          onChange={(e) => setLat(e.target.value)}
        />
        <input
          className="border p-2"
          placeholder={t('neighborhood.longitude')}
          value={lon}
          onChange={(e) => setLon(e.target.value)}
        />
        <input
          className="border p-2"
          placeholder={t('neighborhood.city')}
          value={city}
          onChange={(e) => setCity(e.target.value)}
        />
        <input
          className="border p-2 col-span-2"
          placeholder={t('neighborhood.neighborhood')}
          value={neighborhood}
          onChange={(e) => setNeighborhood(e.target.value)}
        />
      </div>
      <button
        type="button"
        className="bg-black text-white px-3 py-2 rounded focus-visible:outline-none focus-visible:outline-2 focus-visible:outline-ring/50"
        onClick={async () => {
          setError(null);
          setLoading(true);
          try {
            const res = await neighborhoodQualityApi({
              property_id: propertyId,
              latitude: lat ? parseFloat(lat) : undefined,
              longitude: lon ? parseFloat(lon) : undefined,
              city: city || undefined,
              neighborhood: neighborhood || undefined,
            });
            setData(res);
          } catch (e: unknown) {
            const msg = e instanceof Error ? e.message : String(e);
            setError(msg || t('neighborhood.failed'));
          } finally {
            setLoading(false);
          }
        }}
      >
        {loading ? t('neighborhood.analyzing') : t('analyze')}
      </button>
      {error && <p className="text-destructive mt-2">{error}</p>}
      {hint && <p className="text-sm text-muted-foreground mt-1">{hint}</p>}
      {data && (
        <div className="mt-4 space-y-3">
          <div className="flex items-center gap-4">
            <h3 className="text-lg font-semibold">
              {t('neighborhood.overallScore')}:{' '}
              <span className={`${getScoreColor(data.overall_score)} text-2xl`}>
                {data.overall_score.toFixed(1)}
              </span>
              /100
            </h3>
            <span
              className={`px-2 py-1 rounded text-sm ${getScoreColor(data.overall_score)} bg-muted`}
            >
              {getRatingLabel(data.overall_score)}
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
            <ScoreBar label={t('neighborhood.safety')} score={data.safety_score} weight="25%" />
            <ScoreBar label={t('neighborhood.schools')} score={data.schools_score} weight="20%" />
            <ScoreBar
              label={t('neighborhood.amenities')}
              score={data.amenities_score}
              weight="20%"
            />
            <ScoreBar
              label={t('neighborhood.walkability')}
              score={data.walkability_score}
              weight="20%"
            />
            <ScoreBar
              label={t('neighborhood.greenSpace')}
              score={data.green_space_score}
              weight="15%"
            />
          </div>

          <div className="mt-4 p-3 bg-background rounded text-sm">
            <p className="font-semibold">{t('neighborhood.location')}</p>
            <p>{t('fields.city', { value: data.city || '-' })}</p>
            <p>{t('fields.neighborhood', { value: data.neighborhood || '-' })}</p>
            <p>
              {t('neighborhood.coordinates', {
                lat: data.latitude?.toFixed(4) || '-',
                lon: data.longitude?.toFixed(4) || '-',
              })}
            </p>
            <p className="mt-2 text-muted-foreground">
              {t('neighborhood.dataSources', { sources: data.data_sources.join(', ') })}
            </p>
          </div>
        </div>
      )}
    </section>
  );
}

function ScoreBar({ label, score, weight }: { label: string; score: number; weight: string }) {
  const t = useTranslations('pages.tools');
  const getScoreColor = (score: number): string => {
    if (score >= 85) return 'bg-success';
    if (score >= 70) return 'bg-chart-7';
    if (score >= 55) return 'bg-warning';
    if (score >= 40) return 'bg-warning';
    return 'bg-destructive';
  };

  return (
    <div>
      <div className="flex justify-between mb-1">
        <span className="text-sm font-medium">{label}</span>
        <span className="text-sm text-muted-foreground">
          {t('neighborhood.scoreBar', { score: score.toFixed(1), weight })}
        </span>
      </div>
      <div className="w-full bg-muted rounded-full h-2.5">
        <div
          className={`h-2.5 rounded-full ${getScoreColor(score)}`}
          style={{ width: `${score}%` }}
        ></div>
      </div>
    </div>
  );
}

function PromptTemplatesSection() {
  const t = useTranslations('pages.tools');
  const [templates, setTemplates] = useState<PromptTemplateInfo[]>([]);
  const [selectedId, setSelectedId] = useState<string>('');
  const [variables, setVariables] = useState<Record<string, string>>({});
  const [result, setResult] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const items = await listPromptTemplates();
        if (!mounted) return;
        setTemplates(items);
        if (items.length) {
          setSelectedId((prev) => prev || items[0].id);
        }
      } catch (e: unknown) {
        if (!mounted) return;
        const msg = e instanceof Error ? e.message : String(e);
        setError(msg || t('templates.loadFailed'));
      }
    })();
    return () => {
      mounted = false;
    };
  }, [t]);

  const selected = useMemo(
    () => templates.find((t) => t.id === selectedId) || null,
    [templates, selectedId]
  );

  useEffect(() => {
    if (!selected) return;
    setVariables((prev) => {
      const next: Record<string, string> = {};
      for (const v of selected.variables) {
        next[v.name] = prev[v.name] ?? '';
      }
      return next;
    });
    setResult('');
    setError(null);
  }, [selected]);

  return (
    <section>
      <h2 className="text-xl font-medium">{t('templates.title')}</h2>
      <p className="text-sm text-muted-foreground mt-1">{t('templates.description')}</p>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-2 my-2">
        <select
          className="border p-2 rounded"
          value={selectedId}
          onChange={(e) => setSelectedId(e.target.value)}
          aria-label={t('templates.picker')}
        >
          {templates.map((tpl) => (
            <option key={tpl.id} value={tpl.id}>
              {tpl.title}
            </option>
          ))}
        </select>
        {selected ? (
          <div className="text-sm text-muted-foreground flex items-center">
            {selected.description}
          </div>
        ) : null}
      </div>

      {selected ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-2 my-2">
          {selected.variables.map((v) => (
            <div key={v.name} className="flex flex-col gap-1">
              <label className="text-sm">
                {v.name}
                {v.required ? ' *' : ''}
              </label>
              <input
                className="border p-2"
                placeholder={v.example ? String(v.example) : v.description}
                value={variables[v.name] ?? ''}
                onChange={(e) =>
                  setVariables((prev) => ({
                    ...prev,
                    [v.name]: e.target.value,
                  }))
                }
                aria-label={t('templates.variable', { name: v.name })}
              />
              <span className="text-xs text-muted-foreground">{v.description}</span>
            </div>
          ))}
        </div>
      ) : null}

      <div className="flex flex-wrap gap-2 items-center">
        <button
          type="button"
          className="bg-black text-white px-3 py-2 rounded focus-visible:outline-none focus-visible:outline-2 focus-visible:outline-ring/50"
          disabled={!selected || loading}
          onClick={async () => {
            if (!selected) return;
            setError(null);
            setLoading(true);
            try {
              const vars: Record<string, string> = {};
              for (const v of selected.variables) {
                const raw = variables[v.name] ?? '';
                if (raw.trim()) vars[v.name] = raw.trim();
              }
              const res = await applyPromptTemplate(selected.id, vars);
              setResult(res.rendered_text);
            } catch (e: unknown) {
              const msg = e instanceof Error ? e.message : String(e);
              setError(msg || t('templates.renderFailed'));
              setResult('');
            } finally {
              setLoading(false);
            }
          }}
        >
          {loading ? t('templates.generating') : t('templates.generate')}
        </button>
        <button
          type="button"
          className="border px-3 py-2 rounded focus-visible:outline-none focus-visible:outline-2 focus-visible:outline-ring/50"
          disabled={!result}
          onClick={async () => {
            if (!result) return;
            try {
              await navigator.clipboard.writeText(result);
            } catch {}
          }}
        >
          {t('templates.copy')}
        </button>
      </div>
      {error && <p className="text-destructive mt-2">{error}</p>}
      {result ? (
        <textarea
          className="border p-2 w-full mt-2"
          rows={10}
          value={result}
          onChange={(e) => setResult(e.target.value)}
          aria-label={t('templates.output')}
        />
      ) : null}
    </section>
  );
}

function ValuationSection() {
  const t = useTranslations('pages.tools');
  const [pid, setPid] = useState<string>('');
  const [value, setValue] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const hint = error ? getToolHint(error, t) : null;
  return (
    <section>
      <h2 className="text-xl font-medium">{t('valuation.title')}</h2>
      <input
        className="border p-2 w-full my-2"
        placeholder={t('propertyId')}
        value={pid}
        onChange={(e) => setPid(e.target.value)}
      />
      <button
        type="button"
        className="bg-black text-white px-3 py-2 rounded focus-visible:outline-none focus-visible:outline-2 focus-visible:outline-ring/50"
        onClick={async () => {
          setError(null);
          setLoading(true);
          try {
            const res = await valuationApi(pid);
            setValue(res.estimated_value);
          } catch (e: unknown) {
            const msg = e instanceof Error ? e.message : String(e);
            setError(msg || t('valuation.failed'));
          } finally {
            setLoading(false);
          }
        }}
      >
        {loading ? t('valuation.estimating') : t('valuation.estimate')}
      </button>
      {error && <p className="text-destructive mt-2">{error}</p>}
      {hint && <p className="text-sm text-muted-foreground mt-1">{hint}</p>}
      {value !== null && (
        <p className="mt-2">{t('fields.estimatedValue', { value: value.toFixed(2) })}</p>
      )}
    </section>
  );
}

function LegalCheckSection() {
  const t = useTranslations('pages.tools');
  const [text, setText] = useState<string>('');
  const [data, setData] = useState<Awaited<ReturnType<typeof legalCheckApi>> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const hint = error ? getToolHint(error, t) : null;
  return (
    <section>
      <h2 className="text-xl font-medium">{t('legal.title')}</h2>
      <textarea
        className="border p-2 w-full my-2"
        placeholder={t('legal.contract')}
        rows={4}
        value={text}
        onChange={(e) => setText(e.target.value)}
      />
      <button
        type="button"
        className="bg-black text-white px-3 py-2 rounded focus-visible:outline-none focus-visible:outline-2 focus-visible:outline-ring/50"
        onClick={async () => {
          setError(null);
          setLoading(true);
          try {
            const res = await legalCheckApi(text);
            setData(res);
          } catch (e: unknown) {
            const msg = e instanceof Error ? e.message : String(e);
            setError(msg || t('legal.failed'));
          } finally {
            setLoading(false);
          }
        }}
      >
        {loading ? t('legal.analyzing') : t('analyze')}
      </button>
      {error && <p className="text-destructive mt-2">{error}</p>}
      {hint && <p className="text-sm text-muted-foreground mt-1">{hint}</p>}
      {data && (
        <div className="mt-2">
          <p>{t('fields.score', { value: data.score })}</p>
          <p>{t('fields.risks', { value: Array.isArray(data.risks) ? data.risks.length : 0 })}</p>
        </div>
      )}
    </section>
  );
}

function EnrichAddressSection() {
  const t = useTranslations('pages.tools');
  const [address, setAddress] = useState<string>('');
  const [data, setData] = useState<Awaited<ReturnType<typeof enrichAddressApi>> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const hint = error ? getToolHint(error, t) : null;
  return (
    <section>
      <h2 className="text-xl font-medium">{t('enrich.title')}</h2>
      <input
        className="border p-2 w-full my-2"
        placeholder={t('enrich.address')}
        value={address}
        onChange={(e) => setAddress(e.target.value)}
      />
      <button
        type="button"
        className="bg-black text-white px-3 py-2 rounded focus-visible:outline-none focus-visible:outline-2 focus-visible:outline-ring/50"
        onClick={async () => {
          setError(null);
          setLoading(true);
          try {
            const res = await enrichAddressApi(address);
            setData(res);
          } catch (e: unknown) {
            const msg = e instanceof Error ? e.message : String(e);
            setError(msg || t('enrich.failed'));
          } finally {
            setLoading(false);
          }
        }}
      >
        {loading ? t('enrich.enriching') : t('enrich.enrich')}
      </button>
      {error && <p className="text-destructive mt-2">{error}</p>}
      {hint && <p className="text-sm text-muted-foreground mt-1">{hint}</p>}
      {data && (
        <div className="mt-2">
          <p>{t('fields.address', { value: data.address })}</p>
          <pre className="bg-muted p-2 rounded text-sm">{JSON.stringify(data.data, null, 2)}</pre>
        </div>
      )}
    </section>
  );
}

function CrmSyncSection() {
  const t = useTranslations('pages.tools');
  const [name, setName] = useState<string>('');
  const [phone, setPhone] = useState<string>('');
  const [email, setEmail] = useState<string>('');
  const [id, setId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const hint = error ? getToolHint(error, t) : null;
  return (
    <section>
      <h2 className="text-xl font-medium">{t('crm.title')}</h2>
      <div className="grid grid-cols-3 gap-2 my-2">
        <input
          className="border p-2"
          placeholder={t('crm.name')}
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
        <input
          className="border p-2"
          placeholder={t('crm.phone')}
          value={phone}
          onChange={(e) => setPhone(e.target.value)}
        />
        <input
          className="border p-2"
          placeholder={t('crm.email')}
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
      </div>
      <button
        type="button"
        className="bg-black text-white px-3 py-2 rounded focus-visible:outline-none focus-visible:outline-2 focus-visible:outline-ring/50"
        onClick={async () => {
          setError(null);
          setLoading(true);
          try {
            const res = await crmSyncContactApi(name, phone || undefined, email || undefined);
            setId(res.id);
          } catch (e: unknown) {
            const msg = e instanceof Error ? e.message : String(e);
            setError(msg || t('crm.failed'));
          } finally {
            setLoading(false);
          }
        }}
      >
        {loading ? t('crm.syncing') : t('crm.sync')}
      </button>
      {error && <p className="text-destructive mt-2">{error}</p>}
      {hint && <p className="text-sm text-muted-foreground mt-1">{hint}</p>}
      {id && <p className="mt-2">{t('fields.contactId', { id })}</p>}
    </section>
  );
}

function getToolHint(error: string, t: ToolTranslator): string | null {
  if (error.includes('Data enrichment disabled')) {
    return t('hints.dataEnrichment');
  }
  if (error.includes('CRM connector not configured')) {
    return t('hints.crm');
  }
  if (error.includes('Valuation disabled')) {
    return t('hints.valuation');
  }
  if (error.includes('Legal check disabled')) {
    return t('hints.legalCheck');
  }
  if (error.includes('Vector store unavailable')) {
    return t('hints.vectorStore');
  }
  return null;
}
