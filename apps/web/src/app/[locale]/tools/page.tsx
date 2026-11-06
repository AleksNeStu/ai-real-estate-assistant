"use client";
import React, { useEffect, useMemo, useState } from "react";
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
} from "@/lib/api";
import type { PromptTemplateInfo, NeighborhoodQualityResult } from "@/lib/types";

export default function ToolsPage() {
  return (
    <div className="container mx-auto px-4 py-8 space-y-8">
      <h1 className="text-2xl font-semibold">Tools</h1>
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
  const [propertyPrice, setPropertyPrice] = useState<string>("");
  const [downPaymentPercent, setDownPaymentPercent] = useState<string>("20");
  const [interestRate, setInterestRate] = useState<string>("6.5");
  const [loanYears, setLoanYears] = useState<string>("30");
  const [result, setResult] = useState<null | { monthly_payment: number }>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const hint = error ? getToolHint(error) : null;
  return (
    <section>
      <h2 className="text-xl font-medium">Mortgage Calculator</h2>
      <div className="grid grid-cols-2 gap-2 my-2">
        <input
          className="border p-2"
          placeholder="Property price"
          value={propertyPrice}
          onChange={(e) => setPropertyPrice(e.target.value)}
        />
        <input
          className="border p-2"
          placeholder="Down payment %"
          value={downPaymentPercent}
          onChange={(e) => setDownPaymentPercent(e.target.value)}
        />
        <input
          className="border p-2"
          placeholder="Interest rate %"
          value={interestRate}
          onChange={(e) => setInterestRate(e.target.value)}
        />
        <input
          className="border p-2"
          placeholder="Loan years"
          value={loanYears}
          onChange={(e) => setLoanYears(e.target.value)}
        />
      </div>
      <button
        className="bg-black text-white px-3 py-2 rounded"
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
            setError(msg || "Calculation failed");
          } finally {
            setLoading(false);
          }
        }}
      >
        {loading ? "Calculating..." : "Calculate"}
      </button>
      {error && <p className="text-red-600 mt-2">{error}</p>}
      {hint && <p className="text-sm text-gray-600 mt-1">{hint}</p>}
      {result && <p className="mt-2">Monthly payment: {result.monthly_payment.toFixed(2)}</p>}
    </section>
  );
}

