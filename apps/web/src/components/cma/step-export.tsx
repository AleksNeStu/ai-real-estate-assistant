'use client';

import React, { useState } from 'react';
import { useTranslations } from 'next-intl';
import { Button } from '@/components/ui/button';
import { MonoAnnotation } from '@/components/ui/mono-annotation';
import { downloadCMAPdf } from '@/lib/api';

import type { CMAReportResponse } from './report';

interface StepExportProps {
  report: CMAReportResponse | null;
  onReset: () => void;
}

/**
 * The export.
 *
 * The design draws it as a row of formats and one action. The report
 * leaves the browser as a PDF, as the raw JSON, or as a link the reader can
 * pass on - the three ways the API serves a report.
 */
export function StepExport({ report, onReset }: StepExportProps) {
  const t = useTranslations('cma.export');
  const [isDownloading, setIsDownloading] = useState(false);
  const [downloadError, setDownloadError] = useState<string | null>(null);
  const [copiedLink, setCopiedLink] = useState(false);

  const handleDownloadPdf = async () => {
    if (!report) return;

    setIsDownloading(true);
    setDownloadError(null);

    try {
      const blob = await downloadCMAPdf(report.id);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `cma-report-${report.id.slice(0, 8)}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      const message = err instanceof Error ? err.message : t('failedDownload');
      setDownloadError(message);
    } finally {
      setIsDownloading(false);
    }
  };

  const handleDownloadJson = () => {
    if (!report) return;

    const json = JSON.stringify(report, null, 2);
    const blob = new Blob([json], { type: 'application/json' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `cma-report-${report.id.slice(0, 8)}.json`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);
  };

  const handleCopyLink = async () => {
    if (!report) return;

    const shareUrl = `${window.location.origin}/cma/shared/${report.id}`;
    try {
      await navigator.clipboard.writeText(shareUrl);
      setCopiedLink(true);
      setTimeout(() => setCopiedLink(false), 2000);
    } catch {
      // Fallback for older browsers
      const textArea = document.createElement('textarea');
      textArea.value = shareUrl;
      document.body.appendChild(textArea);
      textArea.select();
      document.execCommand('copy');
      document.body.removeChild(textArea);
      setCopiedLink(true);
      setTimeout(() => setCopiedLink(false), 2000);
    }
  };

  if (!report) {
    return (
      <div className="flex flex-col gap-3">
        <p className="text-[14px] text-muted-foreground">{t('noReport')}</p>
        <Button onClick={onReset} variant="outline" className="self-start">
          {t('createNew')}
        </Button>
      </div>
    );
  }

  return (
    <div className="flex max-w-[560px] flex-col gap-4">
      <h3 className="text-[18px] font-semibold text-foreground">{t('title')}</h3>

      <div className="flex flex-wrap gap-2">
        <span className="rounded-md border border-foreground px-3 py-1.5 text-[13px] text-foreground">
          PDF
        </span>
        <span className="rounded-md border border-border px-3 py-1.5 text-[13px] text-muted-foreground">
          {t('withComparables')}
        </span>
        <span className="rounded-md border border-border px-3 py-1.5 text-[13px] text-muted-foreground">
          {t('withMap')}
        </span>
      </div>

      <div className="flex flex-col border-t border-foreground">
        <div className="grid grid-cols-[minmax(0,1fr)_auto] items-baseline gap-x-4 border-b border-border py-3">
          <span className="flex flex-col gap-0.5">
            <span className="text-[14px] font-medium text-foreground">{t('pdfReport')}</span>
            <span className="text-[12px] text-muted-foreground">{t('professionalFormat')}</span>
          </span>
          <Button onClick={handleDownloadPdf} disabled={isDownloading}>
            {isDownloading ? t('downloading') : t('downloadPdf')}
          </Button>
        </div>

        <div className="grid grid-cols-[minmax(0,1fr)_auto] items-baseline gap-x-4 border-b border-border py-3">
          <span className="flex flex-col gap-0.5">
            <span className="text-[14px] font-medium text-foreground">{t('jsonData')}</span>
            <span className="text-[12px] text-muted-foreground">{t('rawDataExport')}</span>
          </span>
          <Button variant="outline" onClick={handleDownloadJson}>
            {t('downloadJson')}
          </Button>
        </div>

        <div className="grid grid-cols-[minmax(0,1fr)_auto] items-baseline gap-x-4 border-b border-border py-3">
          <span className="flex flex-col gap-0.5">
            <span className="text-[14px] font-medium text-foreground">{t('shareLink')}</span>
            <span className="text-[12px] text-muted-foreground">{t('copyShareableUrl')}</span>
          </span>
          <Button variant="outline" onClick={handleCopyLink}>
            {copiedLink ? t('copied') : t('copyLink')}
          </Button>
        </div>
      </div>

      {downloadError ? (
        <p className="text-[14px] text-destructive" role="alert">
          {downloadError}
        </p>
      ) : null}

      <div className="flex flex-col gap-0.5 border-t border-foreground pt-2.5">
        <MonoAnnotation>
          {t('reportId')} {report.id}
        </MonoAnnotation>
        <MonoAnnotation>
          {t('created')} {new Date(report.created_at).toLocaleString()}
          {report.expires_at ? ` · ${t('expires')} ${new Date(report.expires_at).toLocaleString()}` : ''}
        </MonoAnnotation>
      </div>

      <Button onClick={onReset} variant="outline" className="self-start">
        {t('createNew')}
      </Button>
    </div>
  );
}
