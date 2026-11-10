'use client';

import { Suspense, useEffect, useReducer } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { useLocale, useTranslations } from 'next-intl';
import { Loader2, ArrowLeft } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { AuthCard, AuthHeading, AuthLinks, AuthNote, AuthStatus } from '@/components/auth/auth-shell';
import { useCapabilities } from '@/hooks/useCapabilities';
import { verifyEmail } from '@/lib/auth';

type State = {
  status: 'loading' | 'success' | 'error';
  error: string | null;
};

type Action = { type: 'SUCCESS' } | { type: 'ERROR'; error: string };

function reducer(_state: State, action: Action): State {
  switch (action.type) {
    case 'SUCCESS':
      return { status: 'success', error: null };
    case 'ERROR':
      return { status: 'error', error: action.error };
    default:
      return _state;
  }
}

function VerifyEmailContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const locale = useLocale();
  const t = useTranslations('auth');
  const { capabilities } = useCapabilities();

  // The deployment that cannot send mail cannot promise a mail. The
  // capabilities endpoint knows, so the heading follows it: the page says
  // the link was sent only when a mail was actually sent.
  const emailEnabled = capabilities?.email?.enabled ?? true;

  // Get token and derive initial validation state
  const token = searchParams.get('token');
  const hasValidToken = Boolean(token);

  // Use reducer to avoid setState in effect
  const [state, dispatch] = useReducer(reducer, {
    status: hasValidToken ? 'loading' : 'error',
    error: hasValidToken ? null : t('verifyEmail.invalidToken'),
  });

  // Only make API call if we have a valid token
  useEffect(() => {
    if (!token) {
      return;
    }

    let cancelled = false;

    verifyEmail(token)
      .then(() => {
        if (!cancelled) {
          dispatch({ type: 'SUCCESS' });
        }
      })
      .catch((err) => {
        if (!cancelled) {
          dispatch({
            type: 'ERROR',
            error: err instanceof Error ? err.message : t('verifyEmail.failed'),
          });
        }
      });

    return () => {
      cancelled = true;
    };
  }, [token, t]);

  if (state.status === 'loading') {
    return (
      <AuthCard>
        <AuthHeading
          title={t('verifyEmail.title')}
          description={emailEnabled ? t('verifyEmail.description') : t('verifyEmail.noMailNote')}
        />
        <div className="flex items-center gap-2.5 py-4 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
          <span>{t('verifyEmail.verifying')}</span>
        </div>
        <AuthNote>{t('note')}</AuthNote>
      </AuthCard>
    );
  }

  if (state.status === 'success') {
    return (
      <AuthCard>
        <AuthHeading title={t('verifyEmail.verified')} />
        <AuthStatus tone="success">{t('verifyEmail.verifiedDescription')}</AuthStatus>
        <p className="text-sm text-muted-foreground">{t('verifyEmail.canLogin')}</p>
        <Button className="w-full" onClick={() => router.push(`/${locale}/auth/login`)}>
          {t('verifyEmail.goToLogin')}
        </Button>
        <AuthNote>{t('note')}</AuthNote>
      </AuthCard>
    );
  }

  return (
    <AuthCard>
      <AuthHeading title={t('verifyEmail.failedTitle')} />
      <AuthStatus tone="destructive">{state.error || t('verifyEmail.failedDescription')}</AuthStatus>
      <p className="text-sm text-muted-foreground">
        {emailEnabled ? t('verifyEmail.linkExpired') : t('verifyEmail.noMailNote')}
      </p>
      {emailEnabled && (
        <Button
          className="w-full"
          variant="outline"
          onClick={() => router.push(`/${locale}/auth/register`)}
        >
          {t('verifyEmail.requestNew')}
        </Button>
      )}
      <AuthLinks>
        <Link
          href={`/${locale}/auth/login`}
          className="inline-flex items-center gap-1 font-medium text-foreground underline underline-offset-4 hover:text-primary"
        >
          <ArrowLeft className="h-3 w-3" aria-hidden="true" />
          {t('verifyEmail.backToLogin')}
        </Link>
      </AuthLinks>
      <AuthNote>{t('note')}</AuthNote>
    </AuthCard>
  );
}

export default function VerifyEmailPage() {
  const t = useTranslations('auth');

  return (
    <Suspense
      fallback={
        <AuthCard>
          <div className="flex items-center gap-2.5 py-4 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
            <span>{t('verifyEmail.loading')}</span>
          </div>
        </AuthCard>
      }
    >
      <VerifyEmailContent />
    </Suspense>
  );
}