function CompareSection() {
  const [ids, setIds] = useState<string>("");
  const [data, setData] = useState<Awaited<ReturnType<typeof comparePropertiesApi>> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [exportFormat, setExportFormat] = useState<string>("csv");
  const [exportColumns, setExportColumns] = useState<string>("");
  const [exportIncludeHeader, setExportIncludeHeader] = useState<boolean>(true);
  const [csvDelimiter, setCsvDelimiter] = useState<string>(",");
  const [csvDecimal, setCsvDecimal] = useState<string>(".");
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);
  const hint = error ? getToolHint(error) : null;
  return (
    <section>
      <h2 className="text-xl font-medium">Compare Properties</h2>
      <input
        className="border p-2 w-full my-2"
        placeholder="IDs comma-separated"
        value={ids}
        onChange={(e) => setIds(e.target.value)}
      />
      <div className="flex flex-wrap gap-2">
        <button
          className="bg-black text-white px-3 py-2 rounded"
          onClick={async () => {
            setError(null);
            setLoading(true);
            try {
              const res = await comparePropertiesApi(ids.split(",").map((p) => p.trim()).filter(Boolean));
              setData(res);
            } catch (e: unknown) {
              const msg = e instanceof Error ? e.message : String(e);
              setError(msg || "Compare failed");
            } finally {
              setLoading(false);
            }
          }}
        >
          {loading ? "Comparing..." : "Compare"}
        </button>
        <select
          className="border p-2 rounded"
          value={exportFormat}
          onChange={(e) => setExportFormat(e.target.value)}
          aria-label="Export format"
        >
          <option value="csv">CSV</option>
          <option value="xlsx">Excel</option>
          <option value="json">JSON</option>
          <option value="md">Markdown</option>
          <option value="pdf">PDF</option>
        </select>
        <button
          className="bg-black text-white px-3 py-2 rounded"
          disabled={exporting}
          onClick={async () => {
            setExportError(null);
            setExporting(true);
            try {
              const propertyIds = ids.split(",").map((p) => p.trim()).filter(Boolean);
              if (!propertyIds.length) {
                setExportError("Please provide at least one property ID.");
                return;
              }
              const columns = exportColumns
                .split(",")
                .map((c) => c.trim())
                .filter(Boolean);
              const { filename, blob } = await exportPropertiesByIds(
                propertyIds,
                exportFormat as "csv" | "xlsx" | "json" | "md" | "pdf",
                {
                  columns: columns.length ? columns : undefined,
                  include_header: exportIncludeHeader,
                  csv_delimiter: exportFormat === "csv" ? csvDelimiter : undefined,
                  csv_decimal: exportFormat === "csv" ? csvDecimal : undefined,
                }
              );
              const url = window.URL.createObjectURL(blob);
              const a = document.createElement("a");
              a.href = url;
              a.download = filename;
              document.body.appendChild(a);
              a.click();
              a.remove();
              window.URL.revokeObjectURL(url);
            } catch (e: unknown) {
              const msg = e instanceof Error ? e.message : String(e);
              setExportError(msg || "Export failed");
            } finally {
              setExporting(false);
            }
          }}
        >
          {exporting ? "Exporting..." : "Export"}
        </button>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-2 my-2">
        <input
          className="border p-2 w-full"
          placeholder="Columns (optional), e.g., id, city, price"
          value={exportColumns}
          onChange={(e) => setExportColumns(e.target.value)}
          aria-label="Export columns"
        />
        {exportFormat === "csv" ? (
          <div className="grid grid-cols-2 gap-2">
            <select
              className="border p-2 rounded"
              value={csvDelimiter}
              onChange={(e) => setCsvDelimiter(e.target.value)}
              aria-label="CSV delimiter"
            >
              <option value=",">Comma (,)</option>
              <option value=";">Semicolon (;)</option>
            </select>
            <select
              className="border p-2 rounded"
              value={csvDecimal}
              onChange={(e) => setCsvDecimal(e.target.value)}
              aria-label="CSV decimal separator"
            >
              <option value=".">Dot (.)</option>
              <option value=",">Comma (,)</option>
            </select>
            <label className="flex items-center gap-2 text-sm col-span-2">
              <input
                type="checkbox"
                checked={exportIncludeHeader}
                onChange={(e) => setExportIncludeHeader(e.target.checked)}
                aria-label="Include CSV header"
              />
              Include header row
            </label>
          </div>
        ) : null}
      </div>
      {error && <p className="text-red-600 mt-2">{error}</p>}
      {hint && <p className="text-sm text-gray-600 mt-1">{hint}</p>}
      {exportError && <p className="text-red-600 mt-2">{exportError}</p>}
      {data && (
        <div className="mt-2">
          <p>Count: {data.summary?.count}</p>
          <p>Min price: {data.summary?.min_price ?? "-"}</p>
          <p>Max price: {data.summary?.max_price ?? "-"}</p>
          <p>Diff: {data.summary?.price_difference ?? "-"}</p>
        </div>
      )}
    </section>
  );
}

function PriceAnalysisSection() {
  const [query, setQuery] = useState<string>("");
  const [data, setData] = useState<Awaited<ReturnType<typeof priceAnalysisApi>> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const hint = error ? getToolHint(error) : null;
  return (
    <section>
      <h2 className="text-xl font-medium">Price Analysis</h2>
      <input
        className="border p-2 w-full my-2"
        placeholder="Query (e.g., city or type)"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
      />
      <button
        className="bg-black text-white px-3 py-2 rounded"
        onClick={async () => {
          setError(null);
          setLoading(true);
          try {
            const res = await priceAnalysisApi(query);
            setData(res);
          } catch (e: unknown) {
            const msg = e instanceof Error ? e.message : String(e);
            setError(msg || "Analysis failed");
          } finally {
            setLoading(false);
          }
        }}
      >
        {loading ? "Analyzing..." : "Analyze"}
      </button>
      {error && <p className="text-red-600 mt-2">{error}</p>}
      {hint && <p className="text-sm text-gray-600 mt-1">{hint}</p>}
      {data && (
        <div className="mt-2">
          <p>Count: {data.count}</p>
          <p>Average price: {data.average_price ?? "-"}</p>
          <p>Median price: {data.median_price ?? "-"}</p>
        </div>
      )}
    </section>
  );
}

