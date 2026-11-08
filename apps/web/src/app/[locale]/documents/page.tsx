'use client';

import { useState, useEffect, useCallback } from 'react';
import { Plus, Loader2, AlertCircle, FileText, RefreshCw } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { getDocuments, getExpiringDocuments } from '@/lib/api';
import type { Document, DocumentListResponse, ExpiringDocumentsResponse } from '@/lib/types';
import { DocumentUpload } from '@/components/documents/document-upload';
import { DocumentList } from '@/components/documents/document-list';
import { Button } from '@/components/ui/button';
import { EmptyState } from '@/components/ui/states';
import { Modal } from '@/components/ui/modal';
import { PageHeader } from '@/components/ui/page-header';

export default function DocumentsPage() {
  const t = useTranslations('pages.documents');
  const tCommon = useTranslations('common');
  const tDocsErrors = useTranslations('documents.errors');
  const [documents, setDocuments] = useState<Document[]>([]);
  const [expiringDocuments, setExpiringDocuments] = useState<Document[]>([]);
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
      <div className="flex flex-col items-center justify-center min-h-[400px]">
        <Loader2 className="h-10 w-10 animate-spin text-primary mb-4" />
        <p className="text-muted-foreground">{t('loading')}</p>
      </div>
    );
  }

  // Error state
  if (error && documents.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] text-center">
        <AlertCircle className="h-12 w-12 text-destructive mb-4" />
        <h2 className="text-xl font-semibold mb-2">{t('errorTitle')}</h2>
        <p className="text-muted-foreground mb-4">{error}</p>
        <Button type="button" variant="outline" onClick={handleRefresh}>
          <RefreshCw className="h-4 w-4" aria-hidden="true" />
          {tCommon('tryAgain')}
        </Button>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8">
      {/* Header */}
      <PageHeader
        className="mb-6"
        title={t('title')}
        description={t('description')}
        actions={
          <>
            <Button type="button" variant="outline" onClick={handleRefresh} disabled={loading}>
              <RefreshCw
                className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`}
                aria-hidden="true"
              />
              {t('refresh')}
            </Button>
            <Button type="button" onClick={() => setShowUpload(true)}>
              <Plus className="h-4 w-4" aria-hidden="true" />
              {t('upload')}
            </Button>
          </>
        }
      />

      {/* Expiring Documents Alert */}
      {expiringDocuments.length > 0 && (
        <div className="mb-6 p-4 rounded-lg bg-warning/10 border border-warning/30">
          <div className="flex items-start gap-3">
            <AlertCircle className="h-5 w-5 text-warning flex-shrink-0 mt-0.5" />
            <div>
              <h3 className="font-medium text-warning">
                {t('expiringTitle', { count: expiringDocuments.length })}
              </h3>
              <p className="text-sm text-warning mt-1">
                {t('expiringIntro')}
                {expiringDocuments.slice(0, 3).map((doc, idx) => (
                  <span key={doc.id}>
                    {idx > 0 && ', '}
                    &nbsp;{doc.original_filename}
                  </span>
                ))}
                {expiringDocuments.length > 3 && (
                  <span> {t('andMore', { count: expiringDocuments.length - 3 })}</span>
                )}
              </p>
            </div>
          </div>
        </div>
      )}

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

      {/* Empty State */}
      {documents.length === 0 && !loading && (
        <EmptyState
          icon={FileText}
          title={t('emptyTitle')}
          description={t('emptyDescription')}
          action={
            <Button type="button" onClick={() => setShowUpload(true)}>
              <Plus className="h-5 w-5" aria-hidden="true" />
              {t('uploadFirst')}
            </Button>
          }
        />
      )}

      {/* Document List */}
      {documents.length > 0 && (
        <>
          <DocumentList
            documents={documents}
            onDocumentDeleted={handleDocumentDeleted}
            onDocumentUpdated={handleDocumentUpdated}
          />

          {/* Load More */}
          {page < totalPages && (
            <div className="flex justify-center mt-6">
              <button
                type="button"
                onClick={handleLoadMore}
                disabled={loadingMore}
                className="inline-flex items-center gap-2 px-6 py-2 rounded-md border border-input hover:bg-muted disabled:opacity-50 focus-visible:outline-none focus-visible:outline-2 focus-visible:outline-ring/50"
              >
                {loadingMore ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                    {tCommon('loading')}
                  </>
                ) : (
                  <>
                    {t('loadMore')} ({page}/{totalPages})
                  </>
                )}
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
