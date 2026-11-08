'use client';

import { AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import type { DataSource } from '@/lib/types';

interface DeleteConfirmDialogProps {
  source: DataSource | null;
  isOpen: boolean;
  onClose: () => void;
  onConfirm: (id: string) => void;
  isDeleting?: boolean;
}

export function DeleteConfirmDialog({
  source,
  isOpen,
  onClose,
  onConfirm,
  isDeleting = false,
}: DeleteConfirmDialogProps) {
  if (!isOpen || !source) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      role="dialog"
      aria-modal="true"
      aria-labelledby="delete-dialog-title"
    >
      {/* Backdrop */}
      {/* The backdrop only closes the dialog for the mouse — the cancel button and Escape serve the keyboard. */}
      <div className="absolute inset-0 bg-black/50" onClick={onClose} aria-hidden="true" />

      {/* Dialog */}
      <div className="relative bg-card rounded-lg shadow-lg p-6 w-full max-w-md mx-4">
        <div className="flex items-start gap-4">
          <div className="p-2 bg-destructive/10 rounded-full">
            <AlertCircle className="w-6 h-6 text-destructive" aria-hidden="true" />
          </div>
          <div className="flex-1">
            <h3 className="text-lg font-semibold mb-2" id="delete-dialog-title">
              Delete Data Source
            </h3>
            <p className="text-sm text-muted-foreground mb-4">
              Are you sure you want to delete <strong>{source.name}</strong>? This will also delete
              all sync history and cannot be undone.
            </p>
            <p className="text-xs text-muted-foreground mb-4">
              Records already imported from this source will remain in the system.
            </p>
          </div>
        </div>

        <div className="flex justify-end gap-2 mt-4">
          <Button variant="outline" onClick={onClose} disabled={isDeleting}>
            Cancel
          </Button>
          <Button variant="destructive" onClick={() => onConfirm(source.id)} disabled={isDeleting}>
            {isDeleting ? 'Deleting...' : 'Delete'}
          </Button>
        </div>
      </div>
    </div>
  );
}