function LocationAnalysisSection() {
  const [pid, setPid] = useState<string>("");
  const [data, setData] = useState<Awaited<ReturnType<typeof locationAnalysisApi>> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const hint = error ? getToolHint(error) : null;
  return (
    <section>
      <h2 className="text-xl font-medium">Location Analysis</h2>
      <input
        className="border p-2 w-full my-2"
        placeholder="Property ID"
        value={pid}
        onChange={(e) => setPid(e.target.value)}
      />
      <button
        className="bg-black text-white px-3 py-2 rounded"
        onClick={async () => {
          setError(null);
          setLoading(true);
          try {
            const res = await locationAnalysisApi(pid);
            setData(res);
          } catch (e: unknown) {
            const msg = e instanceof Error ? e.message : String(e);
            setError(msg || "Location analysis failed");
          } finally {
            setLoading(false);
          }
        }}
      >
        {loading ? "Analyzing..." : "Analyze"}
      </button>
      {error && <p className="text-red-600 mt-2">{error}</p>}
      {hint && <p className="text-sm text-gray-600 mt-1">{hint}</p>}
      {data && (
        <div className="mt-2">
          <p>City: {data.city ?? "-"}</p>
          <p>Neighborhood: {data.neighborhood ?? "-"}</p>
          <p>Lat/Lon: {data.lat ?? "-"}, {data.lon ?? "-"}</p>
        </div>
      )}
    </section>
  );
}

function NeighborhoodQualitySection() {
  const [propertyId, setPropertyId] = useState<string>("");
  const [lat, setLat] = useState<string>("");
  const [lon, setLon] = useState<string>("");
  const [city, setCity] = useState<string>("");
  const [neighborhood, setNeighborhood] = useState<string>("");
  const [data, setData] = useState<NeighborhoodQualityResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const hint = error ? getToolHint(error) : null;

  const getScoreColor = (score: number): string => {
    if (score >= 85) return "text-green-600";
    if (score >= 70) return "text-lime-600";
    if (score >= 55) return "text-yellow-600";
    if (score >= 40) return "text-orange-600";
    return "text-red-600";
  };

  const getRatingLabel = (score: number): string => {
    if (score >= 85) return "Excellent";
    if (score >= 70) return "Good";
    if (score >= 55) return "Fair";
    if (score >= 40) return "Poor";
    return "Very Poor";
  };

  return (
    <section>
      <h2 className="text-xl font-medium">Neighborhood Quality Index</h2>
      <div className="grid grid-cols-2 gap-2 my-2">
        <input
          className="border p-2"
          placeholder="Property ID"
          value={propertyId}
          onChange={(e) => setPropertyId(e.target.value)}
        />
        <input
          className="border p-2"
          placeholder="Latitude (optional)"
          value={lat}
          onChange={(e) => setLat(e.target.value)}
        />
        <input
          className="border p-2"
          placeholder="Longitude (optional)"
          value={lon}
          onChange={(e) => setLon(e.target.value)}
        />
        <input
          className="border p-2"
          placeholder="City (optional)"
          value={city}
          onChange={(e) => setCity(e.target.value)}
        />
        <input
          className="border p-2 col-span-2"
          placeholder="Neighborhood (optional)"
          value={neighborhood}
          onChange={(e) => setNeighborhood(e.target.value)}
        />
      </div>
      <button
        className="bg-black text-white px-3 py-2 rounded"
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
            setError(msg || "Neighborhood quality analysis failed");
          } finally {
            setLoading(false);
          }
        }}
      >
        {loading ? "Analyzing..." : "Analyze"}
      </button>
      {error && <p className="text-red-600 mt-2">{error}</p>}
      {hint && <p className="text-sm text-gray-600 mt-1">{hint}</p>}
      {data && (
        <div className="mt-4 space-y-3">
          <div className="flex items-center gap-4">
            <h3 className="text-lg font-semibold">
              Overall Score: <span className={`${getScoreColor(data.overall_score)} text-2xl`}>{data.overall_score.toFixed(1)}</span>/100
            </h3>
            <span className={`px-2 py-1 rounded text-sm ${getScoreColor(data.overall_score)} bg-gray-100`}>
              {getRatingLabel(data.overall_score)}
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
            <ScoreBar label="Safety" score={data.safety_score} weight="25%" />
            <ScoreBar label="Schools" score={data.schools_score} weight="20%" />
            <ScoreBar label="Amenities" score={data.amenities_score} weight="20%" />
            <ScoreBar label="Walkability" score={data.walkability_score} weight="20%" />
            <ScoreBar label="Green Space" score={data.green_space_score} weight="15%" />
          </div>

          <div className="mt-4 p-3 bg-gray-50 rounded text-sm">
            <p className="font-semibold">Location:</p>
            <p>City: {data.city || "-"}</p>
            <p>Neighborhood: {data.neighborhood || "-"}</p>
            <p>Coordinates: {data.latitude?.toFixed(4) || "-"}, {data.longitude?.toFixed(4) || "-"}</p>
            <p className="mt-2 text-gray-600">Data Sources: {data.data_sources.join(", ")}</p>
          </div>
        </div>
      )}
    </section>
  );
}

