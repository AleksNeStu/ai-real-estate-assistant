'use client';

import { useState, useEffect, useCallback } from 'react';
import { Download } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { Button } from '@/components/ui/button';

interface InstallPromptProps {
  className?: string;
}

/**
 * Install Prompt Component
 * Shows a prompt to install the PWA when the app is installable
 */
export function InstallPrompt({ className }: InstallPromptProps) {
  const [showPrompt, setShowPrompt] = useState(false);
  const [isInstalling, setIsInstalling] = useState(false);
  const t = useTranslations('designStates');
  const tCommon = useTranslations('common');

  useEffect(() => {
    // Check if already installed
    if (window.matchMedia?.('(display-mode: standalone)')) {
      return;
    }

    // Check if prompt was dismissed before
    const dismissed = localStorage.getItem('pwa-install-dismissed');
    if (dismissed) {
      return;
    }

    // Listen for install availability
    const handleInstallAvailable = () => {
      setShowPrompt(true);
    };

    window.addEventListener('pwa-install-available', handleInstallAvailable);

    // Check if already available
    if ('BeforeInstallPromptEvent' in window) {
      setShowPrompt(true);
    }

    return () => {
      window.removeEventListener('pwa-install-available', handleInstallAvailable);
    };
  }, []);

  const handleInstall = useCallback(async () => {
    setIsInstalling(true);
    try {
      const { promptPWAInstall } = await import('@/lib/sw');
      const accepted = await promptPWAInstall();
      if (accepted) {
        setShowPrompt(false);
      }
    } catch (error) {
      console.error('Install failed:', error);
    } finally {
      setIsInstalling(false);
    }
  }, []);

  const handleLater = useCallback(() => {
    setShowPrompt(false);
  }, []);

  if (!showPrompt) {
    return null;
  }

  return (
    <div
      className={`fixed bottom-4 left-4 right-4 z-50 mx-4 overflow-hidden rounded-lg border border-border bg-popover shadow-[0_8px_24px_rgb(9_9_11/0.10)] ${className || ''}`}
      role="status"
    >
      <div className="flex items-start gap-3 p-4">
        <div className="flex-shrink-0">
          <div className="flex size-9 items-center justify-center rounded-md bg-muted">
            <Download className="size-4 text-foreground" aria-hidden="true" />
          </div>
        </div>
        <div className="flex-1">
          <p className="text-[14px] font-semibold leading-5 text-foreground">{t('install.title')}</p>
          <p className="text-[13px] leading-5 text-muted-foreground">{t('install.body')}</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="sm" onClick={handleLater} className="text-muted-foreground">
            {t('install.notNow')}
          </Button>
          <Button size="sm" onClick={handleInstall} disabled={isInstalling}>
            {isInstalling ? tCommon('installing') : t('install.install')}
          </Button>
        </div>
      </div>
    </div>
  );
}
