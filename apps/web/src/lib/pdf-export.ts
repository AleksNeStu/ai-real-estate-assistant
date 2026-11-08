/**
 * PDF Export Utility for TCO Calculator Results
 *
 * Uses jsPDF and html2canvas to generate PDF exports of TCO analysis
 */

import jsPDF from 'jspdf';
import html2canvas from 'html2canvas';
import type { TCOResult, TCOComparisonResult, EnhancedTCOResult } from './types';

interface PDFOptions {
  title?: string;
  filename?: string;
  includeDate?: boolean;
  /**
   * Translated labels for the document. Every field falls back to the
   * English default, so callers that do not care about localisation can keep
   * passing an empty options object.
   */
  copy?: Partial<TcoPdfCopy>;
}

/**
 * Every user-visible label of the TCO PDF documents.
 *
 * The lib stays free of any i18n dependency: the caller reads the labels
 * from the message catalogue and hands them over as `copy`.
 */
export interface TcoPdfCopy {
  title: string;
  comparisonTitle: string;
  generated: string;
  summary: string;
  monthlyTco: string;
  annualTco: string;
  downPayment: string;
  loanAmount: string;
  monthlyBreakdown: string;
  mortgage: string;
  propertyTax: string;
  insurance: string;
  hoa: string;
  utilities: string;
  internet: string;
  parking: string;
  maintenance: string;
  totalCosts: string;
  totalOwnershipCost: string;
  allInCost: string;
  multiYearProjections: string;
  year: string;
  cumulativeCost: string;
  equityBuilt: string;
  propertyValue: string;
  costCategoryAnalysis: string;
  fixedCosts: string;
  variableCosts: string;
  discretionaryCosts: string;
  pageOf: string;
  comparisonSummary: string;
  keyDifferences: string;
  totalCost: string;
  monthlyCostDifference: string;
  equityDifference: string;
  breakEvenPoint: string;
  breakEvenNotAvailable: string;
  recommendation: string;
  recommended: string;
  advantages: string;
}

/**
 * English defaults — the document reads exactly as it did before the copy
 * parameter was introduced.
 */
export const DEFAULT_TCO_PDF_COPY: TcoPdfCopy = {
  title: 'Total Cost of Ownership Analysis',
  comparisonTitle: 'TCO Comparison Analysis',
  generated: 'Generated: {date}',
  summary: 'Summary',
  monthlyTco: 'Monthly TCO',
  annualTco: 'Annual TCO',
  downPayment: 'Down Payment',
  loanAmount: 'Loan Amount',
  monthlyBreakdown: 'Monthly Cost Breakdown',
  mortgage: 'Mortgage',
  propertyTax: 'Property Tax',
  insurance: 'Insurance',
  hoa: 'HOA',
  utilities: 'Utilities',
  internet: 'Internet',
  parking: 'Parking',
  maintenance: 'Maintenance',
  totalCosts: 'Total Costs',
  totalOwnershipCost: 'Total Ownership Cost',
  allInCost: 'All-In Cost (incl. Down Payment)',
  multiYearProjections: 'Multi-Year Projections',
  year: 'Year',
  cumulativeCost: 'Cumulative Cost',
  equityBuilt: 'Equity Built',
  propertyValue: 'Property Value',
  costCategoryAnalysis: 'Cost Category Analysis',
  fixedCosts: 'Fixed Costs (Monthly)',
  variableCosts: 'Variable Costs (Monthly)',
  discretionaryCosts: 'Discretionary Costs (Monthly)',
  pageOf: 'Page {page} of {total}',
  comparisonSummary: 'Comparison Summary',
  keyDifferences: 'Key Differences',
  totalCost: 'Total Cost',
  monthlyCostDifference: 'Monthly Cost Difference',
  equityDifference: 'Equity Difference',
  breakEvenPoint: 'Break-Even Point: {years} years',
  breakEvenNotAvailable: 'Break-Even Point: N/A',
  recommendation: 'Recommendation',
  recommended: 'Recommended',
  advantages: '{scenario} Advantages',
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
function formatCurrency(value: number, currency: string = 'USD'): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency,
    maximumFractionDigits: 0,
  }).format(value);
}

/**
 * Generate a PDF from TCO result data
 */