function ScoreBar({ label, score, weight }: { label: string; score: number; weight: string }) {
  const getScoreColor = (score: number): string => {
    if (score >= 85) return "bg-green-500";
    if (score >= 70) return "bg-lime-500";
    if (score >= 55) return "bg-yellow-500";
    if (score >= 40) return "bg-orange-500";
    return "bg-red-500";
  };

  return (
    <div>
      <div className="flex justify-between mb-1">
        <span className="text-sm font-medium">{label}</span>
        <span className="text-sm text-gray-600">{score.toFixed(1)}/100 (Weight: {weight})</span>
      </div>
      <div className="w-full bg-gray-200 rounded-full h-2.5">
        <div
          className={`h-2.5 rounded-full ${getScoreColor(score)}`}
          style={{ width: `${score}%` }}
        ></div>
      </div>
    </div>
  );
}

function PromptTemplatesSection() {
  const [templates, setTemplates] = useState<PromptTemplateInfo[]>([]);
  const [selectedId, setSelectedId] = useState<string>("");
  const [variables, setVariables] = useState<Record<string, string>>({});
  const [result, setResult] = useState<string>("");
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
        setError(msg || "Failed to load templates");
      }
    })();
    return () => {
      mounted = false;
    };
  }, []);

  const selected = useMemo(
    () => templates.find((t) => t.id === selectedId) || null,
    [templates, selectedId]
  );

  useEffect(() => {
    if (!selected) return;
    setVariables((prev) => {
      const next: Record<string, string> = {};
      for (const v of selected.variables) {
        next[v.name] = prev[v.name] ?? "";
      }
      return next;
    });
    setResult("");
    setError(null);
  }, [selected]);

  return (
    <section>
      <h2 className="text-xl font-medium">Prompt Templates</h2>
      <p className="text-sm text-gray-600 mt-1">
        Pick a template, fill variables, and generate ready-to-use text.
      </p>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-2 my-2">
        <select
          className="border p-2 rounded"
          value={selectedId}
          onChange={(e) => setSelectedId(e.target.value)}
          aria-label="Template picker"
        >
          {templates.map((t) => (
            <option key={t.id} value={t.id}>
              {t.title}
            </option>
          ))}
        </select>
        {selected ? (
          <div className="text-sm text-gray-600 flex items-center">
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
                {v.required ? " *" : ""}
              </label>
              <input
                className="border p-2"
                placeholder={v.example ? String(v.example) : v.description}
                value={variables[v.name] ?? ""}
                onChange={(e) =>
                  setVariables((prev) => ({
                    ...prev,
                    [v.name]: e.target.value,
                  }))
                }
                aria-label={`Variable ${v.name}`}
              />
              <span className="text-xs text-gray-500">{v.description}</span>
            </div>
          ))}
        </div>
      ) : null}

      <div className="flex flex-wrap gap-2 items-center">
        <button
          className="bg-black text-white px-3 py-2 rounded"
          disabled={!selected || loading}
          onClick={async () => {
            if (!selected) return;
            setError(null);
            setLoading(true);
            try {
              const vars: Record<string, string> = {};
              for (const v of selected.variables) {
                const raw = variables[v.name] ?? "";
                if (raw.trim()) vars[v.name] = raw.trim();
              }
              const res = await applyPromptTemplate(selected.id, vars);
              setResult(res.rendered_text);
            } catch (e: unknown) {
              const msg = e instanceof Error ? e.message : String(e);
              setError(msg || "Template render failed");
              setResult("");
            } finally {
              setLoading(false);
            }
          }}
        >
          {loading ? "Generating..." : "Generate"}
        </button>
        <button
          className="border px-3 py-2 rounded"
          disabled={!result}
          onClick={async () => {
            if (!result) return;
            try {
              await navigator.clipboard.writeText(result);
            } catch {}
          }}
        >
          Copy
        </button>
      </div>
      {error && <p className="text-red-600 mt-2">{error}</p>}
      {result ? (
        <textarea
          className="border p-2 w-full mt-2"
          rows={10}
          value={result}
          onChange={(e) => setResult(e.target.value)}
          aria-label="Rendered template output"
        />
      ) : null}
    </section>
  );
}

