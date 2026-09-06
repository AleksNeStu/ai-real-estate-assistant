'use client';

import React, { useState } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { calculateRentVsBuy } from '@/lib/api';
import { RentVsBuyResult } from '@/lib/types';
import { Loader2, AlertCircle, RefreshCw, ChevronDown, ChevronUp } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { extractErrorState, type ErrorState } from '@/lib/error-utils';

const formatCurrency = (value: number): string => {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
  }).format(value);
};

const formatCurrencyDetailed = (value: number): string => {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 2,
  }).format(value);
};

const getRecommendationColor = (rec: string): string => {
  if (rec === 'buy') return 'text-green-600';
  if (rec === 'rent') return 'text-blue-600';
  return 'text-yellow-600';
};

const getRecommendationLabel = (rec: string, t: (key: string) => string): string => {
  if (rec === 'buy') return t('results.buyingRecommended');
  if (rec === 'rent') return t('results.rentingRecommended');
  return t('results.dependsTimeline');
};

export function RentVsBuyCalculator() {
  const t = useTranslations('rentVsBuy');
  const [loading, setLoading] = useState(false);
  const [errorState, setErrorState] = useState<ErrorState | null>(null);
  const [result, setResult] = useState<RentVsBuyResult | null>(null);
  const [lastFormData, setLastFormData] = useState<typeof formData | null>(null);
  const [showAdvancedOptions, setShowAdvancedOptions] = useState(false);

  const [formData, setFormData] = useState<{
    property_price: number;
    monthly_rent: number;
    down_payment_percent: number;
    interest_rate: number;
    loan_years: number;
    annual_property_tax: number;
    annual_insurance: number;
    monthly_hoa: number;
    maintenance_percent: number;
    appreciation_rate: number;
    rent_increase_rate: number;
    investment_return_rate: number;
    marginal_tax_rate: number;
    projection_years: number;
  }>({
    property_price: 500000,
    monthly_rent: 2000,
    down_payment_percent: 20,
    interest_rate: 6.5,
    loan_years: 30,
    annual_property_tax: 6000,
    annual_insurance: 1200,
    monthly_hoa: 0,
    maintenance_percent: 1,
    appreciation_rate: 3,
    rent_increase_rate: 2.5,
    investment_return_rate: 7,
    marginal_tax_rate: 24,
    projection_years: 30,
  });

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: parseFloat(value) || 0,
    }));
  };

  const handleCalculate = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setErrorState(null);
    setLastFormData(formData);

    try {
      const data = await calculateRentVsBuy(formData);
      setResult(data);
    } catch (err: unknown) {
      setErrorState(extractErrorState(err));
    } finally {
      setLoading(false);
    }
  };

  const handleRetry = async () => {
    if (!lastFormData || loading) return;
    setLoading(true);
    setErrorState(null);

    try {
      const data = await calculateRentVsBuy(lastFormData);
      setResult(data);
    } catch (err: unknown) {
      setErrorState(extractErrorState(err));
    } finally {
      setLoading(false);
    }
  };

  // Prepare chart data
  const chartData = result?.yearly_breakdown.map((item) => ({
    year: item.year,
    'Cumulative Rent': item.cumulative_rent,
    'Cumulative Ownership': item.cumulative_ownership_cost,
    'Property Value': item.property_value,
    Equity: item.equity,
    'Net Benefit': item.net_benefit,
  }));

  return (
    <div className={result || errorState || loading ? 'grid gap-6 lg:grid-cols-2' : 'grid gap-6'}>
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

      {/* Calculator Form - centered when no results, left column when results present */}
      <Card className={result || errorState || loading ? undefined : 'mx-auto w-full max-w-2xl'}>
        <CardHeader>
          <CardTitle>{t('title')}</CardTitle>
          <CardDescription>{t('description')}</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleCalculate} className="space-y-4">
            {/* Basic Inputs */}
            <div className="space-y-3">
              <h4 className="text-sm font-semibold">{t('form.propertyRent')}</h4>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="property_price">{t('form.propertyPrice')}</Label>
                  <Input
                    id="property_price"
                    name="property_price"
                    type="number"
                    value={formData.property_price}
                    onChange={handleChange}
                    min="0"
                    step="10000"
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="monthly_rent">{t('form.monthlyRent')}</Label>
                  <Input
                    id="monthly_rent"
                    name="monthly_rent"
                    type="number"
                    value={formData.monthly_rent}
                    onChange={handleChange}
                    min="0"
                    step="50"
                    required
                  />
                </div>
              </div>
            </div>

            {/* Advanced Options Toggle */}
            <Button
              type="button"
              variant="outline"
              className="w-full"
              onClick={() => setShowAdvancedOptions(!showAdvancedOptions)}
              aria-expanded={showAdvancedOptions}
            >
              {showAdvancedOptions ? (
                <>
                  <ChevronUp className="mr-2 h-4 w-4" aria-hidden="true" />
                  {t('form.hideAdvanced')}
                </>
              ) : (
                <>
                  <ChevronDown className="mr-2 h-4 w-4" aria-hidden="true" />
                  {t('form.showAdvanced')}
                </>
              )}
            </Button>

            {/* Advanced Options */}
            {showAdvancedOptions && (
              <div className="space-y-4 pt-4 border-t">
                <h4 className="text-sm font-semibold">{t('form.mortgageDetails')}</h4>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="down_payment_percent">{t('form.downPayment')}</Label>
                    <Input
                      id="down_payment_percent"
                      name="down_payment_percent"
                      type="number"
                      value={formData.down_payment_percent}
                      onChange={handleChange}
                      min="0"
                      max="100"
                      step="1"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="interest_rate">{t('form.interestRate')}</Label>
                    <Input
                      id="interest_rate"
                      name="interest_rate"
                      type="number"
                      value={formData.interest_rate}
                      onChange={handleChange}
                      min="0"
                      step="0.1"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="loan_years">{t('form.loanTerm')}</Label>
                    <Input
                      id="loan_years"
                      name="loan_years"
                      type="number"
                      value={formData.loan_years}
                      onChange={handleChange}
                      min="1"
                      max="50"
                    />
                  </div>
                </div>

                <h4 className="text-sm font-semibold">{t('form.ownershipCosts')}</h4>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="annual_property_tax">{t('form.annualPropertyTax')}</Label>
                    <Input
                      id="annual_property_tax"
                      name="annual_property_tax"
                      type="number"
                      value={formData.annual_property_tax}
                      onChange={handleChange}
                      min="0"
                      step="100"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="annual_insurance">{t('form.annualInsurance')}</Label>
                    <Input
                      id="annual_insurance"
                      name="annual_insurance"
                      type="number"
                      value={formData.annual_insurance}
                      onChange={handleChange}
                      min="0"
                      step="100"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="monthly_hoa">{t('form.monthlyHoa')}</Label>
                    <Input
                      id="monthly_hoa"
                      name="monthly_hoa"
                      type="number"
                      value={formData.monthly_hoa}
                      onChange={handleChange}
                      min="0"
                      step="10"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="maintenance_percent">{t('form.maintenancePercent')}</Label>
                    <Input
                      id="maintenance_percent"
                      name="maintenance_percent"
                      type="number"
                      value={formData.maintenance_percent}
                      onChange={handleChange}
                      min="0"
                      max="5"
                      step="0.1"
                    />
                  </div>
                </div>

                <h4 className="text-sm font-semibold">Growth Rates</h4>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="appreciation_rate">{t('form.appreciationRate')}</Label>
                    <Input
                      id="appreciation_rate"
                      name="appreciation_rate"
                      type="number"
                      value={formData.appreciation_rate}
                      onChange={handleChange}
                      min="-10"
                      max="20"
                      step="0.5"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="rent_increase_rate">{t('form.rentIncreaseRate')}</Label>
                    <Input
                      id="rent_increase_rate"
                      name="rent_increase_rate"
                      type="number"
                      value={formData.rent_increase_rate}
                      onChange={handleChange}
                      min="0"
                      max="15"
                      step="0.5"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="investment_return_rate">{t('form.investmentReturnRate')}</Label>
                    <Input
                      id="investment_return_rate"
                      name="investment_return_rate"
                      type="number"
                      value={formData.investment_return_rate}
                      onChange={handleChange}
                      min="0"
                      max="20"
                      step="0.5"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="marginal_tax_rate">{t('form.marginalTaxRate')}</Label>
                    <Input
                      id="marginal_tax_rate"
                      name="marginal_tax_rate"
                      type="number"
                      value={formData.marginal_tax_rate}
                      onChange={handleChange}
                      min="0"
                      max="50"
                      step="1"
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="projection_years">{t('form.projectionYears')}</Label>
                  <Input
                    id="projection_years"
                    name="projection_years"
                    type="number"
                    value={formData.projection_years}
                    onChange={handleChange}
                    min="1"
                    max="50"
                  />
                </div>
              </div>
            )}

            <Button type="submit" className="w-full" disabled={loading}>
              {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />}
              {t('analyzeButton')}
            </Button>

            {/* Error state */}
            {errorState && (
              <div
                className="flex flex-col items-start gap-3 rounded-lg border border-destructive/20 bg-destructive/10 p-4"
                role="alert"
                aria-live="assertive"
              >
                <div className="flex items-start gap-2">
                  <AlertCircle
                    className="h-4 w-4 text-destructive mt-0.5 shrink-0"
                    aria-hidden="true"
                  />
                  <div className="flex-1">
                    <p className="text-sm text-destructive font-medium">{t('error.title')}</p>
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
                    {t('error.retry')}
                  </Button>
                </div>
              </div>
            )}
          </form>
        </CardContent>
      </Card>

      {/* Results Card */}
      {result && (
        <Card className="lg:row-span-2">
          <CardHeader>
            <CardTitle>{t('results.title')}</CardTitle>
            <CardDescription>
              {t('results.description', { years: result.yearly_breakdown.length })}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Recommendation Banner */}
            <div className="bg-primary/5 rounded-lg p-4 text-center">
              <p className="text-sm text-muted-foreground mb-1">{t('results.recommendation')}</p>
              <p className={`text-2xl font-bold ${getRecommendationColor(result.recommendation)}`}>
                {getRecommendationLabel(result.recommendation, t)}
              </p>
              {result.break_even_years && (
                <p className="text-sm text-muted-foreground mt-2">
                  {t('results.breakEvenAt', { years: result.break_even_years.toFixed(1) })}
                </p>
              )}
            </div>

            {/* Key Metrics */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-sm text-muted-foreground">{t('results.monthlyMortgage')}</p>
                <p className="text-xl font-bold">
                  {formatCurrencyDetailed(result.monthly_mortgage)}
                </p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">{t('results.monthlyRentInitial')}</p>
                <p className="text-xl font-bold">
                  {formatCurrencyDetailed(result.monthly_rent_initial)}
                </p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">{t('results.totalRentPaid')}</p>
                <p className="text-xl font-bold text-blue-600">
                  {formatCurrency(result.total_rent_paid)}
                </p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">{t('results.totalOwnershipCost')}</p>
                <p className="text-xl font-bold text-green-600">
                  {formatCurrency(result.total_ownership_cost)}
                </p>
              </div>
            </div>

            {/* Net Advantage */}
            <div className="border-t pt-4">
              <div className="flex justify-between items-center">
                <div>
                  <p className="text-sm text-muted-foreground">{t('results.netBuyingAdvantage')}</p>
                  <p
                    className={`text-xl font-bold ${result.net_buying_advantage >= 0 ? 'text-green-600' : 'text-red-600'}`}
                  >
                    {formatCurrency(result.net_buying_advantage)}
                  </p>
                </div>
                <div className="text-right">
                  <p className="text-sm text-muted-foreground">{t('results.equityBuilt')}</p>
                  <p className="text-xl font-bold">{formatCurrency(result.total_equity_built)}</p>
                </div>
              </div>
              <p className="text-xs text-muted-foreground mt-2">
                {t('results.advantageExplanation')}
              </p>
            </div>

            {/* Cumulative Cost Chart */}
            <div className="border-t pt-4">
              <h4 className="text-sm font-medium mb-3">
                {t('results.charts.cumulativeCost.title')}
              </h4>
              <div
                className="h-64"
                role="img"
                aria-label={t('results.charts.cumulativeCost.ariaLabel')}
              >
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="year" tick={{ fontSize: 12 }} tickLine={false} />
                    <YAxis
                      tick={{ fontSize: 12 }}
                      tickLine={false}
                      tickFormatter={(value) => `$${(value / 1000).toFixed(0)}k`}
                    />
                    <Tooltip
                      formatter={(value: number) => formatCurrency(value)}
                      labelFormatter={(label) => `Year ${label}`}
                    />
                    <Legend />
                    <Line
                      type="monotone"
                      dataKey="Cumulative Rent"
                      stroke="#3b82f6"
                      strokeWidth={2}
                      dot={false}
                    />
                    <Line
                      type="monotone"
                      dataKey="Cumulative Ownership"
                      stroke="#22c55e"
                      strokeWidth={2}
                      dot={false}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Equity vs Property Value Chart */}
            <div className="border-t pt-4">
              <h4 className="text-sm font-medium mb-3">{t('results.charts.equityGrowth.title')}</h4>
              <div
                className="h-64"
                role="img"
                aria-label={t('results.charts.equityGrowth.ariaLabel')}
              >
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="year" tick={{ fontSize: 12 }} tickLine={false} />
                    <YAxis
                      tick={{ fontSize: 12 }}
                      tickLine={false}
                      tickFormatter={(value) => `$${(value / 1000).toFixed(0)}k`}
                    />
                    <Tooltip
                      formatter={(value: number) => formatCurrency(value)}
                      labelFormatter={(label) => `Year ${label}`}
                    />
                    <Legend />
                    <Line
                      type="monotone"
                      dataKey="Property Value"
                      stroke="#8b5cf6"
                      strokeWidth={2}
                      dot={false}
                    />
                    <Line
                      type="monotone"
                      dataKey="Equity"
                      stroke="#06b6d4"
                      strokeWidth={2}
                      dot={false}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Summary Stats */}
            <div className="border-t pt-4">
              <h4 className="text-sm font-medium mb-3">{t('results.finalSummary')}</h4>
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div className="p-2 bg-muted/50 rounded">
                  <p className="text-muted-foreground">{t('results.finalPropertyValue')}</p>
                  <p className="font-medium">{formatCurrency(result.final_property_value)}</p>
                </div>
                <div className="p-2 bg-muted/50 rounded">
                  <p className="text-muted-foreground">{t('results.totalEquityBuilt')}</p>
                  <p className="font-medium">{formatCurrency(result.total_equity_built)}</p>
                </div>
                <div className="p-2 bg-muted/50 rounded">
                  <p className="text-muted-foreground">{t('results.opportunityCost')}</p>
                  <p className="font-medium">{formatCurrency(result.opportunity_cost_of_buying)}</p>
                </div>
                <div className="p-2 bg-muted/50 rounded">
                  <p className="text-muted-foreground">{t('results.netAdvantage')}</p>
                  <p
                    className={`font-medium ${result.net_buying_advantage >= 0 ? 'text-green-600' : 'text-red-600'}`}
                  >
                    {formatCurrency(result.net_buying_advantage)}
                  </p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
