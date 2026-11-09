'use client';

import { useEffect, useMemo, useState } from 'react';
import { Download, Search, Trash2 } from 'lucide-react';
import { useLocale, useTranslations } from 'next-intl';
import type { Document as DocumentType, DocumentCategory } from '@/lib/types';
import { deleteDocument, getDocumentDownloadUrl } from '@/lib/api';
import { MonoAnnotation } from '@/components/ui/mono-annotation';

/**
 * The vault as a ledger of files.
 *
 * The design draws a list of files as rows under a rule, not as a grid of
 * cards: a file is a row of a vault, and the vault is a table of what it
 * holds. The columns are the prototype's - name, property, size, expiry -
 * and the row carries the details the API returned: the category, the tags,
 * the description and when it was added.
 *
 * The expiry is the column that asks for attention, so a file that expires
 * within thirty days says so in amber, with the days it has left. The days
 * are counted from the expiry date the API carries - nothing is guessed.
 *
 * The delete asks twice: the first press turns the button into a
 * confirmation, the second one removes the file. A confirmation that costs
 * one click and no dialog is a confirmation people still read.
 */

interface DocumentListProps {
  documents: DocumentType[];
  onDocumentDeleted?: (documentId: string) => void;
  onDocumentUpdated?: (document: DocumentType) => void;
}

const EXPIRY_WINDOW_DAYS = 30;

const CONTROL_CLASS =
  'h-9 w-full rounded-md border border-input bg-background px-2.5 text-[13px] text-foreground';

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

/**
 * The days left until the expiry, or null when the file does not expire.
 *
 * A file that has already expired gets a negative number of days left, and
 * the caller writes it as expired rather than as "in -3 days".
 */
function daysUntil(expiryDate?: string, now: number): number | null {
  if (!expiryDate) return null;
  const expiry = new Date(expiryDate).getTime();
  if (!Number.isFinite(expiry)) return null;
  return Math.ceil((expiry - now) / (1000 * 60 * 60 * 24));
}

