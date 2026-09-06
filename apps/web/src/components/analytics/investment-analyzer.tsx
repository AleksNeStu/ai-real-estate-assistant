'use client';

import React, { useState } from 'react';
import { useTranslations } from 'next-intl';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { calculateInvestment, ApiError } from '@/lib/api';
import { InvestmentAnalysisResult } from '@/lib/types';
import { Loader2, AlertCircle, RefreshCw, ChevronDown, ChevronUp } from 'lucide-react';

interface ErrorState {
  message: string;
  requestId?: string;
}

const extractErrorState = (err: unknown): ErrorState => {
  let message = 'Unknown error';
  let requestId: string | undefined = undefined;

  if (err instanceof ApiError) {
    message = err.message;
    requestId = err.request_id;
  } else if (err instanceof Error) {
    message = err.message;
  } else {
    message = String(err);
  }

  return { message, requestId };
};

const getScoreColor = (score: number): string => {
  if (score >= 80) return 'text-green-600';
  if (score >= 60) return 'text-yellow-600';
  if (score >= 40) return 'text-orange-600';
  return 'text-red-600';
};

const getScoreLabel = (score: number, t: (key: string) => string): string => {
  if (score >= 80) return t('scoreExcellent');
  if (score >= 60) return t('scoreGood');
  if (score >= 40) return t('scoreFair');
  return t('scorePoor');
};

