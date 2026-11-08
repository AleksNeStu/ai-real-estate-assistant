/**
 * PDF Export Utility for Investment Analysis Results
 *
 * Uses jsPDF to generate PDF exports of investment analysis
 */

import jsPDF from 'jspdf';
import type { AdvancedInvestmentResult } from './types';

interface InvestmentPDFOptions {
  title?: string;
  filename?: string;
  includeDate?: boolean;
  /**
   * Translated labels for the document. Every field falls back to the
   * English default, so callers that do not care about localisation can keep
   * passing an empty options object.
   */
  copy?: Partial<InvestmentPdfCopy>;
}

/**
 * Every user-visible label of the investment analysis PDF.
 *
 * The lib stays free of any i18n dependency: the caller reads the labels
 * from the message catalogue and hands them over as `copy`.
 */
export interface InvestmentPdfCopy {
  title: string;
  generated: string;
  keyMetrics: string;
  monthlyCashFlow: string;
  annualCashFlow: string;
  cashOnCashRoi: string;
  capRate: string;
  grossYield: string;
  netYield: string;
  totalInvestment: string;
  investmentScore: string;
  incomeExpenses: string;
  monthlyIncome: string;
  monthlyExpenses: string;
  annualIncome: string;
  annualExpenses: string;
  monthlyMortgage: string;
  scoreBreakdown: string;
  advancedMetrics: string;
  riskScore: string;
  totalProjectedCashFlow: string;
  finalEquity: string;
  irr: string;
  annualDepreciation: string;
  taxBenefit: string;
  riskFactors: string;
  recommendations: string;
  cashFlowProjectionSummary: string;
  year: string;
  cashFlow: string;
  cumulative: string;
  equity: string;
  pageOf: string;
  footerBrand: string;
  notAvailable: string;
  /**
   * Optional map from the API score-breakdown keys (`location`, `type`, …) to
   * translated labels. Unknown keys fall back to a title-cased version of the
   * key itself.
   */
  scoreLabels?: Record<string, string>;
}

/**
 * English defaults — the document reads exactly as it did before the copy
 * parameter was introduced.
 */
export const DEFAULT_INVESTMENT_PDF_COPY: InvestmentPdfCopy = {
  title: 'Investment Analysis Report',
  generated: 'Generated: {date}',
  keyMetrics: 'Key Metrics',
  monthlyCashFlow: 'Monthly Cash Flow',
  annualCashFlow: 'Annual Cash Flow',
  cashOnCashRoi: 'Cash-on-Cash ROI',
  capRate: 'Cap Rate',
  grossYield: 'Gross Yield',
  netYield: 'Net Yield',
  totalInvestment: 'Total Investment',
  investmentScore: 'Investment Score',
  incomeExpenses: 'Income & Expenses',
  monthlyIncome: 'Monthly Income',
  monthlyExpenses: 'Monthly Expenses',
  annualIncome: 'Annual Income',
  annualExpenses: 'Annual Expenses',
  monthlyMortgage: 'Monthly Mortgage',
  scoreBreakdown: 'Score Breakdown',
  advancedMetrics: 'Advanced Metrics',
  riskScore: 'Risk Score',
  totalProjectedCashFlow: 'Total Projected Cash Flow',
  finalEquity: 'Final Equity',
  irr: 'IRR',
  annualDepreciation: 'Annual Depreciation',
  taxBenefit: 'Tax Benefit',
  riskFactors: 'Risk Factors',
  recommendations: 'Recommendations',
  cashFlowProjectionSummary: 'Cash Flow Projection Summary',
  year: 'Year',
  cashFlow: 'Cash Flow',
  cumulative: 'Cumulative',
  equity: 'Equity',
  pageOf: 'Page {page} of {total}',
  footerBrand: 'AI Real Estate Assistant - Investment Analysis',
  notAvailable: 'N/A',
};

/**
 * Fill `{name}` placeholders in a label. The PDF copy uses plain named
 * placeholders only — no ICU plurals — so a plain replacement is enough and
 * the lib stays independent of any i18n runtime.
 */
function fill(template: string, params: Record<string, string | number>): string {
  return Object.entries(params).reduce(
    (acc, [key, value]) => acc.replaceAll(`{${key}}`, String(value)),
    template
  );
}

/**
 * Format currency for PDF display
 */
function formatCurrency(value: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
  }).format(value);
}

/**
 * Format percentage for PDF display
 */
function formatPercent(value: number): string {
  return `${value.toFixed(2)}%`;
}

/**
 * Generate a PDF from investment analysis result data
 */