export async function exportTCOToPDF(
  tcoResult: TCOResult | EnhancedTCOResult,
  options: PDFOptions = {}
): Promise<void> {
  const c: TcoPdfCopy = { ...DEFAULT_TCO_PDF_COPY, ...options.copy };
  const { title = c.title, filename = 'tco-analysis', includeDate = true } = options;

  const doc = new jsPDF();
  const pageWidth = doc.internal.pageSize.getWidth();
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

  // Summary Section
  doc.setFontSize(14);
  doc.setFont('helvetica', 'bold');
  doc.text(c.summary, margin, y);
  y += 8;

  doc.setFontSize(10);
  doc.setFont('helvetica', 'normal');

  const summaryData = [
    [c.monthlyTco, formatCurrency(tcoResult.monthly_tco)],
    [c.annualTco, formatCurrency(tcoResult.annual_tco)],
    [c.downPayment, formatCurrency(tcoResult.down_payment)],
    [c.loanAmount, formatCurrency(tcoResult.loan_amount)],
  ];

  summaryData.forEach(([label, value]) => {
    doc.text(`${label}:`, margin, y);
    doc.text(value, margin + 60, y);
    y += 6;
  });

  y += 10;

  // Monthly Breakdown Section
  doc.setFontSize(14);
  doc.setFont('helvetica', 'bold');
  doc.text(c.monthlyBreakdown, margin, y);
  y += 8;

  doc.setFontSize(10);
  doc.setFont('helvetica', 'normal');

  const breakdownData = [
    [c.mortgage, formatCurrency(tcoResult.monthly_mortgage)],
    [c.propertyTax, formatCurrency(tcoResult.monthly_property_tax)],
    [c.insurance, formatCurrency(tcoResult.monthly_insurance)],
    [c.hoa, formatCurrency(tcoResult.monthly_hoa)],
    [c.utilities, formatCurrency(tcoResult.monthly_utilities)],
    [c.internet, formatCurrency(tcoResult.monthly_internet)],
    [c.parking, formatCurrency(tcoResult.monthly_parking)],
    [c.maintenance, formatCurrency(tcoResult.monthly_maintenance)],
  ];

  breakdownData.forEach(([label, value]) => {
    doc.text(`${label}:`, margin, y);
    doc.text(value, margin + 60, y);
    y += 6;
  });

  y += 10;

  // Total Costs Section
  doc.setFontSize(14);
  doc.setFont('helvetica', 'bold');
  doc.text(c.totalCosts, margin, y);
  y += 8;

  doc.setFontSize(10);
  doc.setFont('helvetica', 'normal');

  doc.text(`${c.totalOwnershipCost}:`, margin, y);
  doc.text(formatCurrency(tcoResult.total_ownership_cost), margin + 80, y);
  y += 6;

  doc.text(`${c.allInCost}:`, margin, y);
  doc.text(formatCurrency(tcoResult.total_all_costs), margin + 80, y);
  y += 15;

  // Projections (if EnhancedTCOResult)
  const enhancedResult = tcoResult as EnhancedTCOResult;
  if (enhancedResult.projections && enhancedResult.projections.length > 0) {
    // Check if we need a new page
    if (y > 220) {
      doc.addPage();
      y = 20;
    }

    doc.setFontSize(14);
    doc.setFont('helvetica', 'bold');
    doc.text(c.multiYearProjections, margin, y);
    y += 8;

    doc.setFontSize(10);
    doc.setFont('helvetica', 'normal');

    // Table header
    doc.setFont('helvetica', 'bold');
    doc.text(c.year, margin, y);
    doc.text(c.cumulativeCost, margin + 25, y);
    doc.text(c.equityBuilt, margin + 65, y);
    doc.text(c.propertyValue, margin + 105, y);
    y += 6;

    doc.setFont('helvetica', 'normal');
    enhancedResult.projections.forEach((proj) => {
      doc.text(`${proj.year}`, margin, y);
      doc.text(formatCurrency(proj.cumulative_cost), margin + 25, y);
      doc.text(formatCurrency(proj.cumulative_equity), margin + 65, y);
      doc.text(formatCurrency(proj.property_value_estimate), margin + 105, y);
      y += 5;
    });
  }

  // Cost Category Analysis (if EnhancedTCOResult)
  if (
    enhancedResult.percentage_breakdown &&
    Object.keys(enhancedResult.percentage_breakdown).length > 0
  ) {
    y += 10;

    // Check if we need a new page
    if (y > 220) {
      doc.addPage();
      y = 20;
    }

    doc.setFontSize(14);
    doc.setFont('helvetica', 'bold');
    doc.text(c.costCategoryAnalysis, margin, y);
    y += 8;

    doc.setFontSize(10);
    doc.setFont('helvetica', 'normal');

    Object.entries(enhancedResult.percentage_breakdown).forEach(([category, percentage]) => {
      doc.text(`${category}:`, margin, y);
      doc.text(`${percentage.toFixed(1)}%`, margin + 60, y);
      y += 5;
    });

    y += 5;
    doc.text(`${c.fixedCosts}:`, margin, y);
    doc.text(formatCurrency(enhancedResult.fixed_costs_monthly), margin + 70, y);
    y += 5;

    doc.text(`${c.variableCosts}:`, margin, y);
    doc.text(formatCurrency(enhancedResult.variable_costs_monthly), margin + 70, y);
    y += 5;

    doc.text(`${c.discretionaryCosts}:`, margin, y);
    doc.text(formatCurrency(enhancedResult.discretionary_costs_monthly), margin + 70, y);
  }

  // Footer
  const pageCount = doc.getNumberOfPages();
  for (let i = 1; i <= pageCount; i++) {
    doc.setPage(i);
    doc.setFontSize(8);
    doc.setTextColor(150);
    doc.text(
      fill(c.pageOf, { page: i, total: pageCount }),
      pageWidth / 2,
      doc.internal.pageSize.getHeight() - 10,
      {
        align: 'center',
      }
    );
  }

  // Save the PDF
  const dateSuffix = includeDate ? `-${new Date().toISOString().split('T')[0]}` : '';
  doc.save(`${filename}${dateSuffix}.pdf`);
}

