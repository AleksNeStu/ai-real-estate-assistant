'use client';

import { useCallback, useState } from 'react';
import { Upload, X, FileText, Loader2, CheckCircle, AlertCircle } from 'lucide-react';
import { uploadDocument } from '@/lib/api';
import type { DocumentUploadResponse, DocumentCategory } from '@/lib/types';

interface DocumentUploadProps {
  propertyId?: string;
  onUploadSuccess?: (document: DocumentUploadResponse) => void;
  onCancel?: () => void;
}

const ACCEPTED_TYPES = '.pdf,.doc,.docx,.jpg,.jpeg,.png';
const MAX_SIZE_MB = 10;

const CATEGORIES: { value: DocumentCategory | ''; label: string }[] = [
  { value: '', label: 'Select category (optional)' },
  { value: 'contract', label: 'Contract' },
  { value: 'inspection', label: 'Inspection Report' },
  { value: 'photo', label: 'Photo' },
  { value: 'financial', label: 'Financial Document' },
  { value: 'other', label: 'Other' },
];

export function DocumentUpload({ propertyId, onUploadSuccess, onCancel }: DocumentUploadProps) {
  const [file, setFile] = useState<File | null>(null);
  const [category, setCategory] = useState<string>('');
  const [description, setDescription] = useState('');
  const [tags, setTags] = useState('');
  const [expiryDate, setExpiryDate] = useState('');
  const [uploading, setUploading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);

  const validateFile = useCallback((file: File): string | null => {
    const ext = '.' + file.name.split('.').pop()?.toLowerCase();
    const validExts = ACCEPTED_TYPES.split(',');
    if (!validExts.includes(ext)) {
      return `Invalid file type: ${ext}. Allowed: ${ACCEPTED_TYPES}`;
    }
    if (file.size > MAX_SIZE_MB * 1024 * 1024) {
      return `File too large. Maximum size: ${MAX_SIZE_MB}MB`;
    }
    return null;
  }, []);

  const handleFileSelect = useCallback(
    (selectedFile: File) => {
      const validationError = validateFile(selectedFile);
      if (validationError) {
        setError(validationError);
        return;
      }
      setFile(selectedFile);
      setError(null);
    },
    [validateFile]
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);
      const droppedFile = e.dataTransfer.files[0];
      if (droppedFile) {
        handleFileSelect(droppedFile);
      }
    },
    [handleFileSelect]
  );

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback(() => {
    setIsDragging(false);
  }, []);

  const handleUpload = async () => {
    if (!file) return;

    setUploading(true);
    setError(null);

    try {
      const response = await uploadDocument(file, {
        property_id: propertyId,
        category: category || undefined,
        tags: tags
          ? tags
              .split(',')
              .map((t) => t.trim())
              .filter(Boolean)
          : undefined,
        description: description || undefined,
        expiry_date: expiryDate || undefined,
      });

      setSuccess(true);
      setTimeout(() => {
        onUploadSuccess?.(response);
      }, 1500);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  if (success) {
    return (
      <div className="flex flex-col items-center justify-center py-8 text-center">
        <CheckCircle className="h-12 w-12 text-success mb-4" />
        <h3 className="text-lg font-semibold">Upload Successful!</h3>
        <p className="text-sm text-muted-foreground mt-1">{file?.name}</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Drag-drop zone */}
      <div
        className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors cursor-pointer ${
          isDragging
            ? 'border-primary bg-primary/5'
            : file
              ? 'border-success bg-success/10'
              : 'border-muted-foreground/25 hover:border-primary/50'
        }`}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onClick={() => document.getElementById('file-input')?.click()}
      >
        <input
          id="file-input"
          type="file"
          accept={ACCEPTED_TYPES}
          className="hidden"
          onChange={(e) => e.target.files?.[0] && handleFileSelect(e.target.files[0])}
        />

        {file ? (
          <div className="flex items-center justify-center gap-3">
            <FileText className="h-8 w-8 text-success" />
            <div className="text-left">
              <p className="font-medium">{file.name}</p>
              <p className="text-sm text-muted-foreground">
                {(file.size / 1024 / 1024).toFixed(2)} MB
              </p>
            </div>
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                setFile(null);
              }}
              className="ml-2 p-1 hover:bg-muted rounded"
              aria-label="Remove selected file"
            >
              <X className="h-4 w-4" aria-hidden="true" />
            </button>
          </div>
        ) : (
          <>
            <Upload className="h-10 w-10 mx-auto mb-3 text-muted-foreground" aria-hidden="true" />
            <p className="font-medium">Drag & drop a file here</p>
            <p className="text-sm text-muted-foreground mt-1">or click to browse</p>
            <p className="text-xs text-muted-foreground mt-2">
              Supports: PDF, DOC, DOCX, JPG, PNG (max {MAX_SIZE_MB}MB)
            </p>
          </>
        )}
      </div>

      {/* Metadata fields */}
      <div className="grid gap-4">
        <div>
          <label htmlFor="doc-category" className="text-sm font-medium">
            Category
          </label>
          <select
            id="doc-category"
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
          >
            {CATEGORIES.map((cat) => (
              <option key={cat.value} value={cat.value}>
                {cat.label}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label htmlFor="doc-description" className="text-sm font-medium">
            Description
          </label>
          <textarea
            id="doc-description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Optional description..."
            rows={2}
            className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
          />
        </div>

        <div>
          <label htmlFor="doc-tags" className="text-sm font-medium">
            Tags
          </label>
          <input
            id="doc-tags"
            type="text"
            value={tags}
            onChange={(e) => setTags(e.target.value)}
            placeholder="contract, urgent, reviewed (comma-separated)"
            className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
          />
        </div>

        <div>
          <label htmlFor="doc-expiry" className="text-sm font-medium">
            Expiry Date
          </label>
          <input
            id="doc-expiry"
            type="date"
            value={expiryDate}
            onChange={(e) => setExpiryDate(e.target.value)}
            className="mt-1 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
          />
        </div>
      </div>

      {/* Error display */}
      {error && (
        <div
          className="flex items-start gap-3 p-4 rounded-lg bg-destructive/10 border border-destructive/20"
          role="alert"
        >
          <AlertCircle className="w-5 h-5 text-destructive flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-medium text-destructive">Upload Failed</p>
            <p className="text-sm text-destructive/90">{error}</p>
          </div>
        </div>
      )}

      {/* Actions */}
      <div className="flex justify-end gap-2 pt-2">
        {onCancel && (
          <button
            type="button"
            onClick={onCancel}
            disabled={uploading}
            className="px-4 py-2 text-sm font-medium rounded-md border border-input hover:bg-muted disabled:opacity-50 focus-visible:outline-none focus-visible:outline-2 focus-visible:outline-ring/50"
          >
            Cancel
          </button>
        )}
        <button
          type="button"
          onClick={handleUpload}
          disabled={!file || uploading}
          className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-md bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50 focus-visible:outline-none focus-visible:outline-2 focus-visible:outline-ring/50"
        >
          {uploading ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" />
              Uploading...
            </>
          ) : (
            <>
              <Upload className="w-4 h-4" aria-hidden="true" />
              Upload Document
            </>
          )}
        </button>
      </div>
    </div>
  );
}
