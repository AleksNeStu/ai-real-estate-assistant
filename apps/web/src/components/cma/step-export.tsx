'use client';

import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { downloadCMAPdf } from '@/lib/api';
import type { CMAReport } from '@/lib/types';

interface StepExportProps {
  report: CMAReport | null;
  onReset: () => void;
  onPrev: () => void;
}

export function StepExport({ report, onReset, onPrev }: StepExportProps) {
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
      const message = err instanceof Error ? err.message : 'Failed to download PDF';
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
      <div className="space-y-4">
        <div className="text-center py-8 text-muted-foreground">
          No report available. Please go back and generate a report first.
        </div>
        <div className="flex justify-start">
          <Button variant="outline" onClick={onPrev}>
            Back
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Success message */}
      <div className="text-center py-4">
        <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-success/15 mb-4">
          <svg
            className="w-8 h-8 text-success"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
            aria-hidden="true"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
        </div>
        <h3 className="text-lg font-semibold">Report Generated Successfully</h3>
        <p className="text-sm text-muted-foreground mt-1">
          Your Comparative Market Analysis report is ready for export.
        </p>
      </div>

      {/* Export options */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* PDF Download */}
        <div className="border rounded-lg p-4 hover:bg-muted/30 transition-colors">
          <div className="flex items-center gap-3 mb-3">
            <div className="p-2 bg-destructive/15 rounded">
              <svg
                className="w-5 h-5 text-destructive"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
                aria-hidden="true"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 0H8a1 1 0 00-1 1v6.586a1 1 0 01.707.293l5.414 5.414a1 1 0 00.707.293H15a2 2 0 002-2z"
                />
              </svg>
            </div>
            <div>
              <h4 className="font-medium text-sm">PDF Report</h4>
              <p className="text-xs text-muted-foreground">Professional format</p>
            </div>
          </div>
          <Button className="w-full" onClick={handleDownloadPdf} disabled={isDownloading}>
            {isDownloading ? 'Downloading...' : 'Download PDF'}
          </Button>
        </div>

        {/* JSON Download */}
        <div className="border rounded-lg p-4 hover:bg-muted/30 transition-colors">
          <div className="flex items-center gap-3 mb-3">
            <div className="p-2 bg-info/15 rounded">
              <svg
                className="w-5 h-5 text-info"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
                aria-hidden="true"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4"
                />
              </svg>
            </div>
            <div>
              <h4 className="font-medium text-sm">JSON Data</h4>
              <p className="text-xs text-muted-foreground">Raw data export</p>
            </div>
          </div>
          <Button className="w-full" onClick={handleDownloadJson}>
            Download JSON
          </Button>
        </div>

        {/* Share Link */}
        <div className="border rounded-lg p-4 hover:bg-muted/30 transition-colors">
          <div className="flex items-center gap-3 mb-3">
            <div className="p-2 bg-success/15 rounded">
              <svg
                className="w-5 h-5 text-success"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
                aria-hidden="true"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M8.684 13.342C8.886 12.938 9 12 9 12c0 .482.114.954.316 1.342m1.652-2.17C10.157 10.482 10 9.5 10 9c0-.482-.114-.954-.316-1.342m1.652 2.17zM10 8a4 4 0 11-4 4 4 4 0 01-4-4 4 4 0 014-4zm7.657 2.342C17.886 12.938 18 12 18 12c0-.482-.114-.954-.316-1.342m-1.652 2.17c.202.388.316.86.316 1.342 0 .482-.114.954-.316 1.342m1.652-2.17zM14 8a4 4 0 11-4 4 4 4 0 01-4-4 4 4 0 014-4zm-7.316 5.658C6.886 14.938 6 14.5 6 14.5c0 .482.114.954.316 1.342m-1.652-2.17C4.157 12.982 4 12.5 4 12c0-.482.114-.954.316-1.342m1.652 2.17z"
                />
              </svg>
            </div>
            <div>
              <h4 className="font-medium text-sm">Share Link</h4>
              <p className="text-xs text-muted-foreground">Copy shareable URL</p>
            </div>
          </div>
          <Button className="w-full" variant="outline" onClick={handleCopyLink}>
            {copiedLink ? 'Copied!' : 'Copy Link'}
          </Button>
        </div>
      </div>

      {/* Download error */}
      {downloadError && (
        <div className="text-sm text-destructive bg-destructive/10 px-4 py-3 rounded" role="alert">
          {downloadError}
        </div>
      )}

      {/* Report info */}
      <div className="text-sm text-muted-foreground bg-muted/30 rounded p-3">
        <p>
          Report ID: <span className="font-mono">{report.id}</span>
        </p>
        <p className="mt-1">
          Created: {new Date(report.created_at).toLocaleString()}
          {report.expires_at && (
            <span> • Expires: {new Date(report.expires_at).toLocaleString()}</span>
          )}
        </p>
      </div>

      {/* Navigation */}
      <div className="flex justify-between pt-4">
        <Button variant="outline" onClick={onPrev}>
          Back
        </Button>
        <Button onClick={onReset}>Create New Report</Button>
      </div>
    </div>
  );
}