export async function exportInvestmentToPDF(
  result: AdvancedInvestmentResult,
  options: InvestmentPDFOptions = {}
): Promise<void> {
  const c: InvestmentPdfCopy = { ...DEFAULT_INVESTMENT_PDF_COPY, ...options.copy };
  const { title = c.title, filename = 'investment-analysis', includeDate = true } = options;

  const doc = new jsPDF();
  const pageWidth = doc.internal.pageSize.getWidth();
  const pageHeight = doc.internal.pageSize.getHeight();
  const margin = 20;
  let y = 20;

  // Title
  doc.setFontSize(18);
  doc.setFont('helvetica', 'bold');
  doc.text(title, margin, y);
  y += 10;

  // Date
  if (includeDate) {
    doc.setFontSize(10);
    doc.setFont('helvetica', 'normal');
    doc.setTextColor(100);
    doc.text(fill(c.generated, { date: new Date().toLocaleDateString() }), margin, y);
    y += 15;
  }

  doc.setTextColor(0);

  // Key Metrics Section
  doc.setFontSize(14);
  doc.setFont('helvetica', 'bold');
  doc.text(c.keyMetrics, margin, y);
  y += 8;

  // Draw separator line
  doc.setDrawColor(200);
  doc.line(margin, y - 2, pageWidth - margin, y - 2);

  // Metrics data in two columns
  const metrics = [
    [c.monthlyCashFlow, formatCurrency(result.monthly_cash_flow)],
    [c.annualCashFlow, formatCurrency(result.annual_cash_flow)],
    [c.cashOnCashRoi, formatPercent(result.cash_on_cash_roi)],
    [c.capRate, formatPercent(result.cap_rate)],
    [c.grossYield, formatPercent(result.gross_yield)],
    [c.netYield, formatPercent(result.net_yield)],
    [c.totalInvestment, formatCurrency(result.total_investment)],
    [c.investmentScore, `${result.investment_score.toFixed(0)}/100`],
  ];

  doc.setFontSize(10);
  doc.setFont('helvetica', 'normal');

  const leftColX = margin;
  const rightColX = margin + 80;
  let leftY = y;
  let rightY = y;

  metrics.forEach((metric, index) => {
    const [label, value] = metric;
    if (index < metrics.length / 2) {
      doc.setFont('helvetica', 'bold');
      doc.text(label + ':', leftColX, leftY);
      doc.setFont('helvetica', 'normal');
      doc.text(value, leftColX + 45, leftY);
      leftY += 6;
    } else {
      doc.setFont('helvetica', 'bold');
      doc.text(label + ':', rightColX, rightY);
      doc.setFont('helvetica', 'normal');
      doc.text(value, rightColX + 45, rightY);
      rightY += 6;
    }
  });

  y = Math.max(leftY, rightY) + 10;

  // Income and Expenses Section
  if (y > pageHeight - 60) {
    doc.addPage();
    y = 20;
  }

  doc.setFontSize(14);
  doc.setFont('helvetica', 'bold');
  doc.text(c.incomeExpenses, margin, y);
  y += 8;

  doc.line(margin, y - 2, pageWidth - margin, y - 2);
  y += 5;

  doc.setFontSize(10);
  doc.setFont('helvetica', 'normal');

  const incomeExpenses = [
    [c.monthlyIncome, formatCurrency(result.monthly_income)],
    [c.monthlyExpenses, formatCurrency(result.monthly_expenses)],
    [c.annualIncome, formatCurrency(result.annual_income)],
    [c.annualExpenses, formatCurrency(result.annual_expenses)],
    [c.monthlyMortgage, formatCurrency(result.monthly_mortgage)],
  ];

  incomeExpenses.forEach(([label, value]) => {
    doc.setFont('helvetica', 'bold');
    doc.text(label + ':', margin, y);
    doc.setFont('helvetica', 'normal');
    doc.text(value, margin + 60, y);
    y += 6;
  });

  // Investment Score Breakdown
  if (result.score_breakdown && Object.keys(result.score_breakdown).length > 0) {
    y += 8;

    if (y > pageHeight - 50) {
      doc.addPage();
      y = 20;
    }

    doc.setFontSize(12);
    doc.setFont('helvetica', 'bold');
    doc.text(c.scoreBreakdown, margin, y);
    y += 8;

    doc.setFontSize(10);
    doc.setFont('helvetica', 'normal');

    Object.entries(result.score_breakdown).forEach(([key, value]) => {
      const label =
        c.scoreLabels?.[key] ??
        key
          .split('_')
          .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
          .join(' ');
      doc.text(`${label}:`, margin + 5, y);
      doc.text(`${value.toFixed(1)}`, margin + 60, y);
      y += 5;
    });
  }

  // Advanced Metrics
  y += 10;

  if (y > pageHeight - 50) {
    doc.addPage();
    y = 20;
  }

  doc.setFontSize(12);
  doc.setFont('helvetica', 'bold');
  doc.text(c.advancedMetrics, margin, y);
  y += 8;

  doc.setFontSize(10);
  doc.setFont('helvetica', 'normal');

  const advancedMetrics = [
    [c.riskScore, `${result.risk_score}/100`],
    [c.totalProjectedCashFlow, formatCurrency(result.total_projected_cash_flow)],
    [c.finalEquity, formatCurrency(result.final_equity)],
    [c.irr, result.irr !== null ? formatPercent(result.irr) : c.notAvailable],
    [c.annualDepreciation, formatCurrency(result.annual_depreciation)],
    [c.taxBenefit, formatCurrency(result.tax_benefit)],
  ];

  advancedMetrics.forEach(([label, value]) => {
    doc.setFont('helvetica', 'bold');
    doc.text(label + ':', margin, y);
    doc.setFont('helvetica', 'normal');
    doc.text(value, margin + 60, y);
    y += 6;
  });

  // Risk Factors
  if (result.risk_factors && result.risk_factors.length > 0) {
    y += 8;

    if (y > pageHeight - 40) {
      doc.addPage();
      y = 20;
    }

    doc.setFontSize(12);
    doc.setFont('helvetica', 'bold');
    doc.text(c.riskFactors, margin, y);
    y += 8;

    doc.setFontSize(10);
    doc.setFont('helvetica', 'normal');

    result.risk_factors.forEach((factor) => {
      const lines = doc.splitTextToSize(`\u2022 ${factor}`, pageWidth - 2 * margin - 5);
      lines.forEach((line: string) => {
        doc.text(line, margin + 5, y);
        y += 5;
      });
    });
  }

  // Recommendations
  if (result.recommendations && result.recommendations.length > 0) {
    y += 8;

    if (y > pageHeight - 40) {
      doc.addPage();
      y = 20;
    }

    doc.setFontSize(12);
    doc.setFont('helvetica', 'bold');
    doc.text(c.recommendations, margin, y);
    y += 8;

    doc.setFontSize(10);
    doc.setFont('helvetica', 'normal');

    result.recommendations.forEach((rec) => {
      const lines = doc.splitTextToSize(`\u2022 ${rec}`, pageWidth - 2 * margin - 5);
      lines.forEach((line: string) => {
        doc.text(line, margin + 5, y);
        y += 5;
      });
    });
  }

  // Cash Flow Projection Summary
  if (result.cash_flow_projection && result.cash_flow_projection.length > 0) {
    y += 10;

    if (y > pageHeight - 50) {
      doc.addPage();
      y = 20;
    }

    doc.setFontSize(12);
    doc.setFont('helvetica', 'bold');
    doc.text(c.cashFlowProjectionSummary, margin, y);
    y += 8;

    // Table header
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(9);
    doc.text(c.year, margin, y);
    doc.text(c.cashFlow, margin + 25, y);
    doc.text(c.cumulative, margin + 60, y);
    doc.text(c.equity, margin + 95, y);
    doc.line(margin, y + 2, pageWidth - margin, y + 2);
    y += 6;

    // Show first 5 years and last year
    const projectionsToShow = [
      ...result.cash_flow_projection.slice(0, 5),
      result.cash_flow_projection[result.cash_flow_projection.length - 1],
    ];

    doc.setFont('helvetica', 'normal');
    projectionsToShow.forEach((proj) => {
      if (y > pageHeight - 20) {
        doc.addPage();
        y = 20;
        doc.setFont('helvetica', 'bold');
        doc.text(c.year, margin, y);
        doc.text(c.cashFlow, margin + 25, y);
        doc.text(c.cumulative, margin + 60, y);
        doc.text(c.equity, margin + 95, y);
        doc.line(margin, y + 2, pageWidth - margin, y + 2);
        y += 6;
        doc.setFont('helvetica', 'normal');
      }
      doc.text(`${proj.year}`, margin, y);
      doc.text(formatCurrency(proj.cash_flow), margin + 25, y);
      doc.text(formatCurrency(proj.cumulative_cash_flow), margin + 60, y);
      doc.text(formatCurrency(proj.equity), margin + 95, y);
      y += 5;
    });
  }

  // Footer
  const pageCount = doc.getNumberOfPages();
  for (let i = 1; i <= pageCount; i++) {
    doc.setPage(i);
    doc.setFontSize(8);
    doc.setTextColor(150);
    doc.text(fill(c.pageOf, { page: i, total: pageCount }), pageWidth / 2, pageHeight - 10, {
      align: 'center',
    });
    doc.text(c.footerBrand, pageWidth / 2, pageHeight - 6, { align: 'center' });
  }

  // Save the PDF
  const dateSuffix = includeDate ? `-${new Date().toISOString().split('T')[0]}` : '';
  doc.save(`${filename}${dateSuffix}.pdf`);
}
