'use client';

import { useState, useEffect, useCallback } from 'react';
import { Plus, Loader2, AlertCircle, FileText, RefreshCw } from 'lucide-react';
import { getDocuments, getExpiringDocuments } from '@/lib/api';
import type { Document, DocumentListResponse, ExpiringDocumentsResponse } from '@/lib/types';
import { DocumentUpload } from '@/components/documents/document-upload';
import { DocumentList } from '@/components/documents/document-list';

export default function DocumentsPage() {
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

  const fetchDocuments = useCallback(async (pageNum: number = 1, append: boolean = false) => {
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
      setError(err instanceof Error ? err.message : 'Failed to load documents');
    } finally {
      setLoading(false);
      setLoadingMore(false);
    }
  }, []);

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
        <p className="text-muted-foreground">Loading documents...</p>
      </div>
    );
  }

  // Error state
  if (error && documents.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] text-center">
        <AlertCircle className="h-12 w-12 text-destructive mb-4" />
        <h2 className="text-xl font-semibold mb-2">Failed to Load Documents</h2>
        <p className="text-muted-foreground mb-4">{error}</p>
        <button
          onClick={handleRefresh}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-md bg-primary text-primary-foreground hover:bg-primary/90"
        >
          <RefreshCw className="h-4 w-4" />
          Try Again
        </button>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">Documents</h1>
          <p className="text-muted-foreground mt-1">
            Manage your property documents, contracts, and reports
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={handleRefresh}
            disabled={loading}
            className="inline-flex items-center gap-2 px-3 py-2 rounded-md border border-input hover:bg-muted disabled:opacity-50"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
          <button
            onClick={() => setShowUpload(true)}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-md bg-primary text-primary-foreground hover:bg-primary/90"
          >
            <Plus className="h-4 w-4" />
            Upload Document
          </button>
        </div>
      </div>

      {/* Expiring Documents Alert */}
      {expiringDocuments.length > 0 && (
        <div className="mb-6 p-4 rounded-lg bg-yellow-50 border border-yellow-200">
          <div className="flex items-start gap-3">
            <AlertCircle className="h-5 w-5 text-yellow-600 flex-shrink-0 mt-0.5" />
            <div>
              <h3 className="font-medium text-yellow-800">
                {expiringDocuments.length} document{expiringDocuments.length > 1 ? 's' : ''}{' '}
                expiring soon
              </h3>
              <p className="text-sm text-yellow-700 mt-1">
                The following documents will expire within 30 days:
                {expiringDocuments.slice(0, 3).map((doc, idx) => (
                  <span key={doc.id}>
                    {idx > 0 && ', '}
                    &nbsp;{doc.original_filename}
                  </span>
                ))}
                {expiringDocuments.length > 3 && (
                  <span> and {expiringDocuments.length - 3} more</span>
                )}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Upload Modal */}
      {showUpload && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="bg-background rounded-lg shadow-lg w-full max-w-lg mx-4 max-h-[90vh] overflow-y-auto">
            <div className="p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold">Upload Document</h2>
                <button
                  onClick={() => setShowUpload(false)}
                  className="p-1 hover:bg-muted rounded text-xl"
                >
                  ×
                </button>
              </div>
              <DocumentUpload
                onUploadSuccess={handleUploadSuccess}
                onCancel={() => setShowUpload(false)}
              />
            </div>
          </div>
        </div>
      )}

      {/* Empty State */}
      {documents.length === 0 && !loading && (
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <FileText className="h-20 w-20 text-muted-foreground/20 mb-6" />
          <h2 className="text-xl font-semibold mb-2">No documents yet</h2>
          <p className="text-muted-foreground mb-6 max-w-md">
            Upload your first document to start organizing your property-related files. Support for
            PDF, DOC, DOCX, JPG, and PNG files up to 10MB.
          </p>
          <button
            onClick={() => setShowUpload(true)}
            className="inline-flex items-center gap-2 px-6 py-3 rounded-md bg-primary text-primary-foreground hover:bg-primary/90"
          >
            <Plus className="h-5 w-5" />
            Upload Your First Document
          </button>
        </div>
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
                onClick={handleLoadMore}
                disabled={loadingMore}
                className="inline-flex items-center gap-2 px-6 py-2 rounded-md border border-input hover:bg-muted disabled:opacity-50"
              >
                {loadingMore ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Loading...
                  </>
                ) : (
                  <>
                    Load More ({page}/{totalPages})
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
