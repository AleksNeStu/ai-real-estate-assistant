'use client';

import React, { useMemo, useState } from 'react';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import { useLocale, useTranslations } from 'next-intl';
import { Loader2, TrendingUp } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { EmptyState, ErrorState } from '@/components/ui/states';
import { MonoAnnotation } from '@/components/ui/mono-annotation';
import { PageHeader } from '@/components/ui/page-header';
import { ForecastChart } from '@/components/valuation/forecast-chart';
import { ForecastLedger } from '@/components/valuation/forecast-ledger';
import { priceForecastApi } from '@/lib/api';
import type { PriceForecastResponse } from '@/lib/api/tools';
import { formatPrice } from '@/lib/format';

type FeatureForm = {
  city: string;
  neighborhood: string;
  property_type: string;
  area_sqm: string;
  rooms: string;
  year_built: string;
  price: string;
  currency: string;
};

const DEFAULT_FORM: FeatureForm = {
  city: '',
  neighborhood: '',
  property_type: 'apartment',
  area_sqm: '',
  rooms: '',
  year_built: '',
  price: '',
  currency: 'EUR',
};

const HORIZON_OPTIONS = [1, 3, 5, 10];

/** How the reader names the property: the catalogue's own id, or its facts. */
type ValuationMode = 'id' | 'features';

