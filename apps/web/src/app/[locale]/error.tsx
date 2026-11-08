'use client';

import { AlertTriangle, RefreshCw, Home } from 'lucide-react';
import Link from 'next/link';
import { useTranslations } from 'next-intl';

/**
 * Next.js App Router error boundary (Task #68).
 * Catches runtime errors in any page and shows a fallback UI.
 *
 * This copy lives in the [locale] segment so it can use the catalogue; the
 * root `app/error.tsx` stays in English because it renders outside the
 * intl provider, when even the provider itself may be the thing that broke.
 */
export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  const t = useTranslations('error');
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] p-8 text-center">
      <AlertTriangle className="h-16 w-16 text-destructive mb-6" />
      <h1 className="text-2xl font-bold mb-2">{t('generic')}</h1>
      <p className="text-muted-foreground mb-2 max-w-md">
        {error.message || t('unexpectedError')}
      </p>
      {error.digest && (
        <p className="text-xs text-muted-foreground mb-6">{t('errorId', { id: error.digest })}</p>
      )}
      <div className="flex gap-3">
        <button type="button"
          onClick={reset}
          className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors focus-visible:outline-none focus-visible:outline-2 focus-visible:outline-ring/50"
        >
          <RefreshCw className="w-4 h-4" />
          {t('retry')}
        </button>
        <Link
          href="/"
          className="inline-flex items-center gap-2 rounded-md border border-input bg-background px-4 py-2 text-sm font-medium hover:bg-accent transition-colors"
        >
          <Home className="w-4 h-4" />
          {t('goHome')}
        </Link>
      </div>
    </div>
  );
}
