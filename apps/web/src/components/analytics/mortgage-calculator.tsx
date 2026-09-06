'use client';

import React, { useState } from 'react';
import { useTranslations } from 'next-intl';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { calculateMortgage, calculateTCO, ApiError } from '@/lib/api';
import { MortgageResult, TCOResult } from '@/lib/types';
import {
  Loader2,
  AlertCircle,
  RefreshCw,
  ChevronDown,
  ChevronUp,
  Scale,
  Download,
} from 'lucide-react';
import { TCOBreakdownChart } from './charts/tco-breakdown-chart';
import { TCOComparison } from './tco-comparison';
import { exportTCOToPDF } from '@/lib/pdf-export';

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

export function MortgageCalculator() {
  const t = useTranslations('mortgage');
  const [loading, setLoading] = useState(false);
  const [errorState, setErrorState] = useState<ErrorState | null>(null);
  const [result, setResult] = useState<MortgageResult | null>(null);
  const [tcoResult, setTcoResult] = useState<TCOResult | null>(null);
  const [lastFormData, setLastFormData] = useState<typeof formData | null>(null);
  const [showTcoOptions, setShowTcoOptions] = useState(false);
  const [showComparison, setShowComparison] = useState(false);

  const [formData, setFormData] = useState({
    property_price: 500000,
    down_payment_percent: 20,
    interest_rate: 4.5,
    loan_years: 30,
    // TCO fields
    monthly_hoa: 0,
    annual_property_tax: 0,
    annual_insurance: 0,
    monthly_utilities: 0,
    monthly_internet: 0,
    monthly_parking: 0,
    maintenance_percent: 1,
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
      const [mortgageData, tcoData] = await Promise.all([
        calculateMortgage(formData),
        calculateTCO(formData),
      ]);
      setResult(mortgageData);
      setTcoResult(tcoData);
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
      const [mortgageData, tcoData] = await Promise.all([
        calculateMortgage(lastFormData),
        calculateTCO(lastFormData),
      ]);
      setResult(mortgageData);
      setTcoResult(tcoData);
    } catch (err: unknown) {
      setErrorState(extractErrorState(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={result || errorState || loading ? 'grid gap-6 md:grid-cols-2' : 'grid gap-6'}>
      {/* STATE 1: Empty state - guidance before calculation */}
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
            <div className="space-y-2">
              <Label htmlFor="property_price">{t('propertyPrice')} ($)</Label>
              <Input
                id="property_price"
                name="property_price"
                type="number"
                value={formData.property_price}
                onChange={handleChange}
                min="0"
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="down_payment_percent">{t('downPaymentPercent')}</Label>
              <Input
                id="down_payment_percent"
                name="down_payment_percent"
                type="number"
                value={formData.down_payment_percent}
                onChange={handleChange}
                min="0"
                max="100"
                step="0.1"
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="interest_rate">{t('interestRate')}</Label>
              <Input
                id="interest_rate"
                name="interest_rate"
                type="number"
                value={formData.interest_rate}
                onChange={handleChange}
                min="0"
                step="0.01"
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="loan_years">{t('loanTerm')}</Label>
              <Input
                id="loan_years"
                name="loan_years"
                type="number"
                value={formData.loan_years}
                onChange={handleChange}
                min="1"
                max="50"
                required
              />
            </div>
            {/* TCO Options Toggle */}
            <div className="pt-4 border-t">
              <Button
                type="button"
                variant="outline"
                className="w-full"
                onClick={() => setShowTcoOptions(!showTcoOptions)}
                aria-expanded={showTcoOptions}
              >
                {showTcoOptions ? (
                  <>
                    <ChevronUp className="mr-2 h-4 w-4" aria-hidden="true" />
                    {t('hideTcoOptions')}
                  </>
                ) : (
                  <>
                    <ChevronDown className="mr-2 h-4 w-4" aria-hidden="true" />
                    {t('showTcoOptions')}
                  </>
                )}
              </Button>
            </div>

            {/* TCO Input Fields */}
            {showTcoOptions && (
              <div className="space-y-4 pt-4">
                <h4 className="text-sm font-semibold">{t('tcoOptionsTitle')}</h4>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="monthly_hoa">{t('tco.monthlyHoa')} ($)</Label>
                    <Input
                      id="monthly_hoa"
                      name="monthly_hoa"
                      type="number"
                      value={formData.monthly_hoa}
                      onChange={handleChange}
                      min="0"
                      step="0.01"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="annual_property_tax">{t('tco.annualPropertyTax')} ($)</Label>
                    <Input
                      id="annual_property_tax"
                      name="annual_property_tax"
                      type="number"
                      value={formData.annual_property_tax}
                      onChange={handleChange}
                      min="0"
                      step="0.01"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="annual_insurance">{t('tco.annualInsurance')} ($)</Label>
                    <Input
                      id="annual_insurance"
                      name="annual_insurance"
                      type="number"
                      value={formData.annual_insurance}
                      onChange={handleChange}
                      min="0"
                      step="0.01"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="monthly_utilities">{t('tco.monthlyUtilities')} ($)</Label>
                    <Input
                      id="monthly_utilities"
                      name="monthly_utilities"
                      type="number"
                      value={formData.monthly_utilities}
                      onChange={handleChange}
                      min="0"
                      step="0.01"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="monthly_internet">{t('tco.monthlyInternet')} ($)</Label>
                    <Input
                      id="monthly_internet"
                      name="monthly_internet"
                      type="number"
                      value={formData.monthly_internet}
                      onChange={handleChange}
                      min="0"
                      step="0.01"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="monthly_parking">{t('tco.monthlyParking')} ($)</Label>
                    <Input
                      id="monthly_parking"
                      name="monthly_parking"
                      type="number"
                      value={formData.monthly_parking}
                      onChange={handleChange}
                      min="0"
                      step="0.01"
                    />
                  </div>
                  <div className="space-y-2 col-span-2">
                    <Label htmlFor="maintenance_percent">{t('tco.maintenancePercent')}</Label>
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
                    <p className="text-xs text-muted-foreground">{t('tco.maintenanceHint')}</p>
                  </div>
                </div>
              </div>
            )}

            <Button type="submit" className="w-full" disabled={loading}>
              {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />}
              {t('calculate')}
            </Button>

            {/* STATE 3: Error state with request_id and retry */}
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
                    <p className="text-sm text-destructive font-medium">{t('calculationFailed')}</p>
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
                    <RefreshCw className="h-3 w-3" />
                    {t('retry')}
                  </Button>
                </div>
              </div>
            )}
          </form>
        </CardContent>
      </Card>

      {result && (
        <Card>
          <CardHeader>
            <CardTitle>{t('results.title')}</CardTitle>
            <CardDescription>{t('results.description')}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-sm text-muted-foreground">{t('results.monthlyPayment')}</p>
                <p className="text-2xl font-bold">
                  ${result.monthly_payment.toLocaleString(undefined, { maximumFractionDigits: 2 })}
                </p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">{t('downPayment')}</p>
                <p className="text-xl font-semibold">
                  ${result.down_payment.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                </p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">{t('results.totalInterest')}</p>
                <p className="text-lg">
                  ${result.total_interest.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                </p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">{t('results.totalCost')}</p>
                <p className="text-lg">
                  ${result.total_cost.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                </p>
              </div>
            </div>

            <div className="border-t pt-4">
              <h4 className="text-sm font-medium mb-2">{t('results.monthlyBreakdown')}</h4>
              <div className="space-y-1">
                {Object.entries(result.breakdown).map(([key, value]) => (
                  <div key={key} className="flex justify-between text-sm">
                    <span className="capitalize">{key.replace(/_/g, ' ')}</span>
                    <span>${value.toLocaleString(undefined, { maximumFractionDigits: 2 })}</span>
                  </div>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {tcoResult && (
        <Card className="col-span-full md:col-span-2">
          <CardHeader>
            <CardTitle>{t('tco.title')}</CardTitle>
            <CardDescription>{t('tco.description')}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Monthly TCO Summary */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-primary/5 rounded-lg p-3">
                <p className="text-xs text-muted-foreground">{t('tco.monthlyTco')}</p>
                <p className="text-xl font-bold text-primary">
                  ${tcoResult.monthly_tco.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                </p>
              </div>
              <div className="bg-muted rounded-lg p-3">
                <p className="text-xs text-muted-foreground">{t('tco.annualTco')}</p>
                <p className="text-lg font-semibold">
                  ${tcoResult.annual_tco.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                </p>
              </div>
              <div className="bg-muted rounded-lg p-3">
                <p className="text-xs text-muted-foreground">
                  {t('tco.totalOverYears', { years: formData.loan_years })}
                </p>
                <p className="text-lg font-semibold">
                  $
                  {tcoResult.total_ownership_cost.toLocaleString(undefined, {
                    maximumFractionDigits: 0,
                  })}
                </p>
              </div>
              <div className="bg-muted rounded-lg p-3">
                <p className="text-xs text-muted-foreground">{t('tco.allInCost')}</p>
                <p className="text-lg font-semibold">
                  $
                  {tcoResult.total_all_costs.toLocaleString(undefined, {
                    maximumFractionDigits: 0,
                  })}
                </p>
              </div>
            </div>

            {/* Monthly Breakdown */}
            <div className="border-t pt-4">
              <h4 className="text-sm font-medium mb-3">{t('tco.monthlyCostBreakdown')}</h4>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <div className="flex justify-between text-sm p-2 bg-muted/50 rounded">
                  <span className="text-muted-foreground">{t('tco.mortgage')}</span>
                  <span className="font-medium">
                    $
                    {tcoResult.monthly_mortgage.toLocaleString(undefined, {
                      maximumFractionDigits: 0,
                    })}
                  </span>
                </div>
                <div className="flex justify-between text-sm p-2 bg-muted/50 rounded">
                  <span className="text-muted-foreground">{t('tco.propertyTax')}</span>
                  <span className="font-medium">
                    $
                    {tcoResult.monthly_property_tax.toLocaleString(undefined, {
                      maximumFractionDigits: 0,
                    })}
                  </span>
                </div>
                <div className="flex justify-between text-sm p-2 bg-muted/50 rounded">
                  <span className="text-muted-foreground">{t('tco.insurance')}</span>
                  <span className="font-medium">
                    $
                    {tcoResult.monthly_insurance.toLocaleString(undefined, {
                      maximumFractionDigits: 0,
                    })}
                  </span>
                </div>
                <div className="flex justify-between text-sm p-2 bg-muted/50 rounded">
                  <span className="text-muted-foreground">{t('tco.hoa')}</span>
                  <span className="font-medium">
                    ${tcoResult.monthly_hoa.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                  </span>
                </div>
                <div className="flex justify-between text-sm p-2 bg-muted/50 rounded">
                  <span className="text-muted-foreground">{t('tco.utilities')}</span>
                  <span className="font-medium">
                    $
                    {tcoResult.monthly_utilities.toLocaleString(undefined, {
                      maximumFractionDigits: 0,
                    })}
                  </span>
                </div>
                <div className="flex justify-between text-sm p-2 bg-muted/50 rounded">
                  <span className="text-muted-foreground">{t('tco.monthlyInternet')}</span>
                  <span className="font-medium">
                    $
                    {tcoResult.monthly_internet.toLocaleString(undefined, {
                      maximumFractionDigits: 0,
                    })}
                  </span>
                </div>
                <div className="flex justify-between text-sm p-2 bg-muted/50 rounded">
                  <span className="text-muted-foreground">{t('tco.monthlyParking')}</span>
                  <span className="font-medium">
                    $
                    {tcoResult.monthly_parking.toLocaleString(undefined, {
                      maximumFractionDigits: 0,
                    })}
                  </span>
                </div>
                <div className="flex justify-between text-sm p-2 bg-muted/50 rounded">
                  <span className="text-muted-foreground">{t('tco.maintenance')}</span>
                  <span className="font-medium">
                    $
                    {tcoResult.monthly_maintenance.toLocaleString(undefined, {
                      maximumFractionDigits: 0,
                    })}
                  </span>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* TCO Breakdown Pie Chart */}
      {tcoResult && (
        <TCOBreakdownChart tcoResult={tcoResult} className="col-span-full md:col-span-2" />
      )}

      {/* Export PDF Button */}
      {tcoResult && (
        <div className="col-span-full md:col-span-2 flex justify-center">
          <Button variant="outline" onClick={() => exportTCOToPDF(tcoResult)} className="gap-2">
            <Download className="h-4 w-4" />
            {t('exportToPdf')}
          </Button>
        </div>
      )}

      {/* Compare Scenarios Button */}
      {tcoResult && (
        <div className="col-span-full md:col-span-2 flex justify-center">
          <Button
            variant="outline"
            size="lg"
            onClick={() => setShowComparison(!showComparison)}
            className="gap-2"
          >
            <Scale className="h-4 w-4" />
            {showComparison ? t('hideComparison') : t('compareScenarios')}
          </Button>
        </div>
      )}

      {/* TCO Comparison Section */}
      {showComparison && (
        <div className="col-span-full md:col-span-2">
          <TCOComparison />
        </div>
      )}
    </div>
  );
}
