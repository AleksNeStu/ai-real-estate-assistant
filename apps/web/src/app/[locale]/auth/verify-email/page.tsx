'use client';

import { Suspense, useEffect, useReducer } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { useTranslations } from 'next-intl';
import { Loader2, CheckCircle2, XCircle, ArrowLeft } from 'lucide-react';

import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
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
  const t = useTranslations('auth');

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
  }, [token]);

  if (state.status === 'loading') {
    return (
      <Card className="w-full">
        <CardContent className="flex flex-col items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
          <p className="mt-4 text-sm text-muted-foreground">{t('verifyEmail.verifying')}</p>
        </CardContent>
      </Card>
    );
  }

  if (state.status === 'success') {
    return (
      <Card className="w-full">
        <CardHeader className="space-y-1 text-center">
          <div className="flex justify-center mb-2">
            <div className="rounded-full bg-success/15 dark:bg-success/20 p-3">
              <CheckCircle2 className="h-6 w-6 text-success dark:text-success" />
            </div>
          </div>
          <CardTitle className="text-2xl">{t('verifyEmail.verified')}</CardTitle>
          <CardDescription>{t('verifyEmail.verifiedDescription')}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-center text-muted-foreground">{t('verifyEmail.canLogin')}</p>
        </CardContent>
        <CardFooter className="flex flex-col gap-4">
          <Button className="w-full" onClick={() => router.push('/auth/login')}>
            {t('verifyEmail.goToLogin')}
          </Button>
        </CardFooter>
      </Card>
    );
  }

  return (
    <Card className="w-full">
      <CardHeader className="space-y-1 text-center">
        <div className="flex justify-center mb-2">
          <div className="rounded-full bg-destructive/15 p-3">
            <XCircle className="h-6 w-6 text-destructive" />
          </div>
        </div>
        <CardTitle className="text-2xl">{t('verifyEmail.failedTitle')}</CardTitle>
        <CardDescription>{state.error || t('verifyEmail.failedDescription')}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm text-center text-muted-foreground">{t('verifyEmail.linkExpired')}</p>
      </CardContent>
      <CardFooter className="flex flex-col gap-4">
        <Button className="w-full" variant="outline" onClick={() => router.push('/auth/register')}>
          {t('verifyEmail.requestNew')}
        </Button>
        <div className="text-sm text-center text-muted-foreground">
          <Link
            href="/auth/login"
            className="inline-flex items-center gap-1 text-primary hover:underline"
          >
            <ArrowLeft className="h-3 w-3" />
            {t('verifyEmail.backToLogin')}
          </Link>
        </div>
      </CardFooter>
    </Card>
  );
}

export default function VerifyEmailPage() {
  const t = useTranslations('auth');

  return (
    <Suspense
      fallback={
        <Card className="w-full">
          <CardContent className="flex flex-col items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
            <p className="mt-4 text-sm text-muted-foreground">{t('verifyEmail.loading')}</p>
          </CardContent>
        </Card>
      }
    >
      <VerifyEmailContent />
    </Suspense>
  );
}
