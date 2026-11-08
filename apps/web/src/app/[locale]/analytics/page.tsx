'use client';

import { BarChart3, TrendingUp, Calculator, PieChart, Scale } from 'lucide-react';
import dynamic from 'next/dynamic';
import { useTranslations } from 'next-intl';

import { PageHeader } from '@/components/ui/page-header';

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
  const t = useTranslations('pages.analytics');
  // The four calculators already carry their title in the catalogue; the
  // advanced investment section is page copy of its own.
  const tMortgage = useTranslations('mortgage');
  const tInvestment = useTranslations('investment');
  const tPortfolio = useTranslations('portfolio');
  const tRentVsBuy = useTranslations('rentVsBuy');

  return (
    <div className="container mx-auto px-4 py-8 space-y-8">
      <PageHeader title={t('title')} description={t('description')} />

      <div className="space-y-12">
        <section className="rounded-lg border bg-card p-6">
          <h2 className="text-2xl font-semibold mb-6 flex items-center gap-2">
            <BarChart3 className="h-6 w-6" />
            {tMortgage('title')}
          </h2>
          <MortgageCalculator />
        </section>

        <section className="rounded-lg border bg-card p-6">
          <h2 className="text-2xl font-semibold mb-6 flex items-center gap-2">
            <TrendingUp className="h-6 w-6" />
            {tInvestment('title')}
          </h2>
          <InvestmentAnalyzer />
        </section>

        <section className="rounded-lg border bg-card p-6">
          <h2 className="text-2xl font-semibold mb-6 flex items-center gap-2">
            <Calculator className="h-6 w-6" />
            {t('sections.advancedInvestment')}
          </h2>
          <AdvancedInvestmentAnalyzer />
        </section>

        <section className="rounded-lg border bg-card p-6">
          <h2 className="text-2xl font-semibold mb-6 flex items-center gap-2">
            <PieChart className="h-6 w-6" />
            {tPortfolio('title')}
          </h2>
          <PortfolioAnalyzer />
        </section>

        <section className="rounded-lg border bg-card p-6">
          <h2 className="text-2xl font-semibold mb-6 flex items-center gap-2">
            <Scale className="h-6 w-6" />
            {tRentVsBuy('title')}
          </h2>
          <RentVsBuyCalculator />
        </section>
      </div>
    </div>
  );
}
