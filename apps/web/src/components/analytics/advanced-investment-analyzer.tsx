'use client';

import React, { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { calculateAdvancedInvestment, ApiError } from '@/lib/api';
import type { AdvancedInvestmentResult, AdvancedInvestmentInput } from '@/lib/types';
import {
  Loader2,
  AlertCircle,
  RefreshCw,
  TrendingUp,
  ChevronDown,
  ChevronUp,
  Download,
} from 'lucide-react';
import { CashFlowChart } from './charts/cash-flow-chart';
import { ScenarioChart } from './charts/scenario-chart';
import { RiskGauge } from './charts/risk-gauge';
import { exportInvestmentToPDF } from '@/lib/investment-pdf-export';

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

export function AdvancedInvestmentAnalyzer() {
  const [loading, setLoading] = useState(false);
  const [errorState, setErrorState] = useState<ErrorState | null>(null);
  const [result, setResult] = useState<AdvancedInvestmentResult | null>(null);
  const [lastFormData, setLastFormData] = useState<typeof formData | null>(null);
  const [showAdvancedOptions, setShowAdvancedOptions] = useState(false);
  const [exporting, setExporting] = useState(false);

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
    projection_years: number;
    appreciation_rate: number;
    rent_growth_rate: number;
    marginal_tax_rate: number;
    land_value_ratio: number;
    market_volatility: number;
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
    projection_years: 10,
    appreciation_rate: 3,
    rent_growth_rate: 2,
    marginal_tax_rate: 24,
    land_value_ratio: 20,
    market_volatility: 50,
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
      const input: AdvancedInvestmentInput = {
        property_price: formData.property_price,
        monthly_rent: formData.monthly_rent,
        down_payment_percent: formData.down_payment_percent,
        closing_costs: formData.closing_costs,
        renovation_costs: formData.renovation_costs,
        interest_rate: formData.interest_rate,
        loan_years: formData.loan_years,
        property_tax_monthly: formData.property_tax_monthly,
        insurance_monthly: formData.insurance_monthly,
        hoa_monthly: formData.hoa_monthly,
        maintenance_percent: formData.maintenance_percent,
        vacancy_rate: formData.vacancy_rate,
        management_percent: formData.management_percent,
        projection_years: formData.projection_years,
        appreciation_rate: formData.appreciation_rate,
        rent_growth_rate: formData.rent_growth_rate,
        marginal_tax_rate: formData.marginal_tax_rate,
        land_value_ratio: formData.land_value_ratio,
        market_volatility: formData.market_volatility,
      };
      const data = await calculateAdvancedInvestment(input);
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
      const input: AdvancedInvestmentInput = {
        ...lastFormData,
      };
      const data = await calculateAdvancedInvestment(input);
      setResult(data);
    } catch (err: unknown) {
      setErrorState(extractErrorState(err));
    } finally {
      setLoading(false);
    }
  };

  const handleExportPDF = async () => {
    if (!result) return;

    setExporting(true);
    try {
      await exportInvestmentToPDF(result, {
        filename: `investment-analysis-${new Date().toISOString().split('T')[0]}`,
      });
    } catch (error) {
      console.error('Export failed:', error);
    } finally {
      setExporting(false);
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
          <p className="text-sm text-muted-foreground">
            Enter property details below to generate multi-year projections and risk analysis.
          </p>
        </div>
      )}

      <div className={result || errorState || loading ? 'grid gap-6 lg:grid-cols-2' : 'grid gap-6'}>
        {/* Form - centered when no results, left column when results present */}
        <Card className={result || errorState || loading ? undefined : 'mx-auto w-full max-w-2xl'}>
          <CardHeader>
            <CardTitle>Property Details</CardTitle>
            <CardDescription>
              Enter property and financing information for advanced analysis.
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

              {/* Financing Details */}
              <div className="space-y-3 pt-3 border-t">
                <h4 className="text-sm font-semibold">Financing</h4>
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
                    />
                  </div>
                </div>
              </div>

              {/* Operating Expenses */}
              <div className="space-y-3 pt-3 border-t">
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
                    Hide Advanced Options
                  </>
                ) : (
                  <>
                    <ChevronDown className="mr-2 h-4 w-4" aria-hidden="true" />
                    Show Advanced Options
                  </>
                )}
              </Button>

              {/* Advanced Options */}
              {showAdvancedOptions && (
                <div className="space-y-4 pt-4 border-t">
                  <h4 className="text-sm font-semibold">Projection Settings</h4>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="projection_years">Projection Years</Label>
                      <Input
                        id="projection_years"
                        name="projection_years"
                        type="number"
                        value={formData.projection_years}
                        onChange={handleChange}
                        min="1"
                        max="30"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="appreciation_rate">Expected Appreciation (%)</Label>
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
                      <Label htmlFor="rent_growth_rate">Rent Growth Rate (%)</Label>
                      <Input
                        id="rent_growth_rate"
                        name="rent_growth_rate"
                        type="number"
                        value={formData.rent_growth_rate}
                        onChange={handleChange}
                        min="0"
                        max="10"
                        step="0.5"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="marginal_tax_rate">Marginal Tax Rate (%)</Label>
                      <Input
                        id="marginal_tax_rate"
                        name="marginal_tax_rate"
                        type="number"
                        value={formData.marginal_tax_rate}
                        onChange={handleChange}
                        min="0"
                        max="50"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="land_value_ratio">Land Value Ratio (%)</Label>
                      <Input
                        id="land_value_ratio"
                        name="land_value_ratio"
                        type="number"
                        value={formData.land_value_ratio}
                        onChange={handleChange}
                        min="0"
                        max="100"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="market_volatility">Market Volatility (0-100)</Label>
                      <Input
                        id="market_volatility"
                        name="market_volatility"
                        type="number"
                        value={formData.market_volatility}
                        onChange={handleChange}
                        min="0"
                        max="100"
                      />
                    </div>
                  </div>
                </div>
              )}

              <Button type="submit" className="w-full" disabled={loading}>
                {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />}
                <TrendingUp className="mr-2 h-4 w-4" aria-hidden="true" />
                Run Advanced Analysis
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

        {/* Results */}
        {result && (
          <div className="space-y-6">
            {/* Quick Stats */}
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <div>
                  <CardTitle>Investment Summary</CardTitle>
                </div>
                <Button
                  onClick={handleExportPDF}
                  variant="outline"
                  size="sm"
                  className="flex items-center gap-2"
                  disabled={exporting || !result}
                >
                  {exporting ? (
                    <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                  ) : (
                    <Download className="h-4 w-4" aria-hidden="true" />
                  )}
                  Export Report
                </Button>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="text-center">
                    <p className="text-sm text-muted-foreground">Risk Score</p>
                    <p
                      className={`text-2xl font-bold ${
                        result.risk_score >= 80
                          ? 'text-green-600'
                          : result.risk_score >= 60
                            ? 'text-blue-600'
                            : result.risk_score >= 40
                              ? 'text-yellow-600'
                              : 'text-red-600'
                      }`}
                    >
                      {result.risk_score}
                    </p>
                    <p className="text-xs text-muted-foreground">/100</p>
                  </div>
                  <div className="text-center">
                    <p className="text-sm text-muted-foreground">Total Cash Flow</p>
                    <p
                      className={`text-2xl font-bold ${result.total_projected_cash_flow >= 0 ? 'text-green-600' : 'text-red-600'}`}
                    >
                      $
                      {result.total_projected_cash_flow.toLocaleString(undefined, {
                        maximumFractionDigits: 0,
                      })}
                    </p>
                  </div>
                  <div className="text-center">
                    <p className="text-sm text-muted-foreground">Final Equity</p>
                    <p className="text-2xl font-bold text-blue-600">
                      ${result.final_equity.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                    </p>
                  </div>
                  <div className="text-center">
                    <p className="text-sm text-muted-foreground">IRR</p>
                    <p
                      className={`text-2xl font-bold ${result.irr !== null && result.irr >= 0 ? 'text-green-600' : 'text-red-600'}`}
                    >
                      {result.irr !== null ? `${result.irr.toFixed(1)}%` : 'N/A'}
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Detailed Results Tabs */}
            <Tabs defaultValue="cashflow" className="w-full">
              <TabsList className="grid w-full grid-cols-4">
                <TabsTrigger value="cashflow">Cash Flow</TabsTrigger>
                <TabsTrigger value="scenarios">Scenarios</TabsTrigger>
                <TabsTrigger value="tax">Tax</TabsTrigger>
                <TabsTrigger value="risk">Risk</TabsTrigger>
              </TabsList>

              <TabsContent value="cashflow" className="mt-4">
                <CashFlowChart
                  data={result.cash_flow_projection}
                  title="Multi-Year Cash Flow Projection"
                  description={`${result.cash_flow_projection.length}-year projection with rent growth and appreciation`}
                />
              </TabsContent>

              <TabsContent value="scenarios" className="mt-4">
                <ScenarioChart
                  scenarios={result.appreciation_scenarios}
                  initialPrice={formData.property_price}
                />
              </TabsContent>

              <TabsContent value="tax" className="mt-4">
                <Card>
                  <CardHeader>
                    <CardTitle>Tax Implications</CardTitle>
                    <CardDescription>
                      Annual depreciation, deductions, and tax benefits
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="grid grid-cols-2 gap-6">
                      <div>
                        <p className="text-sm text-muted-foreground">Annual Depreciation</p>
                        <p className="text-xl font-semibold">
                          $
                          {result.annual_depreciation.toLocaleString(undefined, {
                            maximumFractionDigits: 0,
                          })}
                        </p>
                      </div>
                      <div>
                        <p className="text-sm text-muted-foreground">Total Tax Deductions</p>
                        <p className="text-xl font-semibold text-blue-600">
                          $
                          {result.total_tax_deductions.toLocaleString(undefined, {
                            maximumFractionDigits: 0,
                          })}
                        </p>
                      </div>
                      <div className="col-span-2">
                        <p className="text-sm text-muted-foreground">Annual Tax Benefit</p>
                        <p className="text-2xl font-bold text-green-600">
                          $
                          {result.tax_benefit.toLocaleString(undefined, {
                            maximumFractionDigits: 0,
                          })}
                        </p>
                      </div>
                    </div>
                    <div className="mt-4 pt-4 border-t">
                      <p className="text-xs text-muted-foreground">
                        Based on {formData.marginal_tax_rate}% marginal tax rate and{' '}
                        {formData.land_value_ratio}% land value ratio. Depreciation uses
                        straight-line method over 27.5 years (US residential).
                      </p>
                    </div>
                  </CardContent>
                </Card>
              </TabsContent>

              <TabsContent value="risk" className="mt-4">
                <RiskGauge
                  score={result.risk_score}
                  riskFactors={result.risk_factors}
                  recommendations={result.recommendations}
                />
              </TabsContent>
            </Tabs>
          </div>
        )}
      </div>
    </div>
  );
}
