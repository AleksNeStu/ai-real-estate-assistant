'use client';

import React from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';
import { useTranslations } from 'next-intl';

interface ErrorBoundaryProps {
  children: React.ReactNode;
  fallback?: React.ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

/**
 * The fallback UI. It lives in a function component of its own because the
 * boundary itself is a class — hooks cannot run inside a class, and the copy
 * has to come from the catalogue like the rest of the app.
 */
function ErrorFallback({ error, onRetry }: { error: Error | null; onRetry: () => void }) {
  const t = useTranslations('error');

  return (
    <div
      className="flex flex-col items-center justify-center min-h-[200px] p-8 text-center"
      role="alert"
    >
      <AlertTriangle className="h-12 w-12 text-destructive mb-4" aria-hidden="true" />
      <h2 className="text-lg font-semibold mb-2">{t('generic')}</h2>
      <p className="text-sm text-muted-foreground mb-4 max-w-md">
        {error?.message || t('unexpectedError')}
      </p>
      <button
        type="button"
        onClick={onRetry}
        className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors focus-visible:outline-none focus-visible:outline-2 focus-visible:outline-ring/50"
      >
        <RefreshCw className="h-4 w-4" aria-hidden="true" />
        {t('tryAgain')}
      </button>
    </div>
  );
}

/**
 * Generic React Error Boundary component (Task #68).
 * Catches rendering errors in children and displays a fallback UI
 * instead of crashing the entire app.
 */
export class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('[ErrorBoundary] Caught error:', error, errorInfo);
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return <ErrorFallback error={this.state.error} onRetry={this.handleRetry} />;
    }

    return this.props.children;
  }
}
