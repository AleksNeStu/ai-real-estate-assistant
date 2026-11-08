'use client';

import { AlertTriangle, RefreshCw, Home } from 'lucide-react';
import Link from 'next/link';
import { NextIntlClientProvider, useTranslations } from 'next-intl';
import messages from '../../messages/en.json';

/**
 * Next.js App Router error boundary (Task #68).
 * Catches runtime errors in any page and shows a fallback UI.
 *
 * This boundary sits above the `[locale]` segment, so it renders outside the
 * intl provider of the locale layout — and it has to keep working when the
 * provider itself is the thing that broke. The copy therefore comes from the
 * catalogue, but through a provider of its own: the fallback must never
 * depend on the part of the app that just failed.
 */
function ErrorFallback({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  const t = useTranslations('error');
  const tCommon = useTranslations('common');
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] p-8 text-center">
      <AlertTriangle className="h-16 w-16 text-destructive mb-6" />
      <h1 className="text-2xl font-bold mb-2">{t('generic')}</h1>
      <p className="text-muted-foreground mb-2 max-w-md">
        {error.message || t('unexpectedError')}
      </p>
      {error.digest && (
        <p className="text-xs text-muted-foreground mb-6">
          {t('errorId', { id: error.digest })}
        </p>
      )}
      <div className="flex gap-3">
        <button type="button"
          onClick={reset}
          className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors focus-visible:outline-none focus-visible:outline-2 focus-visible:outline-ring/50"
        >
          <RefreshCw className="h-4 w-4" />
          {tCommon('tryAgain')}
        </button>
        <Link
          href="/"
          className="inline-flex items-center gap-2 rounded-md border border-input bg-background px-4 py-2 text-sm font-medium hover:bg-accent transition-colors"
        >
          <Home className="h-4 w-4" />
          {t('goHome')}
        </Link>
      </div>
    </div>
  );
}

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <NextIntlClientProvider locale="en" messages={messages}>
      <ErrorFallback error={error} reset={reset} />
    </NextIntlClientProvider>
  );
}
