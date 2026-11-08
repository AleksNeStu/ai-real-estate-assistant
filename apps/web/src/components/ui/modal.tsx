'use client';

import * as React from 'react';
import { X } from 'lucide-react';

import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';

/**
 * The one modal in the product.
 *
 * The overlays it replaces were hand-rolled `fixed inset-0` divs: they had no
 * Escape handling, no focus trap, no focus restore and no `aria-modal`, so a
 * keyboard user could tab straight out of the dialog into the page behind it.
 *
 * This one is built on the native `<dialog>` element, so the browser provides
 * the top layer, the focus trap and the Escape key. The only thing left to do
 * is to keep the React state and the native open state in sync.
 */
export interface ModalProps {
  open: boolean;
  onClose: () => void;
  title: React.ReactNode;
  description?: React.ReactNode;
  children?: React.ReactNode;
  footer?: React.ReactNode;
  /** Accessible name of the close button. */
  closeLabel?: string;
  className?: string;
}

export function Modal({
  open,
  onClose,
  title,
  description,
  children,
  footer,
  closeLabel = 'Close',
  className,
}: ModalProps) {
  const dialogRef = React.useRef<HTMLDialogElement | null>(null);

  React.useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;
    // jsdom (and very old browsers) do not implement the modal dialog API.
    // Without this fallback the dialog would never open there.
    if (typeof dialog.showModal !== 'function') {
      if (open) dialog.setAttribute('open', '');
      else dialog.removeAttribute('open');
      return;
    }
    if (open && !dialog.open) {
      dialog.showModal();
    } else if (!open && dialog.open) {
      dialog.close();
    }
  }, [open]);

  return (
    <dialog
      ref={dialogRef}
      onCancel={(event) => {
        // Escape is handled by the browser; the state has to follow it.
        event.preventDefault();
        onClose();
      }}
      onClose={onClose}
      onClick={(event) => {
        // A click on the backdrop lands on the dialog element itself.
        if (event.target === dialogRef.current) onClose();
      }}
      className={cn(
        'fixed inset-0 m-auto h-fit max-h-[90vh] w-full max-w-md overflow-y-auto',
        'border bg-background p-0 text-foreground shadow-lg',
        'backdrop:bg-black/50 backdrop:backdrop-blur-sm',
        'open:animate-in open:fade-in-0 open:zoom-in-95',
        className
      )}
    >
      {/* The content is only mounted while the dialog is open: a closed
          dialog must not put its title and its fields into the accessibility
          tree of the page behind it. */}
      {open ? (
        <>
          <div className="flex items-start justify-between gap-4 border-b p-6">
            <div className="space-y-1">
              <h2 className="text-lg font-semibold tracking-tight">{title}</h2>
              {description ? (
                <p className="text-sm text-muted-foreground">{description}</p>
              ) : null}
            </div>
            <Button
              type="button"
              variant="ghost"
              size="icon"
              onClick={onClose}
              aria-label={closeLabel}
              className="-mr-2 -mt-2 shrink-0"
            >
              <X className="size-5" aria-hidden="true" />
            </Button>
          </div>

          <div className="p-6">{children}</div>

          {footer ? (
            <div className="flex flex-wrap items-center justify-end gap-2 border-t p-6">
              {footer}
            </div>
          ) : null}
        </>
      ) : null}
    </dialog>
  );
}