function ValuationSection() {
  const [pid, setPid] = useState<string>("");
  const [value, setValue] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const hint = error ? getToolHint(error) : null;
  return (
    <section>
      <h2 className="text-xl font-medium">Valuation (CE Stub)</h2>
      <input
        className="border p-2 w-full my-2"
        placeholder="Property ID"
        value={pid}
        onChange={(e) => setPid(e.target.value)}
      />
      <button
        className="bg-black text-white px-3 py-2 rounded"
        onClick={async () => {
          setError(null);
          setLoading(true);
          try {
            const res = await valuationApi(pid);
            setValue(res.estimated_value);
          } catch (e: unknown) {
            const msg = e instanceof Error ? e.message : String(e);
            setError(msg || "Valuation failed");
          } finally {
            setLoading(false);
          }
        }}
      >
        {loading ? "Estimating..." : "Estimate"}
      </button>
      {error && <p className="text-red-600 mt-2">{error}</p>}
      {hint && <p className="text-sm text-gray-600 mt-1">{hint}</p>}
      {value !== null && <p className="mt-2">Estimated value: {value.toFixed(2)}</p>}
    </section>
  );
}

function LegalCheckSection() {
  const [text, setText] = useState<string>("");
  const [data, setData] = useState<Awaited<ReturnType<typeof legalCheckApi>> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const hint = error ? getToolHint(error) : null;
  return (
    <section>
      <h2 className="text-xl font-medium">Legal Check (CE Stub)</h2>
      <textarea
        className="border p-2 w-full my-2"
        placeholder="Contract text"
        rows={4}
        value={text}
        onChange={(e) => setText(e.target.value)}
      />
      <button
        className="bg-black text-white px-3 py-2 rounded"
        onClick={async () => {
          setError(null);
          setLoading(true);
          try {
            const res = await legalCheckApi(text);
            setData(res);
          } catch (e: unknown) {
            const msg = e instanceof Error ? e.message : String(e);
            setError(msg || "Legal check failed");
          } finally {
            setLoading(false);
          }
        }}
      >
        {loading ? "Analyzing..." : "Analyze"}
      </button>
      {error && <p className="text-red-600 mt-2">{error}</p>}
      {hint && <p className="text-sm text-gray-600 mt-1">{hint}</p>}
      {data && (
        <div className="mt-2">
          <p>Score: {data.score}</p>
          <p>Risks: {Array.isArray(data.risks) ? data.risks.length : 0}</p>
        </div>
      )}
    </section>
  );
}

