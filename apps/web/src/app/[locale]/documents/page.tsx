'use client';

import { useState, useEffect, useCallback } from 'react';
import { Plus, Loader2, FileText, RefreshCw } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { getDocuments, getExpiringDocuments } from '@/lib/api';
import type { Document, DocumentListResponse, ExpiringDocumentsResponse } from '@/lib/types';
import { DocumentUpload } from '@/components/documents/document-upload';
import { DocumentList } from '@/components/documents/document-list';
import { Button } from '@/components/ui/button';
import { MonoAnnotation } from '@/components/ui/mono-annotation';
import { EmptyState, ErrorState } from '@/components/ui/states';
import { Modal } from '@/components/ui/modal';
import { PageHeader } from '@/components/ui/page-header';

/**
 * The document vault.
 *
 * The route is the prototype's arrangement: the count of what the vault
 * holds, the two tabs - everything, and what expires soon - and the ledger
 * of the files under them. The tab that asks for attention carries the count
 * the API gave for it, so the badge is never a number of its own.
 *
 * A file is a row of a table, not a card: the name, the property it belongs
 * to, its size and the day it expires.
 */

type VaultTab = 'all' | 'expiring';

export default function DocumentsPage() {
  const t = useTranslations('pages.documents');
  const tCommon = useTranslations('common');
  const tDocsErrors = useTranslations('documents.errors');
  const [documents, setDocuments] = useState<Document[]>([]);
  const [expiringDocuments, setExpiringDocuments] = useState<Document[]>([]);
  const [expiringTotal, setExpiringTotal] = useState(0);
  const [total, setTotal] = useState(0);
  const [tab, setTab] = useState<VaultTab>('all');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showUpload, setShowUpload] = useState(false);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [loadingMore, setLoadingMore] = useState(false);

  const fetchExpiringDocuments = useCallback(async () => {
    try {
      const response: ExpiringDocumentsResponse = await getExpiringDocuments(30);
      setExpiringDocuments(response.items);
      setExpiringTotal(response.total);
    } catch {
      // Silently fail - expiring docs are optional enhancement
    }
  }, []);

  const fetchDocuments = useCallback(
    async (pageNum: number = 1, append: boolean = false) => {
      try {
        if (append) {
          setLoadingMore(true);
        } else {
          setLoading(true);
          setError(null);
        }

        const response: DocumentListResponse = await getDocuments({
          page: pageNum,
          page_size: 20,
          sort_by: 'created_at',
          sort_order: 'desc',
        });

        if (append) {
          setDocuments((prev) => [...prev, ...response.items]);
        } else {
          setDocuments(response.items);
        }
        setTotal(response.total);
        setTotalPages(response.total_pages);
        setPage(pageNum);
      } catch (err) {
        setError(err instanceof Error ? err.message : tDocsErrors('loadFailed'));
      } finally {
        setLoading(false);
        setLoadingMore(false);
      }
    },
    [tDocsErrors]
  );

  useEffect(() => {
    fetchDocuments(1);
    fetchExpiringDocuments();
  }, [fetchDocuments, fetchExpiringDocuments]);

  const handleUploadSuccess = () => {
    setShowUpload(false);
    fetchDocuments(1);
    fetchExpiringDocuments();
  };

  const handleDocumentDeleted = (documentId: string) => {
    setDocuments((prev) => prev.filter((doc) => doc.id !== documentId));
    setExpiringDocuments((prev) => prev.filter((doc) => doc.id !== documentId));
  };

  const handleDocumentUpdated = (updatedDoc: Document) => {
    setDocuments((prev) => prev.map((doc) => (doc.id === updatedDoc.id ? updatedDoc : doc)));
  };

  const handleLoadMore = () => {
    if (page < totalPages && !loadingMore) {
      fetchDocuments(page + 1, true);
    }
  };

  const handleRefresh = () => {
    fetchDocuments(1);
    fetchExpiringDocuments();
  };

  // Loading state
  if (loading && documents.length === 0) {
    return (
      <div className="flex min-h-[400px] flex-col items-center justify-center">
        <Loader2 className="mb-4 h-8 w-8 animate-spin text-muted-foreground" aria-hidden="true" />
        <p className="m-0 text-[14px] text-muted-foreground">{t('loading')}</p>
      </div>
    );
  }

  // Error state
  if (error && documents.length === 0) {
    return (
      <div className="mx-auto max-w-[1100px] px-6 py-8">
        <ErrorState
          title={t('errorTitle')}
          description={error}
          onRetry={handleRefresh}
          retryLabel={tCommon('tryAgain')}
        />
      </div>
    );
  }

  const listed = tab === 'all' ? documents : expiringDocuments;

  const tabClass = (active: boolean) =>
    [
      'inline-flex items-center gap-1.5 border-0 border-b-2 bg-transparent px-0 pb-2 pt-1 text-[14px] leading-5 transition-colors focus-visible:outline-none focus-visible:outline-2 focus-visible:outline-ring/50',
      active
        ? 'border-foreground font-medium text-foreground'
        : 'border-transparent text-muted-foreground hover:text-foreground',
    ].join(' ');

  return (
    <div className="flex min-h-[calc(100vh-56px)] flex-col">
      <div className="border-b border-border px-6 pb-5 pt-6">
        <PageHeader
          title={t('title')}
          description={<MonoAnnotation>{t('vaultCount', { count: total })}</MonoAnnotation>}
          actions={
            <>
              <Button
                type="button"
                variant="outline"
                onClick={handleRefresh}
                disabled={loading}
                aria-label={t('refresh')}
                className="h-9 w-9 px-0"
              >
                <RefreshCw
                  className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`}
                  aria-hidden="true"
                />
              </Button>
              <Button type="button" onClick={() => setShowUpload(true)} className="h-9">
                <Plus className="mr-2 h-4 w-4" aria-hidden="true" />
                {t('upload')}
              </Button>
            </>
          }
        />
      </div>

      {/* The tabs of the vault. */}
      <div className="px-6 pt-4">
        <div className="flex gap-5 border-b border-border" role="tablist">
          <button
            type="button"
            role="tab"
            aria-selected={tab === 'all'}
            onClick={() => setTab('all')}
            className={tabClass(tab === 'all')}
          >
            {t('tabAll')}
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={tab === 'expiring'}
            onClick={() => setTab('expiring')}
            className={tabClass(tab === 'expiring')}
          >
            {t('tabExpiring')}
            <span className="rounded-full bg-warning-surface px-1.5 py-px font-mono text-[11px] leading-4 text-warning">
              {expiringTotal}
            </span>
          </button>
        </div>
      </div>

      <main className="px-6 py-5">
        {listed.length === 0 && !loading ? (
          <EmptyState
            icon={FileText}
            title={t('emptyTitle')}
            description={t('emptyDescription')}
            action={
              <Button type="button" onClick={() => setShowUpload(true)}>
                <Plus className="mr-2 h-4 w-4" aria-hidden="true" />
                {t('uploadFirst')}
              </Button>
            }
          />
        ) : (
          <>
            <DocumentList
              documents={listed}
              onDocumentDeleted={handleDocumentDeleted}
              onDocumentUpdated={handleDocumentUpdated}
            />

            {page < totalPages ? (
              <div className="mt-5 flex items-center justify-between gap-4">
                <MonoAnnotation>{t('page', { page, total: totalPages })}</MonoAnnotation>
                <Button
                  type="button"
                  variant="outline"
                  onClick={handleLoadMore}
                  disabled={loadingMore}
                  className="h-9"
                >
                  {loadingMore ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />
                      {tCommon('loading')}
                    </>
                  ) : (
                    t('loadMore')
                  )}
                </Button>
              </div>
            ) : null}
          </>
        )}
      </main>

      {/* Upload Modal */}
      <Modal
        open={showUpload}
        onClose={() => setShowUpload(false)}
        title={t('upload')}
        closeLabel={tCommon('close')}
      >
        <DocumentUpload
          onUploadSuccess={handleUploadSuccess}
          onCancel={() => setShowUpload(false)}
        />
      </Modal>
    </div>
  );
}
