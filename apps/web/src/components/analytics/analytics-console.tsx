'use client';

import { useState, type ComponentType } from 'react';
import dynamic from 'next/dynamic';
import { useTranslations } from 'next-intl';

import { MonoAnnotation } from '@/components/ui/mono-annotation';

/**
 * The tools of the assistant, in one console.
 *
 * The prototype puts the five calculators behind a row of tabs, so only one
 * of them is on the screen at a time and the screen stays an instrument
 * rather than a stack of panels. The calculators themselves are not rebuilt
 * here: each one is the tool the assistant calls, imported lazily, and the
 * space it needs is held open while it arrives.
 *
 * The tab row is a row of labels with a rule under the one that is open -
 * the same shape the prototype draws, and the same shape the route uses for
 * its own tabs.
 */

const ToolPlaceholder = () => (
  <div className="h-64 w-full animate-pulse rounded-lg bg-muted" aria-hidden="true" />
);

const MortgageCalculator = dynamic(
  () =>
    import('@/components/analytics/mortgage-calculator').then((m) => ({
      default: m.MortgageCalculator,
    })),
  { ssr: false, loading: () => <ToolPlaceholder /> }
);

const InvestmentAnalyzer = dynamic(
  () =>
    import('@/components/analytics/investment-analyzer').then((m) => ({
      default: m.InvestmentAnalyzer,
    })),
  { ssr: false, loading: () => <ToolPlaceholder /> }
);

const AdvancedInvestmentAnalyzer = dynamic(
  () =>
    import('@/components/analytics/advanced-investment-analyzer').then((m) => ({
      default: m.AdvancedInvestmentAnalyzer,
    })),
  { ssr: false, loading: () => <ToolPlaceholder /> }
);

const PortfolioAnalyzer = dynamic(
  () =>
    import('@/components/analytics/portfolio-analyzer').then((m) => ({
      default: m.PortfolioAnalyzer,
    })),
  { ssr: false, loading: () => <ToolPlaceholder /> }
);

const RentVsBuyCalculator = dynamic(
  () =>
    import('@/components/analytics/rent-vs-buy-calculator').then((m) => ({
      default: m.RentVsBuyCalculator,
    })),
  { ssr: false, loading: () => <ToolPlaceholder /> }
);

interface Tool {
  id: string;
  /** The label of the tab, and the key the catalogue holds it under. */
  label: string;
  Component: ComponentType;
}

export function AnalyticsConsole() {
  const t = useTranslations('pages.analytics');

  const tools: Tool[] = [
    { id: 'mortgage', label: t('tools.mortgage'), Component: MortgageCalculator },
    { id: 'investment', label: t('tools.investment'), Component: InvestmentAnalyzer },
    { id: 'advanced', label: t('tools.advanced'), Component: AdvancedInvestmentAnalyzer },
    { id: 'portfolio', label: t('tools.portfolio'), Component: PortfolioAnalyzer },
    { id: 'rentVsBuy', label: t('tools.rentVsBuy'), Component: RentVsBuyCalculator },
  ];
  const [active, setActive] = useState(tools[0].id);

  const current = tools.find((tool) => tool.id === active) ?? tools[0];
  const ToolComponent = current.Component;

  return (
    <div>
      <div
        role="tablist"
        aria-label={t('tools.label')}
        className="flex flex-wrap gap-x-6 gap-y-1 border-b border-border"
      >
        {tools.map((tool) => {
          const isActive = tool.id === active;
          return (
            <button
              key={tool.id}
              type="button"
              role="tab"
              id={`analytics-tab-${tool.id}`}
              aria-selected={isActive}
              aria-controls="analytics-tool"
              onClick={() => setActive(tool.id)}
              className={[
                '-mb-px border-b-2 py-2.5 text-[14px] font-medium transition-colors',
                isActive
                  ? 'border-foreground text-foreground'
                  : 'border-transparent text-muted-foreground hover:text-foreground',
              ].join(' ')}
            >
              {tool.label}
            </button>
          );
        })}
      </div>

      <div
        id="analytics-tool"
        role="tabpanel"
        aria-labelledby={`analytics-tab-${current.id}`}
        className="pt-6"
      >
        <div className="mb-4 flex items-baseline justify-between gap-4">
          <h2 className="text-[18px] font-semibold text-foreground">{current.label}</h2>
          <MonoAnnotation>{t('note')}</MonoAnnotation>
        </div>
        <ToolComponent />
      </div>
    </div>
  );
}