function EnrichAddressSection() {
  const [address, setAddress] = useState<string>("");
  const [data, setData] = useState<Awaited<ReturnType<typeof enrichAddressApi>> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const hint = error ? getToolHint(error) : null;
  return (
    <section>
      <h2 className="text-xl font-medium">Data Enrichment (CE Stub)</h2>
      <input
        className="border p-2 w-full my-2"
        placeholder="Address"
        value={address}
        onChange={(e) => setAddress(e.target.value)}
      />
      <button
        className="bg-black text-white px-3 py-2 rounded"
        onClick={async () => {
          setError(null);
          setLoading(true);
          try {
            const res = await enrichAddressApi(address);
            setData(res);
          } catch (e: unknown) {
            const msg = e instanceof Error ? e.message : String(e);
            setError(msg || "Enrichment failed");
          } finally {
            setLoading(false);
          }
        }}
      >
        {loading ? "Enriching..." : "Enrich"}
      </button>
      {error && <p className="text-red-600 mt-2">{error}</p>}
      {hint && <p className="text-sm text-gray-600 mt-1">{hint}</p>}
      {data && (
        <div className="mt-2">
          <p>Address: {data.address}</p>
          <pre className="bg-gray-100 p-2 rounded text-sm">{JSON.stringify(data.data, null, 2)}</pre>
        </div>
      )}
    </section>
  );
}

function CrmSyncSection() {
  const [name, setName] = useState<string>("");
  const [phone, setPhone] = useState<string>("");
  const [email, setEmail] = useState<string>("");
  const [id, setId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const hint = error ? getToolHint(error) : null;
  return (
    <section>
      <h2 className="text-xl font-medium">CRM Sync Contact (CE Stub)</h2>
      <div className="grid grid-cols-3 gap-2 my-2">
        <input
          className="border p-2"
          placeholder="Name"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
        <input
          className="border p-2"
          placeholder="Phone"
          value={phone}
          onChange={(e) => setPhone(e.target.value)}
        />
        <input
          className="border p-2"
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
      </div>
      <button
        className="bg-black text-white px-3 py-2 rounded"
        onClick={async () => {
          setError(null);
          setLoading(true);
          try {
            const res = await crmSyncContactApi(name, phone || undefined, email || undefined);
            setId(res.id);
          } catch (e: unknown) {
            const msg = e instanceof Error ? e.message : String(e);
            setError(msg || "CRM sync failed");
          } finally {
            setLoading(false);
          }
        }}
      >
        {loading ? "Syncing..." : "Sync"}
      </button>
      {error && <p className="text-red-600 mt-2">{error}</p>}
      {hint && <p className="text-sm text-gray-600 mt-1">{hint}</p>}
      {id && <p className="mt-2">Contact ID: {id}</p>}
    </section>
  );
}

function getToolHint(error: string): string | null {
  if (error.includes("Data enrichment disabled")) {
    return "Enable on the backend: set DATA_ENRICHMENT_ENABLED=true and restart the API.";
  }
  if (error.includes("CRM connector not configured")) {
    return "Configure on the backend: set CRM_WEBHOOK_URL and restart the API.";
  }
  if (error.includes("Valuation disabled")) {
    return "Configure on the backend: set VALUATION_MODE=simple and restart the API.";
  }
  if (error.includes("Legal check disabled")) {
    return "Configure on the backend: set LEGAL_CHECK_MODE=basic and restart the API.";
  }
  if (error.includes("Vector store unavailable")) {
    return "Load/initialize the vector store (Chroma) before running this tool.";
  }
  return null;
}
