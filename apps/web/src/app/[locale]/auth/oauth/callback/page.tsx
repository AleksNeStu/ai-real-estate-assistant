'use client';

import { Suspense, useEffect, useMemo } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { Loader2, XCircle, CheckCircle2 } from 'lucide-react';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { useTranslations } from 'next-intl';

function OAuthCallbackContent() {
  const t = useTranslations('auth');
  const router = useRouter();
  const searchParams = useSearchParams();

  // Derive state from URL params directly (no setState in effect)
  const error = searchParams.get('error');
  const errorDescription = searchParams.get('error_description');

  const { status, message } = useMemo(() => {
    if (error) {
      return {
        status: 'error' as const,
        message: errorDescription || t('oauth.failed'),
      };
    }
    return {
      status: 'success' as const,
      message: t('oauth.success'),
    };
  }, [error, errorDescription, t]);

  // Handle redirects in effect (side effects, not state updates)
  useEffect(() => {
    const redirectTimer = setTimeout(
      () => {
        router.push(error ? '/auth/login' : '/');
      },
      error ? 3000 : 1000
    );

    return () => clearTimeout(redirectTimer);
  }, [error, router]);

  return (
    <Card className="w-full">
      <CardHeader className="space-y-1 text-center">
        <div className="flex justify-center mb-2">
          {status === 'success' && (
            <div className="rounded-full bg-success/15 dark:bg-success/20 p-3">
              <CheckCircle2 className="h-6 w-6 text-success dark:text-success" />
            </div>
          )}
          {status === 'error' && (
            <div className="rounded-full bg-destructive/15 p-3">
              <XCircle className="h-6 w-6 text-destructive" />
            </div>
          )}
        </div>
        <CardTitle className="text-2xl">
          {status === 'success' && t('oauth.welcome')}
          {status === 'error' && t('oauth.failed')}
        </CardTitle>
        <CardDescription>{message}</CardDescription>
      </CardHeader>
      <CardContent>
        {status === 'error' && (
          <p className="text-sm text-center text-muted-foreground">{t('oauth.redirecting')}</p>
        )}
      </CardContent>
    </Card>
  );
}

/**
 * OAuth Callback Page
 *
 * This page handles the OAuth callback from providers like Google and Apple.
 * The backend OAuth endpoint sets the auth cookies directly, so this page
 * just needs to wait for the redirect and then forward to the dashboard.
 */
export default function OAuthCallbackPage() {
  const t = useTranslations('auth');
  return (
    <div className="flex min-h-screen items-center justify-center bg-background">
      <Suspense
        fallback={
          <Card className="w-full">
            <CardHeader className="space-y-1 text-center">
              <div className="flex justify-center mb-2">
                <div className="rounded-full bg-primary/10 p-3">
                  <Loader2 className="h-6 w-6 animate-spin text-primary" />
                </div>
              </div>
              <CardTitle className="text-2xl">{t('oauth.signingIn')}</CardTitle>
              <CardDescription>{t('oauth.pleaseWait')}</CardDescription>
            </CardHeader>
          </Card>
        }
      >
        <OAuthCallbackContent />
      </Suspense>
    </div>
  );
}
