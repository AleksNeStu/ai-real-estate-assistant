'use client';

import React, { useState } from 'react';
import { useTranslations } from 'next-intl';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { analyzePortfolio, ApiError } from '@/lib/api';
import type { PortfolioAnalysisResult, PropertyHolding } from '@/lib/types';
import { extractErrorState, type ErrorState } from '@/lib/error-utils';
import { Loader2, AlertCircle, RefreshCw, PieChart, Plus, Trash2, Building2 } from 'lucide-react';
import { DiversificationChart } from './charts/diversification-chart';
import { RiskGauge } from './charts/risk-gauge';

const PROPERTY_TYPES = ['apartment', 'house', 'condo', 'townhouse', 'multi_family', 'commercial'];

const emptyProperty: Omit<PropertyHolding, 'property_id'> = {
  property_price: 200000,
  monthly_rent: 1800,
  property_type: 'apartment',
  city: 'Berlin',
  monthly_cash_flow: 0,
  cap_rate: 0,
};

export function PortfolioAnalyzer() {
  const t = useTranslations('portfolio');
  const [loading, setLoading] = useState(false);
  const [errorState, setErrorState] = useState<ErrorState | null>(null);
  const [result, setResult] = useState<PortfolioAnalysisResult | null>(null);
  const [properties, setProperties] = useState<
    Array<Omit<PropertyHolding, 'property_id'> & { id: string }>
  >([{ ...emptyProperty, id: '1' }]);

  const addProperty = () => {
    setProperties((prev) => [...prev, { ...emptyProperty, id: Date.now().toString() }]);
  };

  const removeProperty = (id: string) => {
    if (properties.length > 1) {
      setProperties((prev) => prev.filter((p) => p.id !== id));
    }
  };

  const updateProperty = (
    id: string,
    field: keyof Omit<PropertyHolding, 'property_id'>,
    value: string | number
  ) => {
    setProperties((prev) => prev.map((p) => (p.id === id ? { ...p, [field]: value } : p)));
  };

  const handleAnalyze = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setErrorState(null);

    try {
      const holdings: PropertyHolding[] = properties.map((p) => ({
        property_id: p.id,
        property_price: p.property_price,
        monthly_rent: p.monthly_rent,
        property_type: p.property_type,
        city: p.city,
        monthly_cash_flow: p.monthly_cash_flow,
        cap_rate: p.cap_rate,
      }));

      const data = await analyzePortfolio({ properties: holdings });
      setResult(data);
    } catch (err: unknown) {
      setErrorState(extractErrorState(err));
    } finally {
      setLoading(false);
    }
  };

  const handleRetry = async () => {
    if (loading) return;
    setLoading(true);
    setErrorState(null);

    try {
      const holdings: PropertyHolding[] = properties.map((p) => ({
        property_id: p.id,
        property_price: p.property_price,
        monthly_rent: p.monthly_rent,
        property_type: p.property_type,
        city: p.city,
        monthly_cash_flow: p.monthly_cash_flow,
        cap_rate: p.cap_rate,
      }));

      const data = await analyzePortfolio({ properties: holdings });
      setResult(data);
    } catch (err: unknown) {
      setErrorState(extractErrorState(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Empty state hint */}
      {!result && !errorState && !loading && (
        <div
          className="rounded-lg border bg-muted/30 p-4 text-center"
          role="status"
          aria-live="polite"
        >
          <p className="text-sm text-muted-foreground">{t('emptyHint')}</p>
        </div>
      )}

      <div className={result || errorState || loading ? 'grid gap-6 lg:grid-cols-2' : 'grid gap-6'}>
        {/* Property Input Form - centered when no results, left column when results present */}
        <Card className={result || errorState || loading ? undefined : 'mx-auto w-full max-w-2xl'}>
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              <span>{t('addProperty')}</span>
              <Button type="button" variant="outline" size="sm" onClick={addProperty}>
                <Plus className="h-4 w-4 mr-1" aria-hidden="true" />
                {t('addProperty')}
              </Button>
            </CardTitle>
            <CardDescription>{t('emptyHint')}</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleAnalyze} className="space-y-6">
              {properties.map((property, index) => (
                <div key={property.id} className="p-4 border rounded-lg space-y-4">
                  <div className="flex items-center justify-between">
                    <h4 className="text-sm font-semibold flex items-center gap-2">
                      <Building2 className="h-4 w-4" aria-hidden="true" />
                      {t('propertyLabel')} {index + 1}
                    </h4>
                    {properties.length > 1 && (
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        onClick={() => removeProperty(property.id)}
                      >
                        <Trash2 className="h-4 w-4 text-destructive" aria-hidden="true" />
                      </Button>
                    )}
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor={`price-${property.id}`}>{t('propertyPrice')}</Label>
                      <Input
                        id={`price-${property.id}`}
                        type="number"
                        value={property.property_price}
                        onChange={(e) =>
                          updateProperty(
                            property.id,
                            'property_price',
                            parseFloat(e.target.value) || 0
                          )
                        }
                        min="0"
                        step="1000"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor={`rent-${property.id}`}>{t('monthlyRent')}</Label>
                      <Input
                        id={`rent-${property.id}`}
                        type="number"
                        value={property.monthly_rent}
                        onChange={(e) =>
                          updateProperty(
                            property.id,
                            'monthly_rent',
                            parseFloat(e.target.value) || 0
                          )
                        }
                        min="0"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor={`cashflow-${property.id}`}>{t('monthlyCashFlow')}</Label>
                      <Input
                        id={`cashflow-${property.id}`}
                        type="number"
                        value={property.monthly_cash_flow}
                        onChange={(e) =>
                          updateProperty(
                            property.id,
                            'monthly_cash_flow',
                            parseFloat(e.target.value) || 0
                          )
                        }
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor={`caprate-${property.id}`}>{t('capRate')}</Label>
                      <Input
                        id={`caprate-${property.id}`}
                        type="number"
                        value={property.cap_rate}
                        onChange={(e) =>
                          updateProperty(property.id, 'cap_rate', parseFloat(e.target.value) || 0)
                        }
                        min="0"
                        max="30"
                        step="0.1"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor={`city-${property.id}`}>{t('city')}</Label>
                      <Input
                        id={`city-${property.id}`}
                        type="text"
                        value={property.city}
                        onChange={(e) => updateProperty(property.id, 'city', e.target.value)}
                        placeholder={t('cityPlaceholder')}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor={`type-${property.id}`}>{t('propertyType')}</Label>
                      <Select
                        value={property.property_type}
                        onValueChange={(value) =>
                          updateProperty(property.id, 'property_type', value)
                        }
                      >
                        <SelectTrigger id={`type-${property.id}`}>
                          <SelectValue placeholder={t('selectType')} />
                        </SelectTrigger>
                        <SelectContent>
                          {PROPERTY_TYPES.map((type) => (
                            <SelectItem key={type} value={type}>
                              {type.replace('_', ' ').replace(/\b\w/g, (l) => l.toUpperCase())}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                </div>
              ))}

              <Button type="submit" className="w-full" disabled={loading}>
                {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />}
                <PieChart className="mr-2 h-4 w-4" aria-hidden="true" />
                {t('analyzeButton')}
              </Button>

              {/* Error state */}
              {errorState && (
                <div
                  className="flex flex-col items-start gap-3 rounded-lg border border-destructive/20 bg-destructive/10 p-4"
                  role="alert"
                >
                  <div className="flex items-start gap-2">
                    <AlertCircle
                      className="h-4 w-4 text-destructive mt-0.5 shrink-0"
                      aria-hidden="true"
                    />
                    <div className="flex-1">
                      <p className="text-sm text-destructive font-medium">{t('analysisFailed')}</p>
                      <p className="text-sm text-destructive/90 mt-1">{errorState.message}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3 w-full">
                    {errorState.requestId && (
                      <p className="text-xs text-muted-foreground font-mono">
                        request_id={errorState.requestId}
                      </p>
                    )}
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={handleRetry}
                      disabled={loading}
                      className="gap-2 ml-auto"
                    >
                      <RefreshCw className="h-3 w-3" aria-hidden="true" />
                      {t('retry')}
                    </Button>
                  </div>
                </div>
              )}
            </form>
          </CardContent>
        </Card>

        {/* Results */}
        {result && (
          <div className="space-y-6">
            {/* Portfolio Metrics */}
            <Card>
              <CardHeader>
                <CardTitle>{t('results.metricsTitle')}</CardTitle>
                <CardDescription>{t('results.metricsDescription')}</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                  <div className="text-center p-3 bg-muted/50 rounded-lg">
                    <p className="text-sm text-muted-foreground">{t('results.totalProperties')}</p>
                    <p className="text-2xl font-bold">{result.metrics.total_properties}</p>
                  </div>
                  <div className="text-center p-3 bg-muted/50 rounded-lg">
                    <p className="text-sm text-muted-foreground">{t('results.totalValue')}</p>
                    <p className="text-2xl font-bold">
                      ${(result.metrics.total_value / 1000000).toFixed(2)}M
                    </p>
                  </div>
                  <div className="text-center p-3 bg-muted/50 rounded-lg">
                    <p className="text-sm text-muted-foreground">{t('results.annualCashFlow')}</p>
                    <p
                      className={`text-2xl font-bold ${result.metrics.total_annual_cash_flow >= 0 ? 'text-green-600' : 'text-red-600'}`}
                    >
                      $
                      {result.metrics.total_annual_cash_flow.toLocaleString(undefined, {
                        maximumFractionDigits: 0,
                      })}
                    </p>
                  </div>
                  <div className="text-center p-3 bg-muted/50 rounded-lg">
                    <p className="text-sm text-muted-foreground">{t('results.avgCapRate')}</p>
                    <p className="text-2xl font-bold">
                      {result.metrics.weighted_avg_cap_rate.toFixed(2)}%
                    </p>
                  </div>
                  <div className="text-center p-3 bg-muted/50 rounded-lg">
                    <p className="text-sm text-muted-foreground">{t('results.avgYield')}</p>
                    <p className="text-2xl font-bold">
                      {result.metrics.weighted_avg_yield.toFixed(2)}%
                    </p>
                  </div>
                  <div className="text-center p-3 bg-muted/50 rounded-lg">
                    <p className="text-sm text-muted-foreground">{t('results.cashOnCash')}</p>
                    <p className="text-2xl font-bold">
                      {result.performance.cash_on_cash_return.toFixed(2)}%
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Diversification */}
            <DiversificationChart diversification={result.diversification} />

            {/* Risk Assessment */}
            <RiskGauge
              score={result.risk_assessment.overall_risk_score}
              recommendations={result.risk_assessment.recommendations}
            />
          </div>
        )}
      </div>
    </div>
  );
}
