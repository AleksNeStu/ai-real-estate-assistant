'use client';

import { useState } from 'react';
import Link from 'next/link';
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
import { forgotPassword } from '@/lib/auth';

export default function ForgotPasswordPage() {
  const t = useTranslations('auth');
  const [isLoading, setIsLoading] = useState(false);
  const [email, setEmail] = useState('');
  const [isSuccess, setIsSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsLoading(true);
    setError(null);

    try {
      await forgotPassword(email);
      setIsSuccess(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to send reset email');
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
              <CheckCircle2
                className="h-6 w-6 text-success dark:text-success"
                aria-hidden="true"
              />
            </div>
          </div>
          <CardTitle className="text-2xl">{t('forgotPassword.checkEmail')}</CardTitle>
          <CardDescription>{t('forgotPassword.resetSent')}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-center text-muted-foreground">
            {t('forgotPassword.checkInbox')}
          </p>
        </CardContent>
        <CardFooter className="flex flex-col gap-4">
          <Button
            className="w-full"
            variant="outline"
            onClick={() => {
              setIsSuccess(false);
              setEmail('');
            }}
          >
            {t('forgotPassword.resend')}
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
        <CardTitle className="text-2xl">{t('forgotPassword.title')}</CardTitle>
        <CardDescription>{t('forgotPassword.description')}</CardDescription>
      </CardHeader>
      <form onSubmit={onSubmit}>
        <CardContent className="grid gap-4">
          {error && (
            <div className="rounded-md bg-destructive/15 p-3 text-sm text-destructive" role="alert">
              {error}
            </div>
          )}
          <div className="grid gap-2">
            <Label htmlFor="email">{t('forgotPassword.emailLabel')}</Label>
            <Input
              id="email"
              name="email"
              type="email"
              placeholder="name@example.com"
              required
              disabled={isLoading}
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>
        </CardContent>
        <CardFooter className="flex flex-col gap-4">
          <Button className="w-full" type="submit" disabled={isLoading || !email}>
            {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            {t('forgotPassword.submit')}
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