export function DocumentList({
  documents,
  onDocumentDeleted,
  onDocumentUpdated: _onDocumentUpdated,
}: DocumentListProps) {
  const t = useTranslations('documents');
  const tPages = useTranslations('pages.documents');
  const locale = useLocale();

  const [deleting, setDeleting] = useState<string | null>(null);
  const [confirming, setConfirming] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [categoryFilter, setCategoryFilter] = useState<DocumentCategory | ''>('');
  const [sortBy, setSortBy] = useState<'date' | 'name' | 'size'>('date');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');

  const categoryLabels: Record<DocumentCategory, string> = {
    contract: t('categories.contract'),
    inspection: t('categories.inspection'),
    photo: t('categories.photo'),
    financial: t('categories.financial'),
    other: t('categories.other'),
  };

  // The reference point lives in state so that rendering stays pure.
  const [now, setNow] = useState<number | null>(null);

  useEffect(() => {
    const update = () => setNow(Date.now());
    update();
    const interval = setInterval(update, 60000);
    return () => clearInterval(interval);
  }, []);

  const formatRelative = (date: string): string => {
    if (now === null) return new Date(date).toLocaleDateString(locale);
    const diffMinutes = Math.round((new Date(date).getTime() - now) / 60000);
    const diffHours = Math.round(diffMinutes / 60);
    const diffDays = Math.round(diffHours / 24);
    if (Math.abs(diffMinutes) < 60) return `${Math.abs(diffMinutes)} min`;
    if (Math.abs(diffHours) < 24) return `${Math.abs(diffHours)} h`;
    return `${Math.abs(diffDays)} d`;
  };

  const handleDownload = (doc: DocumentType) => {
    try {
      const url = getDocumentDownloadUrl(doc.id);
      const link = document.createElement('a');
      link.href = url;
      link.download = doc.original_filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } catch (error) {
      console.error(t('errors.downloadFailed'), error);
    }
  };

  const handleDelete = async (doc: DocumentType) => {
    // The first press asks; the second one removes.
    if (confirming !== doc.id) {
      setConfirming(doc.id);
      return;
    }

    setDeleting(doc.id);
    try {
      await deleteDocument(doc.id);
      onDocumentDeleted?.(doc.id);
    } catch (error) {
      console.error(t('errors.deleteFailed'), error);
    } finally {
      setDeleting(null);
      setConfirming(null);
    }
  };

  const filteredDocuments = useMemo(
    () =>
      documents
        .filter((doc) => {
          if (searchQuery) {
            const query = searchQuery.toLowerCase();
            const matchesName = doc.original_filename.toLowerCase().includes(query);
            const matchesDesc = doc.description?.toLowerCase().includes(query);
            if (!matchesName && !matchesDesc) return false;
          }
          if (categoryFilter && doc.category !== categoryFilter) {
            return false;
          }
          return true;
        })
        .sort((a, b) => {
          let comparison = 0;
          switch (sortBy) {
            case 'date':
              comparison = new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
              break;
            case 'name':
              comparison = a.original_filename.localeCompare(b.original_filename);
              break;
            case 'size':
              comparison = a.file_size - b.file_size;
              break;
          }
          return sortOrder === 'asc' ? comparison : -comparison;
        }),
    [documents, searchQuery, categoryFilter, sortBy, sortOrder]
  );

  if (documents.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center">
        <p className="m-0 text-[15px] font-semibold text-foreground">{t('emptyState.title')}</p>
        <p className="mt-1 text-[14px] text-muted-foreground">{t('emptyState.description')}</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* The controls of the vault. */}
      <div className="flex flex-wrap items-center gap-2">
        <div className="relative min-w-[200px] flex-1">
          <Search
            className="absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"
            aria-hidden="true"
          />
          <input
            type="text"
            placeholder={t('list.searchPlaceholder')}
            aria-label={t('searchLabel')}
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className={`${CONTROL_CLASS} pl-8`}
          />
        </div>

        <select
          aria-label={t('list.filterByCategory')}
          value={categoryFilter}
          onChange={(e) => setCategoryFilter(e.target.value as DocumentCategory | '')}
          className={`${CONTROL_CLASS} w-auto`}
        >
          <option value="">{t('categories.allCategories')}</option>
          {Object.entries(categoryLabels).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>

        <select
          aria-label={t('list.sortBy')}
          value={sortBy}
          onChange={(e) => setSortBy(e.target.value as 'date' | 'name' | 'size')}
          className={`${CONTROL_CLASS} w-auto`}
        >
          <option value="date">{t('list.sortByDate')}</option>
          <option value="name">{t('list.sortByName')}</option>
          <option value="size">{t('list.sortBySize')}</option>
        </select>

        <button
          type="button"
          onClick={() => setSortOrder((prev) => (prev === 'asc' ? 'desc' : 'asc'))}
          className={`${CONTROL_CLASS} w-auto`}
          aria-label={t('list.sortOrder', {
            order: sortOrder === 'asc' ? t('list.ascending') : t('list.descending'),
          })}
        >
          {sortOrder === 'asc' ? `↑ ${t('list.ascending')}` : `↓ ${t('list.descending')}`}
        </button>
      </div>

      {filteredDocuments.length === 0 ? (
        <p className="m-0 border-t border-foreground py-6 text-[14px] text-muted-foreground">
          {t('list.noResults')}
        </p>
      ) : (
        <div data-testid="document-list">
          {/* The header of the ledger. */}
          <div className="hidden grid-cols-[minmax(0,1.6fr)_1.2fr_90px_120px_70px] gap-4 border-b border-foreground pb-2 text-[12px] leading-4 text-muted-foreground sm:grid">
            <span>{tPages('columns.name')}</span>
            <span>{tPages('columns.property')}</span>
            <span>{tPages('columns.size')}</span>
            <span>{tPages('columns.expires')}</span>
            <span />
          </div>

          {filteredDocuments.map((doc) => {
            const days = now === null ? null : daysUntil(doc.expiry_date, now);
            const expired = days !== null && days < 0;
            const expiringSoon = days !== null && days >= 0 && days <= EXPIRY_WINDOW_DAYS;
            const isConfirming = confirming === doc.id;

            return (
              <article
                key={doc.id}
                data-testid="document-card"
                className="grid grid-cols-2 gap-x-4 gap-y-1 border-b border-border py-[11px] sm:grid-cols-[minmax(0,1.6fr)_1.2fr_90px_120px_70px] sm:items-center"
              >
                <div className="col-span-2 min-w-0 sm:col-span-1">
                  <p className="m-0 truncate text-[14px] font-medium leading-5 text-foreground">
                    {doc.original_filename}
                  </p>
                  <p className="mt-0.5 truncate text-[12px] leading-4 text-muted-foreground">
                    {[
                      doc.category ? categoryLabels[doc.category] : null,
                      doc.description,
                      doc.tags && doc.tags.length > 0 ? doc.tags.join(', ') : null,
                      `${t('list.added')} ${formatRelative(doc.created_at)}`,
                    ]
                      .filter(Boolean)
                      .join(' · ')}
                  </p>
                </div>

                <div className="min-w-0 truncate text-[12px] leading-4 text-muted-foreground">
                  {doc.property_id ? (
                    <MonoAnnotation>{doc.property_id}</MonoAnnotation>
                  ) : (
                    <span className="text-muted-foreground">—</span>
                  )}
                </div>

                <div className="font-mono text-[13px] leading-5 text-foreground">
                  {formatFileSize(doc.file_size)}
                </div>

                <div
                  className={[
                    'font-mono text-[13px] leading-5',
                    expired
                      ? 'text-destructive'
                      : expiringSoon
                        ? 'text-warning'
                        : 'text-foreground',
                  ].join(' ')}
                >
                  {doc.expiry_date ? (
                    <>
                      {new Date(doc.expiry_date).toLocaleDateString(locale)}
                      {expiringSoon && days !== null ? ` · ${days} d` : ''}
                      {expired ? ` · ${t('list.expired')}` : ''}
                    </>
                  ) : (
                    '—'
                  )}
                </div>

                <div className="flex items-center justify-end gap-2">
                  <button
                    type="button"
                    onClick={() => handleDownload(doc)}
                    aria-label={`${t('list.download')} ${doc.original_filename}`}
                    className="inline-flex h-7 w-7 items-center justify-center rounded-md border-0 bg-transparent p-0 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:outline-2 focus-visible:outline-ring/50"
                  >
                    <Download className="h-3.5 w-3.5" aria-hidden="true" />
                  </button>

                  <button
                    type="button"
                    onClick={() => handleDelete(doc)}
                    disabled={deleting === doc.id}
                    aria-label={
                      isConfirming
                        ? `${t('list.confirmDelete')} ${doc.original_filename}`
                        : `${t('list.delete')} ${doc.original_filename}`
                    }
                    className={[
                      'inline-flex h-7 items-center justify-center rounded-md border-0 bg-transparent px-2 text-[12px] transition-colors disabled:opacity-50 focus-visible:outline-none focus-visible:outline-2 focus-visible:outline-ring/50',
                      isConfirming
                        ? 'bg-destructive/10 font-medium text-destructive'
                        : 'text-muted-foreground hover:bg-muted hover:text-foreground',
                    ].join(' ')}
                  >
                    {deleting === doc.id ? (
                      t('list.deleting')
                    ) : isConfirming ? (
                      t('list.confirmDelete')
                    ) : (
                      <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
                    )}
                  </button>
                </div>
              </article>
            );
          })}
        </div>
      )}
    </div>
  );
}
