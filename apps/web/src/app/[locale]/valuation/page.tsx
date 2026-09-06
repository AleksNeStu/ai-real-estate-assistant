'use client';

import React, { useMemo, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { Sparkles, AlertTriangle, Loader2, TrendingUp, MapPin } from 'lucide-react';
import { priceForecastApi } from '@/lib/api';
import type { PriceForecastResponse, ForecastPoint } from '@/lib/api/tools';

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

const HORIZON_OPTIONS = [
  { label: '1 year', value: 1 },
  { label: '3 years', value: 3 },
  { label: '5 years', value: 5 },
  { label: '10 years', value: 10 },
];

function fmtCurrency(value: number, currency: string, locale = 'en-US'): string {
  try {
    return new Intl.NumberFormat(locale, {
      style: 'currency',
      currency,
      maximumFractionDigits: 0,
    }).format(value);
  } catch {
    return `${value.toLocaleString()} ${currency}`;
  }
}

export default function ValuationPage() {
  const params = useSearchParams();
  const initialPropertyId = params?.get('property_id') ?? '';
  const [propertyId, setPropertyId] = useState<string>(initialPropertyId);
  const [form, setForm] = useState<FeatureForm>(DEFAULT_FORM);
  const [horizons, setHorizons] = useState<number[]>([1, 3, 5]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<PriceForecastResponse | null>(null);

  const useFeatures = !propertyId.trim();
  const features = useMemo(() => {
    if (!useFeatures) return null;
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
  }, [form, useFeatures]);

  const canSubmit = (useFeatures && features !== null) || (!useFeatures && propertyId.trim());

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setResult(null);
    if (!canSubmit) {
      setError(
        useFeatures
          ? 'Please fill in at least city, area (sqm), and price (or use a property id).'
          : 'Please enter a property id.'
      );
      return;
    }
    setLoading(true);
    try {
      const res = await priceForecastApi({
        property_id: useFeatures ? undefined : propertyId.trim(),
        property_features: useFeatures ? features ?? undefined : undefined,
        horizon_years: horizons,
      });
      setResult(res);
    } catch (err: unknown) {
      const msg =
        err && typeof err === 'object' && 'message' in err
          ? String((err as { message: unknown }).message)
          : 'Forecast failed';
      setError(msg);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="container mx-auto px-4 py-8 space-y-6">
      <header className="space-y-2">
        <h1 className="text-3xl font-bold tracking-tight flex items-center gap-2">
          <Sparkles className="h-6 w-6 text-violet-500" aria-hidden />
          AI Property Valuation & Forecast
        </h1>
        <p className="text-muted-foreground max-w-2xl">
          Estimate the current market value of a property and project its value at
          1, 3, 5, or 10 years. Powered by an LLM that weighs property features and
          local comparables. Not a formal appraisal.
        </p>
      </header>

      <form
        onSubmit={handleSubmit}
        className="rounded-lg border bg-card p-6 space-y-4"
        data-testid="valuation-form"
      >
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="space-y-2">
            <label htmlFor="property_id" className="text-sm font-medium">
              Property ID (optional)
            </label>
            <input
              id="property_id"
              type="text"
              placeholder="e.g. prop-12345"
              className="w-full rounded border px-3 py-2 bg-background"
              value={propertyId}
              onChange={(e) => setPropertyId(e.target.value)}
              disabled={loading}
            />
            <p className="text-xs text-muted-foreground">
              Leave blank to enter features manually below.
            </p>
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">Forecast horizons</label>
            <div className="flex flex-wrap gap-2">
              {HORIZON_OPTIONS.map((opt) => {
                const active = horizons.includes(opt.value);
                return (
                  <button
                    key={opt.value}
                    type="button"
                    aria-pressed={active}
                    onClick={() =>
                      setHorizons((prev) =>
                        active
                          ? prev.filter((h) => h !== opt.value)
                          : [...prev, opt.value].sort((a, b) => a - b)
                      )
                    }
                    disabled={loading}
                    className={[
                      'rounded-full border px-3 py-1 text-xs font-medium transition-colors',
                      active
                        ? 'bg-violet-600 text-white border-violet-600'
                        : 'bg-background text-foreground hover:bg-muted',
                    ].join(' ')}
                  >
                    {opt.label}
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        {useFeatures ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            <Field
              label="City"
              value={form.city}
              onChange={(v) => setForm((f) => ({ ...f, city: v }))}
              disabled={loading}
            />
            <Field
              label="Neighborhood"
              value={form.neighborhood}
              onChange={(v) => setForm((f) => ({ ...f, neighborhood: v }))}
              disabled={loading}
            />
            <Field
              label="Type"
              value={form.property_type}
              onChange={(v) => setForm((f) => ({ ...f, property_type: v }))}
              disabled={loading}
              placeholder="apartment, house…"
            />
            <Field
              label="Area (sqm)"
              value={form.area_sqm}
              onChange={(v) => setForm((f) => ({ ...f, area_sqm: v }))}
              disabled={loading}
              inputMode="decimal"
            />
            <Field
              label="Rooms"
              value={form.rooms}
              onChange={(v) => setForm((f) => ({ ...f, rooms: v }))}
              disabled={loading}
              inputMode="decimal"
            />
            <Field
              label="Year built"
              value={form.year_built}
              onChange={(v) => setForm((f) => ({ ...f, year_built: v }))}
              disabled={loading}
              inputMode="numeric"
            />
            <Field
              label="Asking price"
              value={form.price}
              onChange={(v) => setForm((f) => ({ ...f, price: v }))}
              disabled={loading}
              inputMode="decimal"
            />
            <Field
              label="Currency"
              value={form.currency}
              onChange={(v) => setForm((f) => ({ ...f, currency: v }))}
              disabled={loading}
              placeholder="EUR, USD, GBP…"
            />
          </div>
        ) : null}

        <div className="flex items-center justify-between pt-2">
          <button
            type="submit"
            disabled={loading || !canSubmit}
            data-testid="valuation-submit"
            className="inline-flex items-center gap-2 rounded-md bg-violet-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-violet-700 disabled:opacity-50"
          >
            {loading ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
                Estimating…
              </>
            ) : (
              <>
                <TrendingUp className="h-4 w-4" aria-hidden />
                Get forecast
              </>
            )}
          </button>
          {useFeatures ? (
            <p className="text-xs text-muted-foreground inline-flex items-center gap-1">
              <MapPin className="h-3 w-3" aria-hidden />
              Enter city &amp; area to enable.
            </p>
          ) : null}
        </div>
      </form>

      {error ? (
        <div
          role="alert"
          className="flex items-start gap-2 rounded-md border border-destructive/30 bg-destructive/5 p-4 text-sm text-destructive"
        >
          <AlertTriangle className="h-4 w-4 mt-0.5" aria-hidden />
          <span>{error}</span>
        </div>
      ) : null}

      {result ? <ForecastResultView result={result} /> : null}
    </main>
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
    <div className="space-y-1">
      <label className="text-xs font-medium text-muted-foreground">{label}</label>
      <input
        type="text"
        inputMode={inputMode ?? 'text'}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        disabled={disabled}
        className="w-full rounded border px-2 py-1.5 text-sm bg-background"
      />
    </div>
  );
}

function ForecastResultView({ result }: { result: PriceForecastResponse }) {
  const currency = result.currency || 'EUR';
  const askingPrice = null; // we don't get the asking price back; rely on chart only
  return (
    <section
      data-testid="valuation-result"
      className="rounded-lg border bg-card p-6 space-y-6"
    >
      <div className="flex flex-wrap items-end gap-4">
        <div>
          <div className="text-xs uppercase tracking-wide text-muted-foreground">
            Current estimate
          </div>
          <div
            data-testid="valuation-current"
            className="text-4xl font-bold tracking-tight"
          >
            {fmtCurrency(result.current_estimate, currency)}
          </div>
        </div>
        <div className="ml-auto text-right text-xs text-muted-foreground space-y-1">
          <div>
            Confidence:{' '}
            <span className="font-medium text-foreground">
              {Math.round(result.confidence * 100)}%
            </span>
          </div>
          <div>Comparables used: {result.comparables_used}</div>
          {result.median_price_per_sqm ? (
            <div>City median: {fmtCurrency(result.median_price_per_sqm, currency)} / sqm</div>
          ) : null}
          {result.neighborhood_median_price_per_sqm ? (
            <div>
              Neighborhood median:{' '}
              {fmtCurrency(result.neighborhood_median_price_per_sqm, currency)} / sqm
            </div>
          ) : null}
        </div>
      </div>

      <ForecastChart result={result} />

      {result.drivers && result.drivers.length ? (
        <div>
          <div className="text-xs uppercase tracking-wide text-muted-foreground mb-2">
            Key drivers
          </div>
          <ul className="flex flex-wrap gap-2">
            {result.drivers.map((d: string, i: number) => (
              <li
                key={i}
                className="rounded-full border bg-muted/30 px-3 py-1 text-xs"
              >
                {d}
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {result.explanation ? (
        <div className="rounded-md bg-muted/30 border p-4 text-sm leading-relaxed">
          {result.explanation}
        </div>
      ) : null}

      <p className="text-xs italic text-muted-foreground">{result.disclaimer}</p>

      {askingPrice === null ? null : null}
    </section>
  );
}

/**
 * Inline SVG line + confidence band. Avoids adding a chart-library dep —
 * the public demo must stay small and SSR-friendly.
 */
function ForecastChart({ result }: { result: PriceForecastResponse }) {
  const points = [
    { years_ahead: 0, estimated_value: result.current_estimate },
    ...result.forecast,
  ];
  if (points.length < 2) return null;

  const padding = 40;
  const w = 600;
  const h = 240;
  const xs = points.map((p) => p.years_ahead);
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const allValues = points.flatMap((p) => {
    const f = result.forecast.find((x: ForecastPoint) => x.years_ahead === p.years_ahead);
    return [p.estimated_value, f?.lower_bound ?? p.estimated_value, f?.upper_bound ?? p.estimated_value];
  });
  const minY = Math.min(...allValues) * 0.95;
  const maxY = Math.max(...allValues) * 1.05;

  const x = (yr: number) =>
    padding + ((yr - minX) / Math.max(maxX - minX, 1)) * (w - 2 * padding);
  const y = (val: number) =>
    h - padding - ((val - minY) / Math.max(maxY - minY, 1)) * (h - 2 * padding);

  // Build confidence-band polygon
  const bandPath = (() => {
    const top: string[] = [];
    const bottom: string[] = [];
    result.forecast.forEach((p: ForecastPoint) => {
      top.push(`${x(p.years_ahead)},${y(p.upper_bound)}`);
      bottom.push(`${x(p.years_ahead)},${y(p.lower_bound)}`);
    });
    return `M ${top.join(' L ')} L ${bottom.reverse().join(' L ')} Z`;
  })();

  const linePath = points
    .map((p, i) => `${i === 0 ? 'M' : 'L'} ${x(p.years_ahead)},${y(p.estimated_value)}`)
    .join(' ');

  return (
    <div className="w-full overflow-x-auto">
      <svg
        viewBox={`0 0 ${w} ${h}`}
        className="w-full max-w-3xl mx-auto"
        role="img"
        aria-label="Forecast chart"
      >
        <path d={bandPath} fill="rgb(139 92 246 / 0.15)" />
        <path
          d={linePath}
          fill="none"
          stroke="rgb(139 92 246)"
          strokeWidth={3}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        {points.map((p) => (
          <circle
            key={p.years_ahead}
            cx={x(p.years_ahead)}
            cy={y(p.estimated_value)}
            r={5}
            fill="rgb(139 92 246)"
          >
            <title>
              {p.years_ahead === 0 ? 'Today' : `+${p.years_ahead}y`}:{' '}
              {fmtCurrency(p.estimated_value, result.currency)}
            </title>
          </circle>
        ))}
        {/* X-axis ticks */}
        {points.map((p) => (
          <text
            key={`x-${p.years_ahead}`}
            x={x(p.years_ahead)}
            y={h - 8}
            textAnchor="middle"
            fontSize={11}
            fill="currentColor"
            opacity={0.6}
          >
            {p.years_ahead === 0 ? 'Today' : `+${p.years_ahead}y`}
          </text>
        ))}
      </svg>
    </div>
  );
}