'use client';

import { Suspense, useState } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { useTranslations, useLocale } from 'next-intl';
import { Loader2, AlertCircle, Play } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { AuthCard, AuthField, AuthHeading, AuthLinks, AuthNote } from '@/components/auth/auth-shell';
import { OAuthButtons } from '@/components/auth/OAuthButtons';
import { login } from '@/lib/auth';
import { useAuth } from '@/hooks/useAuth';

function LoginForm({
  isLoading,
  error,
  onSubmit,
}: {
  isLoading: boolean;
  error: string | null;
  onSubmit: (event: React.FormEvent<HTMLFormElement>) => void;
}) {
  const t = useTranslations('auth.login');
  const locale = useLocale();

  return (
    <>
      <form onSubmit={onSubmit} className="flex flex-col gap-3">
        {error && (
          <div
            className="flex items-center gap-2 rounded-md bg-destructive/15 p-3 text-sm text-destructive"
            role="alert"
          >
            <AlertCircle className="h-4 w-4" aria-hidden="true" />
            <span>{error}</span>
          </div>
        )}
        <AuthField label={t('emailLabel')} htmlFor="email">
          <Input
            id="email"
            name="email"
            type="email"
            placeholder={t('emailPlaceholder')}
            required
            disabled={isLoading}
          />
        </AuthField>
        <AuthField
          label={t('passwordLabel')}
          htmlFor="password"
          hint={
            <Link
              href={`/${locale}/auth/forgot-password`}
              data-testid="auth-forgot-password"
              className="text-xs text-muted-foreground underline underline-offset-4 hover:text-foreground"
            >
              {t('forgotPassword')}
            </Link>
          }
        >
          <Input id="password" name="password" type="password" required disabled={isLoading} />
        </AuthField>
        <Button className="mt-1 h-[42px] w-full" type="submit" disabled={isLoading}>
          {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
          {t('submit')}
        </Button>
      </form>

      {process.env.NEXT_PUBLIC_DEMO_MODE === 'true' ? (
        <Link href={`/${locale}`} className="w-full">
          <Button variant="outline" className="w-full gap-2" type="button">
            <Play className="w-4 h-4" />
            {t('tryDemo')}
          </Button>
        </Link>
      ) : (
        <Link
          href={`/${locale}`}
          className="text-center text-[13px] text-muted-foreground hover:text-foreground underline underline-offset-4"
        >
          {t('continueAsGuest')}
        </Link>
      )}
    </>
  );
}

function LoginCard() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { refreshUser } = useAuth();
  const locale = useLocale();
  const t = useTranslations('auth.login');
  const tErrors = useTranslations('auth.errors');
  const tAuth = useTranslations('auth');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsLoading(true);
    setError(null);

    const data = new FormData(event.currentTarget);
    const email = (data.get('email') || '').toString().trim();
    const password = (data.get('password') || '').toString();

    try {
      await login(email, password);
      // Refresh user context
      await refreshUser();

      // Redirect to the page user was trying to access, or home
      const redirectTo = searchParams.get('redirect') || `/${locale}`;
      router.push(redirectTo);
    } catch (err) {
      const message = err instanceof Error ? err.message : tErrors('loginFailed');
      setError(message);
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <AuthCard>
      <AuthHeading title={t('title')} description={t('description')} />
      <OAuthButtons isLoading={isLoading} />
      <Suspense
        fallback={
          <div className="flex justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        }
      >
        <LoginForm isLoading={isLoading} error={error} onSubmit={onSubmit} />
      </Suspense>
      <AuthLinks>
        <Link
          href={`/${locale}/auth/register`}
          data-testid="auth-register-link"
          className="font-medium text-foreground underline underline-offset-4 hover:text-primary"
        >
          {t('signUp')}
        </Link>
      </AuthLinks>
      <AuthNote>{tAuth('note')}</AuthNote>
    </AuthCard>
  );
}

export default function LoginPage() {
  return <LoginCard />;
}
