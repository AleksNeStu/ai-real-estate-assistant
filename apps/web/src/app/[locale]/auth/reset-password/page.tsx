'use client';

import { Suspense, useState, useEffect } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { useTranslations } from 'next-intl';
import { Building2, Loader2, ArrowLeft, CheckCircle2 } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { resetPassword } from '@/lib/auth';

function ResetPasswordForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
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
      <Card className="w-full">
        <CardHeader className="space-y-1 text-center">
          <div className="flex justify-center mb-2">
            <div className="rounded-full bg-success/15 dark:bg-success/20 p-3">
              <CheckCircle2 className="h-6 w-6 text-success dark:text-success" aria-hidden="true" />
            </div>
          </div>
          <CardTitle className="text-2xl">{t('resetPassword.title')}</CardTitle>
          <CardDescription>{t('resetPassword.success')}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-center text-muted-foreground">{t('resetPassword.canLogin')}</p>
        </CardContent>
        <CardFooter className="flex flex-col gap-4">
          <Button className="w-full" onClick={() => router.push('/auth/login')}>
            {t('resetPassword.goToLogin')}
          </Button>
        </CardFooter>
      </Card>
    );
  }

  return (
    <Card className="w-full">
      <CardHeader className="space-y-1 text-center">
        <div className="flex justify-center mb-2">
          <div className="rounded-full bg-primary/10 p-3">
            <Building2 className="h-6 w-6 text-primary" aria-hidden="true" />
          </div>
        </div>
        <CardTitle className="text-2xl">{t('resetPassword.title')}</CardTitle>
        <CardDescription>{t('resetPassword.description')}</CardDescription>
      </CardHeader>
      <form onSubmit={onSubmit}>
        <CardContent className="grid gap-4">
          {error && (
            <div className="rounded-md bg-destructive/15 p-3 text-sm text-destructive" role="alert">
              {error}
            </div>
          )}
          <div className="grid gap-2">
            <Label htmlFor="password">{t('resetPassword.newPasswordLabel')}</Label>
            <Input
              id="password"
              type="password"
              required
              disabled={isLoading || !token}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder={t('resetPassword.passwordHint')}
            />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="confirmPassword">{t('resetPassword.confirmPasswordLabel')}</Label>
            <Input
              id="confirmPassword"
              type="password"
              required
              disabled={isLoading || !token}
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder={t('resetPassword.confirmHint')}
            />
          </div>
        </CardContent>
        <CardFooter className="flex flex-col gap-4">
          <Button
            className="w-full"
            type="submit"
            disabled={isLoading || !token || !password || !confirmPassword}
          >
            {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            {t('resetPassword.submit')}
          </Button>
          <div className="text-sm text-center text-muted-foreground">
            <Link
              href="/auth/login"
              className="inline-flex items-center gap-1 text-primary hover:underline"
            >
              <ArrowLeft className="h-3 w-3" aria-hidden="true" />
              {t('forgotPassword.backToLogin')}
            </Link>
          </div>
        </CardFooter>
      </form>
    </Card>
  );
}

export default function ResetPasswordPage() {
  return (
    <Suspense
      fallback={
        <Card className="w-full">
          <CardContent className="flex justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </CardContent>
        </Card>
      }
    >
      <ResetPasswordForm />
    </Suspense>
  );
}
