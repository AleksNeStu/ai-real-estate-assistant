'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useLocale, useTranslations } from 'next-intl';
import { Building2, Loader2, AlertCircle } from 'lucide-react';

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
import { register } from '@/lib/auth';
import { useAuth } from '@/hooks/useAuth';

export default function RegisterPage() {
  const router = useRouter();
  const locale = useLocale();
  const t = useTranslations('auth');
  const { refreshUser } = useAuth();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsLoading(true);
    setError(null);

    const data = new FormData(event.currentTarget);
    const fullName = (data.get('fullName') || '').toString().trim();
    const email = (data.get('email') || '').toString().trim();
    const password = (data.get('password') || '').toString();

    try {
      await register(email, password, fullName);
      // Refresh user context
      await refreshUser();

      // Redirect to home page
      router.push('/');
    } catch (err) {
      const message = err instanceof Error ? err.message : t('errors.registerFailed');
      setError(message);
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <Card className="w-full">
      <CardHeader className="space-y-1 text-center">
        <div className="flex justify-center mb-2">
          <div className="rounded-full bg-primary/10 p-3">
            <Building2 className="h-6 w-6 text-primary" aria-hidden="true" />
          </div>
        </div>
        <CardTitle className="text-2xl">{t('register.title')}</CardTitle>
        <CardDescription>{t('register.description')}</CardDescription>
      </CardHeader>
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
            <Label htmlFor="fullName">{t('register.fullNameLabel')}</Label>
            <Input id="fullName" name="fullName" placeholder="John Doe" disabled={isLoading} />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="email">{t('register.emailLabel')}</Label>
            <Input
              id="email"
              name="email"
              type="email"
              placeholder="name@example.com"
              required
              disabled={isLoading}
            />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="password">{t('register.passwordLabel')}</Label>
            <Input
              id="password"
              name="password"
              type="password"
              placeholder={t('resetPassword.passwordHint')}
              required
              disabled={isLoading}
              minLength={8}
            />
          </div>
        </CardContent>
        <CardFooter className="flex flex-col gap-4">
          <Button className="w-full" type="submit" disabled={isLoading}>
            {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            {t('register.submit')}
          </Button>

          <OAuthButtons isLoading={isLoading} />

          <div className="text-sm text-center text-muted-foreground">
            {t('register.haveAccount')}{' '}
            <Link
              href={`/${locale}/auth/login`}
              className="underline underline-offset-4 hover:text-primary"
            >
              {t('login.submit')}
            </Link>
          </div>

          <div className="relative my-2">
            <div className="absolute inset-0 flex items-center">
              <span className="w-full border-t" />
            </div>
            <div className="relative flex justify-center text-xs uppercase">
              <span className="bg-card px-2 text-muted-foreground">{t('login.or')}</span>
            </div>
          </div>

          <Link
            href={`/${locale}`}
            className="text-sm text-center text-muted-foreground hover:text-primary underline underline-offset-4"
          >
            Explore demo first
          </Link>
        </CardFooter>
      </form>
    </Card>
  );
}