/**
 * Generate a PDF from TCO comparison result
 */
export async function exportTCOComparisonToPDF(
  comparisonResult: TCOComparisonResult,
  options: PDFOptions = {}
): Promise<void> {
  const c: TcoPdfCopy = { ...DEFAULT_TCO_PDF_COPY, ...options.copy };
  const { title = c.comparisonTitle, filename = 'tco-comparison', includeDate = true } = options;

  const doc = new jsPDF();
  const pageWidth = doc.internal.pageSize.getWidth();
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

  // Comparison Summary
  doc.setFontSize(14);
  doc.setFont('helvetica', 'bold');
  doc.text(c.comparisonSummary, margin, y);
  y += 8;

  doc.setFontSize(10);
  doc.setFont('helvetica', 'normal');

  // Scenario A
  doc.setFont('helvetica', 'bold');
  doc.text(comparisonResult.scenario_a_name, margin, y);
  doc.setFont('helvetica', 'normal');
  y += 6;

  doc.text(
    `${c.monthlyTco}: ${formatCurrency(comparisonResult.scenario_a.monthly_tco)}`,
    margin + 10,
    y
  );
  y += 5;
  doc.text(
    `${c.totalCost}: ${formatCurrency(comparisonResult.scenario_a.total_ownership_cost)}`,
    margin + 10,
    y
  );
  y += 8;

  // Scenario B
  doc.setFont('helvetica', 'bold');
  doc.text(comparisonResult.scenario_b_name, margin, y);
  doc.setFont('helvetica', 'normal');
  y += 6;

  doc.text(
    `${c.monthlyTco}: ${formatCurrency(comparisonResult.scenario_b.monthly_tco)}`,
    margin + 10,
    y
  );
  y += 5;
  doc.text(
    `${c.totalCost}: ${formatCurrency(comparisonResult.scenario_b.total_ownership_cost)}`,
    margin + 10,
    y
  );
  y += 10;

  // Differences
  doc.setFontSize(14);
  doc.setFont('helvetica', 'bold');
  doc.text(c.keyDifferences, margin, y);
  y += 8;

  doc.setFontSize(10);
  doc.setFont('helvetica', 'normal');

  const diffSign = comparisonResult.monthly_cost_difference > 0 ? '+' : '';
  const diffColor = comparisonResult.monthly_cost_difference > 0 ? [200, 0, 0] : [0, 150, 0];
  doc.setTextColor(diffColor[0], diffColor[1], diffColor[2]);
  doc.text(
    `${c.monthlyCostDifference}: ${diffSign}${formatCurrency(comparisonResult.monthly_cost_difference)}`,
    margin,
    y
  );
  doc.setTextColor(0);
  y += 6;

  doc.text(
    `${c.equityDifference}: ${formatCurrency(comparisonResult.equity_difference)}`,
    margin,
    y
  );
  y += 6;

  if (comparisonResult.break_even_years) {
    doc.text(
      fill(c.breakEvenPoint, { years: comparisonResult.break_even_years.toFixed(1) }),
      margin,
      y
    );
  } else {
    doc.text(c.breakEvenNotAvailable, margin, y);
  }
  y += 10;

  // Recommendation
  doc.setFontSize(14);
  doc.setFont('helvetica', 'bold');
  doc.text(c.recommendation, margin, y);
  y += 8;

  doc.setFontSize(10);
  doc.setFont('helvetica', 'normal');

  doc.setFont('helvetica', 'bold');
  doc.text(`${c.recommended}: ${comparisonResult.recommendation}`, margin, y);
  doc.setFont('helvetica', 'normal');
  y += 6;

  // Wrap recommendation reason text
  const reasonLines = doc.splitTextToSize(
    comparisonResult.recommendation_reason,
    pageWidth - 2 * margin
  );
  reasonLines.forEach((line: string) => {
    doc.text(line, margin, y);
    y += 5;
  });

  y += 10;

  // Advantages
  if (y > 200) {
    doc.addPage();
    y = 20;
  }

  // Scenario A Advantages
  doc.setFontSize(12);
  doc.setFont('helvetica', 'bold');
  doc.text(fill(c.advantages, { scenario: comparisonResult.scenario_a_name }), margin, y);
  y += 6;

  doc.setFontSize(10);
  doc.setFont('helvetica', 'normal');
  comparisonResult.a_advantages.slice(0, 5).forEach((adv) => {
    const lines = doc.splitTextToSize(`• ${adv}`, pageWidth - 2 * margin - 5);
    lines.forEach((line: string) => {
      doc.text(line, margin + 5, y);
      y += 5;
    });
  });

  y += 5;

  // Scenario B Advantages
  doc.setFontSize(12);
  doc.setFont('helvetica', 'bold');
  doc.text(fill(c.advantages, { scenario: comparisonResult.scenario_b_name }), margin, y);
  y += 6;

  doc.setFontSize(10);
  doc.setFont('helvetica', 'normal');
  comparisonResult.b_advantages.slice(0, 5).forEach((adv) => {
    const lines = doc.splitTextToSize(`• ${adv}`, pageWidth - 2 * margin - 5);
    lines.forEach((line: string) => {
      doc.text(line, margin + 5, y);
      y += 5;
    });
  });

  // Footer
  const pageCount = doc.getNumberOfPages();
  for (let i = 1; i <= pageCount; i++) {
    doc.setPage(i);
    doc.setFontSize(8);
    doc.setTextColor(150);
    doc.text(
      fill(c.pageOf, { page: i, total: pageCount }),
      pageWidth / 2,
      doc.internal.pageSize.getHeight() - 10,
      {
        align: 'center',
      }
    );
  }

  // Save the PDF
  const dateSuffix = includeDate ? `-${new Date().toISOString().split('T')[0]}` : '';
  doc.save(`${filename}${dateSuffix}.pdf`);
}