export default function ValuationPage() {
  const t = useTranslations('pages.valuation');
  const locale = useLocale();
  const params = useSearchParams();
  const initialPropertyId = params?.get('property_id') ?? '';

  const [mode, setMode] = useState<ValuationMode>(initialPropertyId ? 'id' : 'features');
  const [propertyId, setPropertyId] = useState<string>(initialPropertyId);
  const [form, setForm] = useState<FeatureForm>(DEFAULT_FORM);
  const [horizons, setHorizons] = useState<number[]>([1, 3, 5]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<PriceForecastResponse | null>(null);

  const features = useMemo(() => {
    if (mode !== 'features') return null;
    const out: Record<string, unknown> = {};
    if (form.city.trim()) out.city = form.city.trim();
    if (form.neighborhood.trim()) out.neighborhood = form.neighborhood.trim();
    if (form.property_type.trim()) out.property_type = form.property_type.trim();
    if (form.area_sqm.trim()) {
      const v = Number(form.area_sqm);
      if (Number.isFinite(v) && v > 0) out.area_sqm = v;
    }
    if (form.rooms.trim()) {
      const v = Number(form.rooms);
      if (Number.isFinite(v) && v > 0) out.rooms = v;
    }
    if (form.year_built.trim()) {
      const v = Number(form.year_built);
      if (Number.isFinite(v) && v > 1500 && v < 2100) out.year_built = v;
    }
    if (form.price.trim()) {
      const v = Number(form.price);
      if (Number.isFinite(v) && v > 0) out.price = v;
    }
    if (form.currency.trim()) out.currency = form.currency.trim().toUpperCase();
    return Object.keys(out).length ? out : null;
  }, [form, mode]);

  const canSubmit = mode === 'id' ? propertyId.trim().length > 0 : features !== null;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setResult(null);
    if (!canSubmit) {
      setError(mode === 'features' ? t('errors.requiredFields') : t('errors.propertyId'));
      return;
    }
    setLoading(true);
    try {
      const res = await priceForecastApi({
        property_id: mode === 'id' ? propertyId.trim() : undefined,
        property_features: mode === 'features' ? (features ?? undefined) : undefined,
        horizon_years: horizons,
      });
      setResult(res);
    } catch (err: unknown) {
      const msg =
        err && typeof err === 'object' && 'message' in err
          ? String((err as { message: unknown }).message)
          : t('errors.forecastFailed');
      setError(msg);
    } finally {
      setLoading(false);
    }
  }

  const toggleHorizon = (years: number) => {
    setHorizons((prev) =>
      prev.includes(years)
        ? prev.filter((h) => h !== years)
        : [...prev, years].sort((a, b) => a - b)
    );
  };

  return (
    <div className="flex min-h-[calc(100vh-56px)] flex-col">
      <div className="border-b border-border px-6 pb-5 pt-6">
        <PageHeader
          title={t('title')}
          description={t('description')}
          actions={<MonoAnnotation>{t('source')}</MonoAnnotation>}
        />
      </div>

      <div className="grid flex-1 gap-6 px-6 py-6 lg:grid-cols-[380px_minmax(0,1fr)]">
        <form
          onSubmit={handleSubmit}
          className="flex flex-col gap-4 border-b border-border pb-6 lg:border-b-0 lg:border-r lg:pb-0 lg:pr-6"
          data-testid="valuation-form"
        >
          <div className="grid grid-cols-2 overflow-hidden rounded-md border border-border">
            <button
              type="button"
              onClick={() => setMode('id')}
              aria-pressed={mode === 'id'}
              className={[
                'h-[34px] text-[13px] font-medium transition-colors',
                mode === 'id'
                  ? 'bg-foreground text-background'
                  : 'bg-background text-foreground hover:bg-muted',
              ].join(' ')}
            >
              {t('mode.byId')}
            </button>
            <button
              type="button"
              onClick={() => setMode('features')}
              aria-pressed={mode === 'features'}
              className={[
                'h-[34px] text-[13px] font-medium transition-colors',
                mode === 'features'
                  ? 'bg-foreground text-background'
                  : 'bg-background text-foreground hover:bg-muted',
              ].join(' ')}
            >
              {t('mode.byFeatures')}
            </button>
          </div>

          {mode === 'id' ? (
            <div className="flex flex-col gap-1.5">
              <label htmlFor="property_id" className="text-[12px] font-medium text-foreground">
                {t('form.propertyId')}
              </label>
              <input
                id="property_id"
                type="text"
                placeholder={t('propertyIdPlaceholder')}
                className="h-[38px] rounded-md border border-input bg-background px-2.5 font-mono text-[13px] text-foreground outline-none focus-visible:outline-2 focus-visible:outline-ring/50"
                value={propertyId}
                onChange={(e) => setPropertyId(e.target.value)}
                disabled={loading}
              />
              <span className="text-[12px] text-muted-foreground">{t('form.propertyIdHint')}</span>
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <Field
                label={t('form.city')}
                value={form.city}
                onChange={(v) => setForm((f) => ({ ...f, city: v }))}
                disabled={loading}
              />
              <Field
                label={t('form.neighborhood')}
                value={form.neighborhood}
                onChange={(v) => setForm((f) => ({ ...f, neighborhood: v }))}
                disabled={loading}
              />
              <Field
                label={t('form.type')}
                value={form.property_type}
                onChange={(v) => setForm((f) => ({ ...f, property_type: v }))}
                disabled={loading}
                placeholder={t('form.typePlaceholder')}
              />
              <Field
                label={t('form.area')}
                value={form.area_sqm}
                onChange={(v) => setForm((f) => ({ ...f, area_sqm: v }))}
                disabled={loading}
                inputMode="decimal"
              />
              <Field
                label={t('form.rooms')}
                value={form.rooms}
                onChange={(v) => setForm((f) => ({ ...f, rooms: v }))}
                disabled={loading}
                inputMode="decimal"
              />
              <Field
                label={t('form.yearBuilt')}
                value={form.year_built}
                onChange={(v) => setForm((f) => ({ ...f, year_built: v }))}
                disabled={loading}
                inputMode="numeric"
              />
              <Field
                label={t('form.askingPrice')}
                value={form.price}
                onChange={(v) => setForm((f) => ({ ...f, price: v }))}
                disabled={loading}
                inputMode="decimal"
              />
              <Field
                label={t('form.currency')}
                value={form.currency}
                onChange={(v) => setForm((f) => ({ ...f, currency: v }))}
                disabled={loading}
                placeholder={t('form.currencyPlaceholder')}
              />
            </div>
          )}

          <div className="flex flex-col gap-1.5">
            <span className="text-[12px] font-medium text-foreground">{t('horizons.title')}</span>
            <div className="flex flex-wrap gap-1.5">
              {HORIZON_OPTIONS.map((years) => {
                const active = horizons.includes(years);
                return (
                  <button
                    key={years}
                    type="button"
                    aria-pressed={active}
                    onClick={() => toggleHorizon(years)}
                    disabled={loading}
                    className={[
                      'h-8 flex-1 rounded-md border px-2 font-mono text-[13px] font-medium transition-colors',
                      active
                        ? 'border-foreground bg-foreground text-background'
                        : 'border-border bg-background text-foreground hover:bg-muted',
                    ].join(' ')}
                  >
                    {t('horizons.short', { years })}
                  </button>
                );
              })}
            </div>
          </div>

          <Button
            type="submit"
            disabled={loading || !canSubmit}
            data-testid="valuation-submit"
            className="w-full"
          >
            {loading ? (
              <>
                <Loader2 className="size-4 animate-spin" aria-hidden />
                {t('form.estimating')}
              </>
            ) : (
              <>
                <TrendingUp className="size-4" aria-hidden />
                {t('form.getForecast')}
              </>
            )}
          </Button>

          {mode === 'features' ? (
            <span className="text-[12px] text-muted-foreground">{t('form.enableHint')}</span>
          ) : null}
        </form>

        <div className="flex min-w-0 flex-col gap-6">
          {error ? (
            <ErrorState title={t('errors.forecastFailed')} description={error} />
          ) : null}

          {result ? (
            <>
              <ForecastLedger result={result} />

              <ForecastChart result={result} />

              <div className="grid gap-6 md:grid-cols-2">
                <section className="flex flex-col gap-2">
                  <h2 className="text-[14px] font-semibold text-foreground">
                    {t('result.keyDrivers')}
                  </h2>
                  {result.drivers && result.drivers.length ? (
                    <ul className="border-t border-foreground">
                      {result.drivers.map((driver, index) => (
                        <li
                          key={`${driver}-${index}`}
                          className="border-b border-border py-2.5 text-[14px] leading-5 text-foreground"
                        >
                          {driver}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-[14px] text-muted-foreground">{t('result.noDrivers')}</p>
                  )}
                </section>

                <section className="flex flex-col gap-2">
                  <h2 className="text-[14px] font-semibold text-foreground">
                    {t('result.confidence')}
                  </h2>
                  <p className="font-mono text-h3 font-semibold leading-6 text-foreground">
                    {Math.round(result.confidence * 100)}%
                  </p>
                  <p className="text-[12px] text-muted-foreground">
                    {t('result.comparablesUsed')}: {result.comparables_used}
                  </p>
                  {result.median_price_per_sqm ? (
                    <p className="text-[12px] text-muted-foreground">
                      {t('result.cityMedian')}:{' '}
                      {formatPrice(result.median_price_per_sqm, result.currency || 'EUR', locale)}
                      /m²
                    </p>
                  ) : null}
                  {result.neighborhood_median_price_per_sqm ? (
                    <p className="text-[12px] text-muted-foreground">
                      {t('result.neighborhoodMedian')}:{' '}
                      {formatPrice(
                        result.neighborhood_median_price_per_sqm,
                        result.currency || 'EUR',
                        locale
                      )}
                      /m²
                    </p>
                  ) : null}
                  {result.explanation ? (
                    <p className="text-[14px] leading-5 text-muted-foreground">
                      {result.explanation}
                    </p>
                  ) : null}
                  <p className="text-[12px] text-muted-foreground">{result.disclaimer}</p>
                  <Link
                    href={`/${locale}/cma`}
                    className="text-[14px] font-medium text-foreground hover:underline"
                  >
                    {t('result.buildCma')}
                  </Link>
                </section>
              </div>
            </>
          ) : (
            <EmptyState title={t('empty.title')} description={t('empty.description')} />
          )}
        </div>
      </div>
    </div>
  );
}

interface FieldProps {
  label: string;
  value: string;
  onChange: (v: string) => void;
  disabled?: boolean;
  placeholder?: string;
  inputMode?: 'text' | 'numeric' | 'decimal';
}

function Field({ label, value, onChange, disabled, placeholder, inputMode }: FieldProps) {
  return (
    <div className="flex flex-col gap-1.5">
      <label className="text-[12px] font-medium text-foreground">{label}</label>
      <input
        type="text"
        inputMode={inputMode ?? 'text'}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        disabled={disabled}
        className="h-[38px] rounded-md border border-input bg-background px-2.5 font-mono text-[13px] text-foreground outline-none focus-visible:outline-2 focus-visible:outline-ring/50"
      />
    </div>
  );
}
