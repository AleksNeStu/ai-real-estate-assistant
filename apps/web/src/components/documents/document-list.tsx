'use client';

import { useEffect, useMemo, useState } from 'react';
import {
  FileText,
  Download,
  Trash2,
  Calendar,
  Tag,
  Building,
  AlertTriangle,
  MoreVertical,
  FileImage,
  File,
  Clock,
  Search,
} from 'lucide-react';
import { useLocale, useTranslations } from 'next-intl';
import type { Document as DocumentType, DocumentCategory } from '@/lib/types';
import { deleteDocument, getDocumentDownloadUrl } from '@/lib/api';

interface DocumentListProps {
  documents: DocumentType[];
  onDocumentDeleted?: (documentId: string) => void;
  onDocumentUpdated?: (document: DocumentType) => void;
}

const FILE_TYPE_ICONS: Record<string, React.ReactNode> = {
  'application/pdf': <FileText className="h-8 w-8 text-destructive" aria-hidden="true" />,
  'application/msword': <File className="h-8 w-8 text-info" aria-hidden="true" />,
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document': (
    <File className="h-8 w-8 text-info" aria-hidden="true" />
  ),
  'image/jpeg': <FileImage className="h-8 w-8 text-success" aria-hidden="true" />,
  'image/jpg': <FileImage className="h-8 w-8 text-success" aria-hidden="true" />,
  'image/png': <FileImage className="h-8 w-8 text-success" aria-hidden="true" />,
};

