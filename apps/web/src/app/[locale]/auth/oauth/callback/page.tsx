'use client';

import { Suspense, useEffect, useMemo } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { Loader2 } from 'lucide-react';
import { useTranslations } from 'next-intl';

import { AuthCard, AuthHeading, AuthNote, AuthStatus } from '@/components/auth/auth-shell';

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
    <AuthCard>
      <AuthHeading title={t('oauth.signingIn')} description={t('oauth.pleaseWait')} />
      <AuthStatus tone={status === 'success' ? 'success' : 'destructive'}>{message}</AuthStatus>
      {status === 'error' && (
        <p className="text-sm text-muted-foreground">{t('oauth.redirecting')}</p>
      )}
      <AuthNote>{t('note')}</AuthNote>
    </AuthCard>
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
    <Suspense
      fallback={
        <AuthCard>
          <AuthHeading title={t('oauth.signingIn')} description={t('oauth.pleaseWait')} />
          <div className="flex items-center gap-2.5 py-4 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
            <span>{t('oauth.pleaseWait')}</span>
          </div>
        </AuthCard>
      }
    >
      <OAuthCallbackContent />
    </Suspense>
  );
}
