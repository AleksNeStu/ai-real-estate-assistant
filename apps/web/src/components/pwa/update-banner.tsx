'use client';

import { useState, useEffect } from 'react';
import { RefreshCw, X } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

interface UpdateBannerProps {
  className?: string;
}

/**
 * Update Banner Component
 * Shows when a new version of the service worker is available
 */
export function UpdateBanner({ className }: UpdateBannerProps) {
  const [showBanner, setShowBanner] = useState(false);
  const t = useTranslations('designStates');
  const tCommon = useTranslations('common');

  useEffect(() => {
    const handleUpdateAvailable = () => {
      setShowBanner(true);
    };

    window.addEventListener('sw-update-available', handleUpdateAvailable);

    return () => {
      window.removeEventListener('sw-update-available', handleUpdateAvailable);
    };
  }, []);

  const handleUpdate = () => {
    window.location.reload();
  };

  const handleDismiss = () => {
    setShowBanner(false);
  };

  if (!showBanner) {
    return null;
  }

  return (
    <div
      className={cn(
        'fixed top-0 left-0 right-0 z-50 border-b border-border bg-muted px-4 py-2.5 text-center text-[13px] leading-5 text-foreground transition-all',
        className
      )}
      role="status"
      aria-live="polite"
    >
      <div className="mx-auto flex max-w-[1248px] items-center justify-center gap-3">
        <RefreshCw className="h-4 w-4 shrink-0 text-muted-foreground" aria-hidden="true" />
        <span>{t('update.title')}</span>
        <Button variant="outline" size="sm" onClick={handleUpdate}>
          {t('update.reload')}
        </Button>
        <Button
          variant="ghost"
          size="sm"
          onClick={handleDismiss}
          className="text-muted-foreground hover:text-foreground"
          aria-label={tCommon('dismissUpdate')}
        >
          <X className="h-4 w-4" aria-hidden="true" />
        </Button>
      </div>
    </div>
  );
}