function getFileIcon(fileType: string): React.ReactNode {
  return (
    FILE_TYPE_ICONS[fileType] || (
      <File className="h-8 w-8 text-muted-foreground" aria-hidden="true" />
    )
  );
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

function isExpiringSoon(expiryDate?: string): boolean {
  if (!expiryDate) return false;
  const expiry = new Date(expiryDate);
  const now = new Date();
  const daysUntilExpiry = (expiry.getTime() - now.getTime()) / (1000 * 60 * 60 * 24);
  return daysUntilExpiry > 0 && daysUntilExpiry <= 30;
}

function isExpired(expiryDate?: string): boolean {
  if (!expiryDate) return false;
  return new Date(expiryDate) < new Date();
}

export function DocumentList({
  documents,
  onDocumentDeleted,
  onDocumentUpdated: _onDocumentUpdated,
}: DocumentListProps) {
  const [deleting, setDeleting] = useState<string | null>(null);
  const [showMenu, setShowMenu] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [categoryFilter, setCategoryFilter] = useState<DocumentCategory | ''>('');
  const [sortBy, setSortBy] = useState<'date' | 'name' | 'size'>('date');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');

  const t = useTranslations('documents');
  const locale = useLocale();

  const categoryLabels: Record<DocumentCategory, string> = {
    contract: t('categories.contract'),
    inspection: t('categories.inspection'),
    photo: t('categories.photo'),
    financial: t('categories.financial'),
    other: t('categories.other'),
  };

  const relativeFormatter = useMemo(
    () => new Intl.RelativeTimeFormat(locale, { numeric: 'auto' }),
    [locale]
  );

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
    if (Math.abs(diffMinutes) < 60) return relativeFormatter.format(diffMinutes, 'minute');
    const diffHours = Math.round(diffMinutes / 60);
    if (Math.abs(diffHours) < 24) return relativeFormatter.format(diffHours, 'hour');
    return relativeFormatter.format(Math.round(diffHours / 24), 'day');
  };

  const handleDownload = async (doc: DocumentType) => {
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
    if (!confirm(t('list.deleteConfirm', { name: doc.original_filename }))) {
      return;
    }

    setDeleting(doc.id);
    try {
      await deleteDocument(doc.id);
      onDocumentDeleted?.(doc.id);
    } catch (error) {
      console.error(t('errors.deleteFailed'), error);
      alert(t('errors.deleteFailed'));
    } finally {
      setDeleting(null);
      setShowMenu(null);
    }
  };

  // Filter and sort documents
  const filteredDocuments = documents
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
    });

  if (documents.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center">
        <FileText className="h-16 w-16 text-muted-foreground/30 mb-4" aria-hidden="true" />
        <h3 className="text-lg font-medium text-muted-foreground">{t('emptyState.title')}</h3>
        <p className="text-sm text-muted-foreground/70 mt-1">{t('emptyState.description')}</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex flex-wrap gap-3 items-center">
        <div className="relative flex-1 min-w-[200px]">
          <Search
            className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground"
            aria-hidden="true"
          />
          <input
            type="text"
            placeholder={t('list.searchPlaceholder')}
            aria-label={t('searchLabel')}
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 rounded-md border border-input bg-background text-sm"
          />
        </div>

        <select
          aria-label={t('list.filterByCategory')}
          value={categoryFilter}
          onChange={(e) => setCategoryFilter(e.target.value as DocumentCategory | '')}
          className="rounded-md border border-input bg-background px-3 py-2 text-sm"
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
          className="rounded-md border border-input bg-background px-3 py-2 text-sm"
        >
          <option value="date">{t('list.sortByDate')}</option>
          <option value="name">{t('list.sortByName')}</option>
          <option value="size">{t('list.sortBySize')}</option>
        </select>

        <button
          type="button"
          onClick={() => setSortOrder((prev) => (prev === 'asc' ? 'desc' : 'asc'))}
          className="px-3 py-2 rounded-md border border-input bg-background text-sm hover:bg-muted"
          aria-label={t('list.sortOrder', {
            order: sortOrder === 'asc' ? t('list.ascending') : t('list.descending'),
          })}
        >
          {sortOrder === 'asc' ? `↑ ${t('list.ascending')}` : `↓ ${t('list.descending')}`}
        </button>
      </div>

      {/* Document Grid */}
      {filteredDocuments.length === 0 ? (
        <div className="text-center py-8 text-muted-foreground">
          <p>{t('list.noResults')}</p>
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {filteredDocuments.map((doc) => {
            const expired = isExpired(doc.expiry_date);
            const expiringSoon = isExpiringSoon(doc.expiry_date);

            return (
              <div
                key={doc.id}
                className={`relative rounded-lg border bg-card p-4 transition-shadow hover:shadow-md ${
                  expired ? 'border-destructive/40 bg-destructive/10/50' : ''
                }`}
              >
                {/* Expiry Badge */}
                {(expired || expiringSoon) && (
                  <div
                    className={`absolute top-2 right-2 flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${
                      expired ? 'bg-destructive/15 text-destructive' : 'bg-warning/15 text-warning'
                    }`}
                  >
                    <AlertTriangle className="h-3 w-3" aria-hidden="true" />
                    {expired ? t('list.expired') : t('list.expiringSoon')}
                  </div>
                )}

                {/* File Icon & Name */}
                <div className="flex items-start gap-3 mb-3">
                  {getFileIcon(doc.file_type)}
                  <div className="flex-1 min-w-0 pr-8">
                    <p className="font-medium truncate" title={doc.original_filename}>
                      {doc.original_filename}
                    </p>
                    <p className="text-sm text-muted-foreground">{formatFileSize(doc.file_size)}</p>
                  </div>
                </div>

                {/* Metadata */}
                <div className="space-y-2 text-sm text-muted-foreground mb-3">
                  {doc.category && (
                    <div className="flex items-center gap-2">
                      <Tag className="h-4 w-4" aria-hidden="true" />
                      <span>{categoryLabels[doc.category]}</span>
                    </div>
                  )}

                  {doc.property_id && (
                    <div className="flex items-center gap-2">
                      <Building className="h-4 w-4" aria-hidden="true" />
                      <span className="truncate">
                        {t('list.property', { id: doc.property_id })}
                      </span>
                    </div>
                  )}

                  {doc.expiry_date && (
                    <div className="flex items-center gap-2">
                      <Calendar className="h-4 w-4" aria-hidden="true" />
                      <span>
                        {t('list.expires')}: {new Date(doc.expiry_date).toLocaleDateString(locale)}
                      </span>
                    </div>
                  )}

                  <div className="flex items-center gap-2">
                    <Clock className="h-4 w-4" aria-hidden="true" />
                    <span>
                      {t('list.added')} {formatRelative(doc.created_at)}
                    </span>
                  </div>
                </div>

                {/* Tags */}
                {doc.tags && doc.tags.length > 0 && (
                  <div className="flex flex-wrap gap-1 mb-3">
                    {doc.tags.map((tag, idx) => (
                      <span
                        key={idx}
                        className="px-2 py-0.5 bg-muted rounded text-xs text-muted-foreground"
                      >
                        {tag}
                      </span>
                    ))}
                  </div>
                )}

                {/* Description */}
                {doc.description && (
                  <p className="text-sm text-muted-foreground line-clamp-2 mb-3">
                    {doc.description}
                  </p>
                )}

                {/* Actions */}
                <div className="flex items-center justify-between pt-2 border-t">
                  <button
                    type="button"
                    onClick={() => handleDownload(doc)}
                    className="inline-flex items-center gap-1 px-3 py-1.5 text-sm rounded-md hover:bg-muted transition-colors"
                  >
                    <Download className="h-4 w-4" aria-hidden="true" />
                    {t('list.download')}
                  </button>

                  <div className="relative">
                    <button
                      type="button"
                      onClick={() => setShowMenu(showMenu === doc.id ? null : doc.id)}
                      className="p-1.5 rounded-md hover:bg-muted"
                      aria-label={t('list.actionsFor', { name: doc.original_filename })}
                      aria-expanded={showMenu === doc.id}
                    >
                      <MoreVertical className="h-4 w-4" aria-hidden="true" />
                    </button>

                    {showMenu === doc.id && (
                      <>
                        {/* The overlay only closes the menu for the mouse. */}
                        <div
                          className="fixed inset-0 z-10"
                          onClick={() => setShowMenu(null)}
                          aria-hidden="true"
                        />
                        <div className="absolute right-0 bottom-full mb-1 z-20 w-40 rounded-md border bg-popover shadow-lg">
                          <button
                            type="button"
                            onClick={() => handleDelete(doc)}
                            disabled={deleting === doc.id}
                            className="flex items-center gap-2 w-full px-3 py-2 text-sm text-destructive hover:bg-destructive/10 rounded-md disabled:opacity-50"
                          >
                            <Trash2 className="h-4 w-4" aria-hidden="true" />
                            {deleting === doc.id ? t('list.deleting') : t('list.delete')}
                          </button>
                        </div>
                      </>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