export function InvestmentAnalyzer() {
  const t = useTranslations('investment');
  const [loading, setLoading] = useState(false);
  const [errorState, setErrorState] = useState<ErrorState | null>(null);
  const [result, setResult] = useState<InvestmentAnalysisResult | null>(null);
  const [lastFormData, setLastFormData] = useState<typeof formData | null>(null);
  const [showFinancingOptions, setShowFinancingOptions] = useState(false);
  const [showExpenseOptions, setShowExpenseOptions] = useState(false);

  const [formData, setFormData] = useState<{
    property_price: number;
    monthly_rent: number;
    down_payment_percent: number;
    closing_costs: number;
    renovation_costs: number;
    interest_rate: number;
    loan_years: number;
    property_tax_monthly: number;
    insurance_monthly: number;
    hoa_monthly: number;
    maintenance_percent: number;
    vacancy_rate: number;
    management_percent: number;
  }>({
    property_price: 200000,
    monthly_rent: 1800,
    down_payment_percent: 20,
    closing_costs: 5000,
    renovation_costs: 0,
    interest_rate: 4.5,
    loan_years: 30,
    property_tax_monthly: 200,
    insurance_monthly: 100,
    hoa_monthly: 0,
    maintenance_percent: 1,
    vacancy_rate: 5,
    management_percent: 0,
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
      const data = await calculateInvestment(formData);
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
      const data = await calculateInvestment(lastFormData);
      setResult(data);
    } catch (err: unknown) {
      setErrorState(extractErrorState(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={result || errorState || loading ? 'grid gap-6 md:grid-cols-2' : 'grid gap-6'}>
      {/* Empty state guidance */}
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
          <CardTitle>Investment Property Analyzer</CardTitle>
          <CardDescription>
            Calculate ROI, cap rate, cash flow, and investment quality score.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleCalculate} className="space-y-4">
            {/* Basic Property Information */}
            <div className="space-y-3">
              <h4 className="text-sm font-semibold">Property Information</h4>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="property_price">Purchase Price ($)</Label>
                  <Input
                    id="property_price"
                    name="property_price"
                    type="number"
                    value={formData.property_price}
                    onChange={handleChange}
                    min="0"
                    step="1000"
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="monthly_rent">Monthly Rent ($)</Label>
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

            {/* Financing Toggle */}
            <Button
              type="button"
              variant="outline"
              className="w-full"
              onClick={() => setShowFinancingOptions(!showFinancingOptions)}
              aria-expanded={showFinancingOptions}
            >
              {showFinancingOptions ? (
                <>
                  <ChevronUp className="mr-2 h-4 w-4" aria-hidden="true" />
                  Hide Financing Options
                </>
              ) : (
                <>
                  <ChevronDown className="mr-2 h-4 w-4" aria-hidden="true" />
                  Show Financing Options
                </>
              )}
            </Button>

            {/* Financing Options */}
            {showFinancingOptions && (
              <div className="space-y-4 pt-4 border-t">
                <h4 className="text-sm font-semibold">Financing Details</h4>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="down_payment_percent">Down Payment (%)</Label>
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
                    <Label htmlFor="interest_rate">Interest Rate (%)</Label>
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
                    <Label htmlFor="loan_years">Loan Term (Years)</Label>
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
                  <div className="space-y-2">
                    <Label htmlFor="closing_costs">Closing Costs ($)</Label>
                    <Input
                      id="closing_costs"
                      name="closing_costs"
                      type="number"
                      value={formData.closing_costs}
                      onChange={handleChange}
                      min="0"
                      step="100"
                    />
                  </div>
                  <div className="space-y-2 col-span-2">
                    <Label htmlFor="renovation_costs">Renovation Costs ($)</Label>
                    <Input
                      id="renovation_costs"
                      name="renovation_costs"
                      type="number"
                      value={formData.renovation_costs}
                      onChange={handleChange}
                      min="0"
                      step="100"
                    />
                  </div>
                </div>
              </div>
            )}

            {/* Expenses Toggle */}
            <Button
              type="button"
              variant="outline"
              className="w-full"
              onClick={() => setShowExpenseOptions(!showExpenseOptions)}
              aria-expanded={showExpenseOptions}
            >
              {showExpenseOptions ? (
                <>
                  <ChevronUp className="mr-2 h-4 w-4" aria-hidden="true" />
                  Hide Operating Expenses
                </>
              ) : (
                <>
                  <ChevronDown className="mr-2 h-4 w-4" aria-hidden="true" />
                  Show Operating Expenses
                </>
              )}
            </Button>

            {/* Operating Expenses */}
            {showExpenseOptions && (
              <div className="space-y-4 pt-4 border-t">
                <h4 className="text-sm font-semibold">Monthly Operating Expenses</h4>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="property_tax_monthly">Property Tax ($)</Label>
                    <Input
                      id="property_tax_monthly"
                      name="property_tax_monthly"
                      type="number"
                      value={formData.property_tax_monthly}
                      onChange={handleChange}
                      min="0"
                      step="10"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="insurance_monthly">Insurance ($)</Label>
                    <Input
                      id="insurance_monthly"
                      name="insurance_monthly"
                      type="number"
                      value={formData.insurance_monthly}
                      onChange={handleChange}
                      min="0"
                      step="10"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="hoa_monthly">HOA Fees ($)</Label>
                    <Input
                      id="hoa_monthly"
                      name="hoa_monthly"
                      type="number"
                      value={formData.hoa_monthly}
                      onChange={handleChange}
                      min="0"
                      step="10"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="maintenance_percent">Maintenance (% of value)</Label>
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
                  <div className="space-y-2">
                    <Label htmlFor="vacancy_rate">Vacancy Rate (%)</Label>
                    <Input
                      id="vacancy_rate"
                      name="vacancy_rate"
                      type="number"
                      value={formData.vacancy_rate}
                      onChange={handleChange}
                      min="0"
                      max="100"
                      step="1"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="management_percent">Management Fee (% of rent)</Label>
                    <Input
                      id="management_percent"
                      name="management_percent"
                      type="number"
                      value={formData.management_percent}
                      onChange={handleChange}
                      min="0"
                      max="15"
                      step="0.5"
                    />
                  </div>
                </div>
              </div>
            )}

            <Button type="submit" className="w-full" disabled={loading}>
              {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />}
              Analyze Investment
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
                    <p className="text-sm text-destructive font-medium">Analysis failed</p>
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
                    Retry
                  </Button>
                </div>
              </div>
            )}
          </form>
        </CardContent>
      </Card>

      {/* Results Card */}
      {result && (
        <Card>
          <CardHeader>
            <CardTitle>Investment Analysis Results</CardTitle>
            <CardDescription>Comprehensive metrics and investment quality score.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Investment Score */}
            <div className="bg-primary/5 rounded-lg p-4 text-center">
              <p className="text-sm text-muted-foreground mb-1">Investment Score</p>
              <div className="flex items-center justify-center gap-3">
                <p className={`text-4xl font-bold ${getScoreColor(result.investment_score)}`}>
                  {result.investment_score.toFixed(1)}
                </p>
                <p className={`text-lg font-semibold ${getScoreColor(result.investment_score)}`}>
                  /100 - {getScoreLabel(result.investment_score, t)}
                </p>
              </div>
              <div className="mt-3 grid grid-cols-2 gap-2 text-xs">
                {Object.entries(result.score_breakdown).map(([key, value]) => (
                  <div key={key} className="flex justify-between">
                    <span className="text-muted-foreground">
                      {key.replace(/_/g, ' ').replace('score', 'score').replace('yield', 'yield')}:
                    </span>
                    <span className="font-medium">{value.toFixed(1)}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Key Metrics */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-sm text-muted-foreground">Monthly Cash Flow</p>
                <p
                  className={`text-xl font-bold ${result.monthly_cash_flow >= 0 ? 'text-green-600' : 'text-red-600'}`}
                >
                  $
                  {result.monthly_cash_flow.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                </p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Cash on Cash ROI</p>
                <p className="text-xl font-bold">{result.cash_on_cash_roi.toFixed(2)}%</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Cap Rate</p>
                <p className="text-xl font-bold">{result.cap_rate.toFixed(2)}%</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Net Yield</p>
                <p className="text-xl font-bold">{result.net_yield.toFixed(2)}%</p>
              </div>
            </div>

            {/* Monthly Breakdown */}
            <div className="border-t pt-4">
              <h4 className="text-sm font-medium mb-3">Monthly Cash Flow Breakdown</h4>
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Monthly Income (Rent)</span>
                  <span className="font-medium text-green-600">
                    ${result.monthly_income.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                  </span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Mortgage Payment</span>
                  <span className="font-medium text-red-600">
                    -$
                    {result.monthly_mortgage.toLocaleString(undefined, {
                      maximumFractionDigits: 0,
                    })}
                  </span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Operating Expenses</span>
                  <span className="font-medium text-red-600">
                    -$
                    {(result.monthly_expenses - result.monthly_mortgage).toLocaleString(undefined, {
                      maximumFractionDigits: 0,
                    })}
                  </span>
                </div>
                <div className="flex justify-between text-sm font-semibold pt-2 border-t">
                  <span>Net Monthly Cash Flow</span>
                  <span
                    className={result.monthly_cash_flow >= 0 ? 'text-green-600' : 'text-red-600'}
                  >
                    $
                    {result.monthly_cash_flow.toLocaleString(undefined, {
                      maximumFractionDigits: 0,
                    })}
                  </span>
                </div>
              </div>
            </div>

            {/* Investment Metrics */}
            <div className="border-t pt-4">
              <h4 className="text-sm font-medium mb-3">Investment Metrics</h4>
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div className="p-2 bg-muted/50 rounded">
                  <p className="text-muted-foreground">Total Investment</p>
                  <p className="font-medium">
                    $
                    {result.total_investment.toLocaleString(undefined, {
                      maximumFractionDigits: 0,
                    })}
                  </p>
                </div>
                <div className="p-2 bg-muted/50 rounded">
                  <p className="text-muted-foreground">Annual Cash Flow</p>
                  <p
                    className={`font-medium ${result.annual_cash_flow >= 0 ? 'text-green-600' : 'text-red-600'}`}
                  >
                    $
                    {result.annual_cash_flow.toLocaleString(undefined, {
                      maximumFractionDigits: 0,
                    })}
                  </p>
                </div>
                <div className="p-2 bg-muted/50 rounded">
                  <p className="text-muted-foreground">Gross Yield</p>
                  <p className="font-medium">{result.gross_yield.toFixed(2)}%</p>
                </div>
                <div className="p-2 bg-muted/50 rounded">
                  <p className="text-muted-foreground">Annual Income</p>
                  <p className="font-medium">
                    ${result.annual_income.toLocaleString(undefined, { maximumFractionDigits: 0 })}
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
