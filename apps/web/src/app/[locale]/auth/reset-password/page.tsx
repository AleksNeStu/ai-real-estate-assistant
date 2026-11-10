'use client';

import { Suspense, useState, useEffect } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { useLocale, useTranslations } from 'next-intl';
import { Loader2, ArrowLeft } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { AuthCard, AuthField, AuthHeading, AuthLinks, AuthNote, AuthStatus } from '@/components/auth/auth-shell';
import { resetPassword } from '@/lib/auth';

function ResetPasswordForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const locale = useLocale();
  const t = useTranslations('auth');
  const [isLoading, setIsLoading] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');

  // Get token from URL
  useEffect(() => {
    const tokenParam = searchParams.get('token');
    if (!tokenParam) {
      setError(t('resetPassword.invalidToken'));
    } else {
      setToken(tokenParam);
    }
  }, [searchParams, t]);

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!token) {
      setError(t('resetPassword.invalidToken'));
      return;
    }

    if (password !== confirmPassword) {
      setError(t('errors.passwordMismatch'));
      return;
    }

    // Password validation
    if (password.length < 8) {
      setError(t('errors.weakPassword'));
      return;
    }
    if (!/[A-Z]/.test(password)) {
      setError(t('errors.uppercaseRequired'));
      return;
    }
    if (!/[a-z]/.test(password)) {
      setError(t('errors.lowercaseRequired'));
      return;
    }
    if (!/\d/.test(password)) {
      setError(t('errors.digitRequired'));
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      await resetPassword(token, password);
      setIsSuccess(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : t('errors.resetFailed'));
    } finally {
      setIsLoading(false);
    }
  }

  if (isSuccess) {
    return (
      <AuthCard>
        <AuthHeading title={t('resetPassword.successTitle')} />
        <AuthStatus tone="success">{t('resetPassword.success')}</AuthStatus>
        <Button className="w-full" onClick={() => router.push(`/${locale}/auth/login`)}>
          {t('resetPassword.goToLogin')}
        </Button>
        <AuthNote>{t('note')}</AuthNote>
      </AuthCard>
    );
  }

  return (
    <AuthCard>
      <AuthHeading
        title={t('resetPassword.title')}
        description={t('resetPassword.description')}
      />
      <form onSubmit={onSubmit} className="flex flex-col gap-3">
        {error && (
          <div className="rounded-md bg-destructive/15 p-3 text-sm text-destructive" role="alert">
            {error}
          </div>
        )}
        <AuthField
          label={t('resetPassword.newPasswordLabel')}
          htmlFor="password"
          hint={t('resetPassword.passwordHint')}
        >
          <Input
            id="password"
            type="password"
            required
            disabled={isLoading || !token}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder={t('resetPassword.passwordHint')}
          />
        </AuthField>
        <AuthField
          label={t('resetPassword.confirmPasswordLabel')}
          htmlFor="confirmPassword"
          hint={t('resetPassword.confirmHint')}
        >
          <Input
            id="confirmPassword"
            type="password"
            required
            disabled={isLoading || !token}
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            placeholder={t('resetPassword.confirmHint')}
          />
        </AuthField>
        <Button
          className="mt-1 w-full"
          type="submit"
          disabled={isLoading || !token || !password || !confirmPassword}
        >
          {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
          {t('resetPassword.submit')}
        </Button>
      </form>
      <AuthLinks>
        <Link
          href={`/${locale}/auth/login`}
          className="inline-flex items-center gap-1 font-medium text-foreground underline underline-offset-4 hover:text-primary"
        >
          <ArrowLeft className="h-3 w-3" aria-hidden="true" />
          {t('forgotPassword.backToLogin')}
        </Link>
      </AuthLinks>
      <AuthNote>{t('note')}</AuthNote>
    </AuthCard>
  );
}

export default function ResetPasswordPage() {
  return (
    <Suspense
      fallback={
        <AuthCard>
          <div className="flex justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        </AuthCard>
      }
    >
      <ResetPasswordForm />
    </Suspense>
  );
}