/**
 * Capture a DOM element and add it to a PDF as an image
 */
export async function captureElementToPDF(
  elementId: string,
  options: PDFOptions = {}
): Promise<void> {
  const { title, filename = 'export', includeDate = true } = options;

  const element = document.getElementById(elementId);
  if (!element) {
    throw new Error(`Element with id "${elementId}" not found`);
  }

  const canvas = await html2canvas(element, {
    scale: 2,
    useCORS: true,
    logging: false,
  });

  const imgData = canvas.toDataURL('image/png');
  const doc = new jsPDF();

  const pageWidth = doc.internal.pageSize.getWidth();
  const pageHeight = doc.internal.pageSize.getHeight();

  if (title) {
    doc.setFontSize(16);
    doc.setFont('helvetica', 'bold');
    doc.text(title, 20, 20);
  }

  // Calculate image dimensions to fit page
  const imgWidth = pageWidth - 40;
  const imgHeight = (canvas.height * imgWidth) / canvas.width;

  // Check if image needs multiple pages
  const startY = title ? 30 : 20;
  const currentY = startY;

  if (imgHeight + startY > pageHeight - 20) {
    // Image is too tall, scale it down
    const scaledHeight = pageHeight - startY - 20;
    const scaledWidth = (canvas.width * scaledHeight) / canvas.height;
    const xOffset = (pageWidth - scaledWidth) / 2;
    doc.addImage(imgData, 'PNG', xOffset, currentY, scaledWidth, scaledHeight);
  } else {
    const xOffset = (pageWidth - imgWidth) / 2;
    doc.addImage(imgData, 'PNG', xOffset, currentY, imgWidth, imgHeight);
  }

  const dateSuffix = includeDate ? `-${new Date().toISOString().split('T')[0]}` : '';
  doc.save(`${filename}${dateSuffix}.pdf`);
}
