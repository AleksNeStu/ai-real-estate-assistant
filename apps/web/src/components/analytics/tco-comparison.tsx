'use client';

import React, { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { Loader2, AlertCircle, ArrowRight, Check } from 'lucide-react';
import { compareTCO, ApiError } from '@/lib/api';
import type { TCOInput, TCOComparisonResult, EnhancedTCOResult } from '@/lib/types';
import { TCOBreakdownChart } from './charts/tco-breakdown-chart';
import { TCOProjectionChart } from './charts/tco-projection-chart';
import { useTranslations } from 'next-intl';

interface TCOComparisonProps {
  className?: string;
}

interface ScenarioFormProps {
  title: string;
  formData: TCOInput;
  onChange: (data: TCOInput) => void;
  disabled?: boolean;
}

function ScenarioForm({ title, formData, onChange, disabled }: ScenarioFormProps) {
  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    onChange({
      ...formData,
      [name]: parseFloat(value) || 0,
    });
  };

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-lg">{title}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-1">
            <Label htmlFor={`${title}-price`} className="text-xs">
              Property Price
            </Label>
            <Input
              id={`${title}-price`}
              name="property_price"
              type="number"
              value={formData.property_price}
              onChange={handleChange}
              disabled={disabled}
              min="0"
              className="h-8"
            />
          </div>
          <div className="space-y-1">
            <Label htmlFor={`${title}-down`} className="text-xs">
              Down Payment %
            </Label>
            <Input
              id={`${title}-down`}
              name="down_payment_percent"
              type="number"
              value={formData.down_payment_percent || 20}
              onChange={handleChange}
              disabled={disabled}
              min="0"
              max="100"
              step="0.1"
              className="h-8"
            />
          </div>
          <div className="space-y-1">
            <Label htmlFor={`${title}-rate`} className="text-xs">
              Interest Rate %
            </Label>
            <Input
              id={`${title}-rate`}
              name="interest_rate"
              type="number"
              value={formData.interest_rate || 4.5}
              onChange={handleChange}
              disabled={disabled}
              min="0"
              step="0.1"
              className="h-8"
            />
          </div>
          <div className="space-y-1">
            <Label htmlFor={`${title}-years`} className="text-xs">
              Loan Years
            </Label>
            <Input
              id={`${title}-years`}
              name="loan_years"
              type="number"
              value={formData.loan_years || 30}
              onChange={handleChange}
              disabled={disabled}
              min="1"
              max="50"
              className="h-8"
            />
          </div>
        </div>

        <Separator className="my-2" />

        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-1">
            <Label htmlFor={`${title}-hoa`} className="text-xs">
              Monthly HOA
            </Label>
            <Input
              id={`${title}-hoa`}
              name="monthly_hoa"
              type="number"
              value={formData.monthly_hoa || 0}
              onChange={handleChange}
              disabled={disabled}
              min="0"
              className="h-8"
            />
          </div>
          <div className="space-y-1">
            <Label htmlFor={`${title}-tax`} className="text-xs">
              Annual Tax
            </Label>
            <Input
              id={`${title}-tax`}
              name="annual_property_tax"
              type="number"
              value={formData.annual_property_tax || 0}
              onChange={handleChange}
              disabled={disabled}
              min="0"
              className="h-8"
            />
          </div>
          <div className="space-y-1">
            <Label htmlFor={`${title}-insurance`} className="text-xs">
              Annual Insurance
            </Label>
            <Input
              id={`${title}-insurance`}
              name="annual_insurance"
              type="number"
              value={formData.annual_insurance || 0}
              onChange={handleChange}
              disabled={disabled}
              min="0"
              className="h-8"
            />
          </div>
          <div className="space-y-1">
            <Label htmlFor={`${title}-utilities`} className="text-xs">
              Monthly Utilities
            </Label>
            <Input
              id={`${title}-utilities`}
              name="monthly_utilities"
              type="number"
              value={formData.monthly_utilities || 0}
              onChange={handleChange}
              disabled={disabled}
              min="0"
              className="h-8"
            />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

interface ResultCardProps {
  result: EnhancedTCOResult;
  name: string;
  isRecommended?: boolean;
}

function ResultCard({ result, name, isRecommended }: ResultCardProps) {
  const t = useTranslations('mortgage');
  const formatCurrency = (value: number) =>
    `$${value.toLocaleString(undefined, { maximumFractionDigits: 0 })}`;

  return (
    <Card className={isRecommended ? 'border-success border-2' : ''}>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg">{name}</CardTitle>
          {isRecommended && (
            <Badge variant="default" className="bg-success">
              {t('tco.recommended')}
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 gap-3 mb-4">
          <div>
            <p className="text-xs text-muted-foreground">{t('tco.monthlyTco')}</p>
            <p className="text-xl font-bold">{formatCurrency(result.monthly_tco)}</p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">{t('tco.annualTco')}</p>
            <p className="text-lg font-semibold">{formatCurrency(result.annual_tco)}</p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">{t('tco.totalOver30Years')}</p>
            <p className="text-lg font-semibold">{formatCurrency(result.total_ownership_cost)}</p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">{t('tco.downPayment')}</p>
            <p className="text-lg font-semibold">{formatCurrency(result.down_payment)}</p>
          </div>
        </div>

        <TCOBreakdownChart
          tcoResult={result}
          title=""
          description=""
          className="border-0 shadow-none"
        />
      </CardContent>
    </Card>
  );
}

export function TCOComparison({ className }: TCOComparisonProps) {
  const t = useTranslations('mortgage');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<TCOComparisonResult | null>(null);

  const [scenarioA, setScenarioA] = useState<TCOInput>({
    property_price: 400000,
    down_payment_percent: 20,
    interest_rate: 4.5,
    loan_years: 30,
    monthly_hoa: 300,
    annual_property_tax: 4000,
    annual_insurance: 1200,
    monthly_utilities: 150,
    monthly_internet: 60,
    monthly_parking: 0,
    maintenance_percent: 1,
  });

  const [scenarioB, setScenarioB] = useState<TCOInput>({
    property_price: 550000,
    down_payment_percent: 20,
    interest_rate: 4.5,
    loan_years: 30,
    monthly_hoa: 150,
    annual_property_tax: 5500,
    annual_insurance: 1500,
    monthly_utilities: 200,
    monthly_internet: 60,
    monthly_parking: 100,
    maintenance_percent: 1,
  });

  const handleCompare = async () => {
    setLoading(true);
    setError(null);

    try {
      const comparisonResult = await compareTCO({
        scenario_a: scenarioA,
        scenario_b: scenarioB,
        scenario_a_name: t('tco.scenarios.centralApartment'),
        scenario_b_name: t('tco.scenarios.suburbanHouse'),
        comparison_years: 10,
        appreciation_rate: 3,
        priority_monthly_cashflow: 0.3,
        priority_long_term_equity: 0.4,
        priority_total_cost: 0.3,
      });
      setResult(comparisonResult);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError(t('tco.comparisonFailed'));
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={className}>
      <Card className="mb-6">
        <CardHeader>
          <CardTitle>{t('tco.compareScenarios')}</CardTitle>
          <CardDescription>
            Compare Total Cost of Ownership between two property scenarios with trade-off analysis
            and recommendations.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {/* Input Forms Side by Side */}
          <div className="grid md:grid-cols-2 gap-4 mb-4">
            <ScenarioForm
              title={t('tco.scenarios.scenarioA')}
              formData={scenarioA}
              onChange={setScenarioA}
              disabled={loading}
            />
            <ScenarioForm
              title={t('tco.scenarios.scenarioB')}
              formData={scenarioB}
              onChange={setScenarioB}
              disabled={loading}
            />
          </div>

          {/* Compare Button */}
          <div className="flex justify-center">
            <Button onClick={handleCompare} disabled={loading} size="lg">
              {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />}
              Compare Scenarios
            </Button>
          </div>

          {/* Error State */}
          {error && (
            <div className="mt-4 flex items-center gap-2 text-destructive bg-destructive/10 p-3 rounded-lg">
              <AlertCircle className="h-4 w-4" aria-hidden="true" />
              <span className="text-sm">{error}</span>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Comparison Results */}
      {result && (
        <>
          {/* Summary Card */}
          <Card className="mb-6">
            <CardHeader>
              <CardTitle>{t('tco.comparisonSummary')}</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid md:grid-cols-3 gap-6">
                {/* Cost Difference */}
                <div className="text-center">
                  <p className="text-sm text-muted-foreground mb-2">{t('tco.monthlyDifference')}</p>
                  <p
                    className={`text-2xl font-bold ${
                      result.monthly_cost_difference > 0 ? 'text-destructive' : 'text-success'
                    }`}
                  >
                    {result.monthly_cost_difference > 0 ? '+' : ''}$
                    {result.monthly_cost_difference.toLocaleString(undefined, {
                      maximumFractionDigits: 0,
                    })}
                  </p>
                  <p className="text-xs text-muted-foreground mt-1">
                    {result.scenario_a_name} vs {result.scenario_b_name}
                  </p>
                </div>

                {/* Equity Difference */}
                <div className="text-center">
                  <p className="text-sm text-muted-foreground mb-2">{t('tco.equityDifference')}</p>
                  <p
                    className={`text-2xl font-bold ${
                      result.equity_difference < 0 ? 'text-destructive' : 'text-success'
                    }`}
                  >
                    {result.equity_difference > 0 ? '+' : ''}$
                    {result.equity_difference.toLocaleString(undefined, {
                      maximumFractionDigits: 0,
                    })}
                  </p>
                  <p className="text-xs text-muted-foreground mt-1">
                    {result.scenario_a_name} vs {result.scenario_b_name}
                  </p>
                </div>

                {/* Break Even */}
                <div className="text-center">
                  <p className="text-sm text-muted-foreground mb-2">{t('tco.breakEvenPoint')}</p>
                  {result.break_even_years ? (
                    <p className="text-2xl font-bold">{result.break_even_years.toFixed(1)} years</p>
                  ) : (
                    <p className="text-2xl font-bold text-muted-foreground">N/A</p>
                  )}
                  <p className="text-xs text-muted-foreground mt-1">{t('tco.breakEvenHint')}</p>
                </div>
              </div>

              {/* Recommendation */}
              <div className="mt-6 p-4 bg-primary/5 rounded-lg">
                <div className="flex items-start gap-3">
                  {result.recommendation === 'scenario_a' ? (
                    <Check className="h-5 w-5 text-success mt-0.5" aria-hidden="true" />
                  ) : result.recommendation === 'scenario_b' ? (
                    <Check className="h-5 w-5 text-success mt-0.5" aria-hidden="true" />
                  ) : (
                    <ArrowRight className="h-5 w-5 text-info mt-0.5" aria-hidden="true" />
                  )}
                  <div>
                    <p className="font-medium">Recommendation: {result.recommendation}</p>
                    <p className="text-sm text-muted-foreground mt-1">
                      {result.recommendation_reason}
                    </p>
                  </div>
                </div>
              </div>

              {/* Trade-offs */}
              <div className="grid md:grid-cols-2 gap-4 mt-4">
                <div className="p-4 bg-muted rounded-lg">
                  <h4 className="font-medium mb-2 flex items-center gap-2">
                    <Check className="h-4 w-4 text-success" aria-hidden="true" />
                    {result.scenario_a_name} Advantages
                  </h4>
                  <ul className="text-sm space-y-1">
                    {result.a_advantages.map((adv, i) => (
                      <li key={i} className="text-muted-foreground">
                        • {adv}
                      </li>
                    ))}
                  </ul>
                </div>
                <div className="p-4 bg-muted rounded-lg">
                  <h4 className="font-medium mb-2 flex items-center gap-2">
                    <Check className="h-4 w-4 text-success" aria-hidden="true" />
                    {result.scenario_b_name} Advantages
                  </h4>
                  <ul className="text-sm space-y-1">
                    {result.b_advantages.map((adv, i) => (
                      <li key={i} className="text-muted-foreground">
                        • {adv}
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Detailed Results Side by Side */}
          <div className="grid md:grid-cols-2 gap-6">
            <ResultCard
              result={result.scenario_a}
              name={result.scenario_a_name}
              isRecommended={result.recommendation === 'scenario_a'}
            />
            <ResultCard
              result={result.scenario_b}
              name={result.scenario_b_name}
              isRecommended={result.recommendation === 'scenario_b'}
            />
          </div>

          {/* Projections Chart */}
          {result.scenario_a.projections.length > 0 && (
            <div className="mt-6">
              <TCOProjectionChart projections={result.scenario_a.projections} />
            </div>
          )}
        </>
      )}
    </div>
  );
}
