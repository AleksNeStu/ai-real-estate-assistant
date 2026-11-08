'use client';

import React from 'react';
import { Bot, RefreshCw } from 'lucide-react';
import { useTranslations } from 'next-intl';

interface ChatErrorFallbackProps {
  error?: Error | null;
  onRetry?: () => void;
}

/**
 * Chat-specific error fallback component (Task #68).
 * Shows a friendly error message with retry option for chat failures.
 */
export function ChatErrorFallback({ error, onRetry }: ChatErrorFallbackProps) {
  const t = useTranslations('error');
  return (
    <div
      className="flex flex-col items-center justify-center p-8 text-center border rounded-lg bg-muted/50"
      role="alert"
    >
      <Bot className="h-10 w-10 text-muted-foreground mb-3" aria-hidden="true" />
      <h3 className="text-base font-semibold mb-1">{t('chatUnavailable')}</h3>
      <p className="text-sm text-muted-foreground mb-4 max-w-sm">
        {error?.message || t('chatErrorFallback')}
      </p>
      {onRetry && (
        <button type="button"
          onClick={onRetry}
          className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors focus-visible:outline-none focus-visible:outline-2 focus-visible:outline-ring/50"
        >
          <RefreshCw className="h-4 w-4" aria-hidden="true" />
          {t('retry')}
        </button>
      )}
    </div>
  );
}
