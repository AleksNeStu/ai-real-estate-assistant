'use client';

import { useCallback, useEffect, useState } from 'react';
import { Download } from 'lucide-react';
import { useLocale, useTranslations } from 'next-intl';
import { Button } from '@/components/ui/button';
import { isMaintained } from '@/i18n/policy';
import { canInstallPWA, promptPWAInstall } from '@/lib/sw';
import { cn } from '@/lib/utils';

/**
 * The install button of the header.
 *
 * The browser fires `beforeinstallprompt` when it can install the app and
 * stays silent when it cannot - a browser inside another app, a browser
 * without the manifest, a browser that already installed it. The button
 * therefore appears only where the install would work: a button that offers
 * an install the browser refuses is worse than no button.
 *
 * The button is offered in the maintained pair of languages only. The other
 * seven catalogues are frozen, and a new surface does not land in them.
 */
export function InstallButton({ className }: { className?: string }) {
  const locale = useLocale();
  const t = useTranslations('shell');
  const [available, setAvailable] = useState(false);

  useEffect(() => {
    if (!isMaintained(locale)) {
      return;
    }

    // The browser may have offered the install before this button mounted.
    if (canInstallPWA()) {
      setAvailable(true);
    }

    const handleAvailable = () => setAvailable(true);
    const handleInstalled = () => setAvailable(false);

    window.addEventListener('pwa-install-available', handleAvailable);
    window.addEventListener('pwa-installed', handleInstalled);

    return () => {
      window.removeEventListener('pwa-install-available', handleAvailable);
      window.removeEventListener('pwa-installed', handleInstalled);
    };
  }, [locale]);

  const install = useCallback(async () => {
    const accepted = await promptPWAInstall();
    if (accepted) {
      setAvailable(false);
    }
  }, []);

  if (!isMaintained(locale) || !available) {
    return null;
  }

  return (
    <Button
      type="button"
      variant="outline"
      size="sm"
      onClick={install}
      className={cn('h-8 gap-1.5 px-3 text-[13px]', className)}
    >
      <Download className="size-[15px]" aria-hidden="true" />
      {t('install')}
    </Button>
  );
}
