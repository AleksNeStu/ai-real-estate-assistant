'use client';

import { Suspense, useState } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { useTranslations, useLocale } from 'next-intl';
import { Building2, Loader2, AlertCircle, Play } from 'lucide-react';

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
import { OAuthButtons } from '@/components/auth/OAuthButtons';
import { login } from '@/lib/auth';
import { useAuth } from '@/hooks/useAuth';

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { refreshUser } = useAuth();
  const locale = useLocale();
  const t = useTranslations('auth.login');
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
      const message = err instanceof Error ? err.message : 'Login failed';
      setError(message);
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <form onSubmit={onSubmit}>
      <CardContent className="grid gap-4">
        {error && (
          <div
            className="flex items-center gap-2 rounded-md bg-destructive/15 p-3 text-sm text-destructive"
            role="alert"
          >
            <AlertCircle className="h-4 w-4" aria-hidden="true" />
            <span>{error}</span>
          </div>
        )}
        <div className="grid gap-2">
          <Label htmlFor="email">{t('emailLabel')}</Label>
          <Input
            id="email"
            name="email"
            type="email"
            placeholder={t('emailPlaceholder')}
            required
            disabled={isLoading}
          />
        </div>
        <div className="grid gap-2">
          <div className="flex items-center justify-between">
            <Label htmlFor="password">{t('passwordLabel')}</Label>
            <Link
              href={`/${locale}/auth/forgot-password`}
              className="text-xs text-primary hover:underline"
            >
              {t('forgotPassword')}
            </Link>
          </div>
          <Input id="password" name="password" type="password" required disabled={isLoading} />
        </div>
      </CardContent>
      <CardFooter className="flex flex-col gap-4">
        <Button className="w-full" type="submit" disabled={isLoading}>
          {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
          {t('submit')}
        </Button>

        <OAuthButtons isLoading={isLoading} />

        <div className="text-sm text-center text-muted-foreground">
          {t('noAccount')}{' '}
          <Link
            href={`/${locale}/auth/register`}
            className="underline underline-offset-4 hover:text-primary"
          >
            {t('signUp')}
          </Link>
        </div>

        <div className="relative my-2">
          <div className="absolute inset-0 flex items-center">
            <span className="w-full border-t" />
          </div>
          <div className="relative flex justify-center text-xs uppercase">
            <span className="bg-card px-2 text-muted-foreground">{t('or')}</span>
          </div>
        </div>

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
            className="text-sm text-center text-muted-foreground hover:text-primary underline underline-offset-4"
          >
            {t('continueAsGuest')}
          </Link>
        )}
      </CardFooter>
    </form>
  );
}

function LoginCard() {
  const t = useTranslations('auth.login');

  return (
    <Card className="w-full">
      <CardHeader className="space-y-1 text-center">
        <div className="flex justify-center mb-2">
          <div className="rounded-full bg-primary/10 p-3">
            <Building2 className="h-6 w-6 text-primary" aria-hidden="true" />
          </div>
        </div>
        <CardTitle className="text-2xl">{t('title')}</CardTitle>
        <CardDescription>{t('description')}</CardDescription>
      </CardHeader>
      <Suspense
        fallback={
          <CardContent className="flex justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </CardContent>
        }
      >
        <LoginForm />
      </Suspense>
    </Card>
  );
}

export default function LoginPage() {
  return <LoginCard />;
}
