'use client';

import { BarChart3, TrendingUp, Calculator, PieChart, Scale } from 'lucide-react';
import dynamic from 'next/dynamic';

const MortgageCalculator = dynamic(
  () =>
    import('@/components/analytics/mortgage-calculator').then((m) => ({
      default: m.MortgageCalculator,
    })),
  { ssr: false, loading: () => <div className="h-64 animate-pulse bg-muted rounded-lg" /> }
);
const InvestmentAnalyzer = dynamic(
  () =>
    import('@/components/analytics/investment-analyzer').then((m) => ({
      default: m.InvestmentAnalyzer,
    })),
  { ssr: false, loading: () => <div className="h-64 animate-pulse bg-muted rounded-lg" /> }
);
const AdvancedInvestmentAnalyzer = dynamic(
  () =>
    import('@/components/analytics/advanced-investment-analyzer').then((m) => ({
      default: m.AdvancedInvestmentAnalyzer,
    })),
  { ssr: false, loading: () => <div className="h-64 animate-pulse bg-muted rounded-lg" /> }
);
const PortfolioAnalyzer = dynamic(
  () =>
    import('@/components/analytics/portfolio-analyzer').then((m) => ({
      default: m.PortfolioAnalyzer,
    })),
  { ssr: false, loading: () => <div className="h-64 animate-pulse bg-muted rounded-lg" /> }
);
const RentVsBuyCalculator = dynamic(
  () =>
    import('@/components/analytics/rent-vs-buy-calculator').then((m) => ({
      default: m.RentVsBuyCalculator,
    })),
  { ssr: false, loading: () => <div className="h-64 animate-pulse bg-muted rounded-lg" /> }
);

export default function AnalyticsPage() {
  return (
    <div className="container mx-auto px-4 py-8 space-y-8">
      <div className="flex flex-col gap-2">
        <h1 className="text-3xl font-bold tracking-tight">Analytics & Tools</h1>
        <p className="text-muted-foreground text-lg">
          Market insights and financial tools to help you make informed decisions.
        </p>
      </div>

      <div className="space-y-12">
        <section className="rounded-lg border bg-card p-6">
          <h2 className="text-2xl font-semibold mb-6 flex items-center gap-2">
            <BarChart3 className="h-6 w-6" />
            Mortgage Calculator
          </h2>
          <MortgageCalculator />
        </section>

        <section className="rounded-lg border bg-card p-6">
          <h2 className="text-2xl font-semibold mb-6 flex items-center gap-2">
            <TrendingUp className="h-6 w-6" />
            Investment Property Analyzer
          </h2>
          <InvestmentAnalyzer />
        </section>

        <section className="rounded-lg border bg-card p-6">
          <h2 className="text-2xl font-semibold mb-6 flex items-center gap-2">
            <Calculator className="h-6 w-6" />
            Advanced Investment Analytics
          </h2>
          <AdvancedInvestmentAnalyzer />
        </section>

        <section className="rounded-lg border bg-card p-6">
          <h2 className="text-2xl font-semibold mb-6 flex items-center gap-2">
            <PieChart className="h-6 w-6" />
            Portfolio Analyzer
          </h2>
          <PortfolioAnalyzer />
        </section>

        <section className="rounded-lg border bg-card p-6">
          <h2 className="text-2xl font-semibold mb-6 flex items-center gap-2">
            <Scale className="h-6 w-6" />
            Rent vs Buy Calculator
          </h2>
          <RentVsBuyCalculator />
        </section>
      </div>
    </div>
  );
}
