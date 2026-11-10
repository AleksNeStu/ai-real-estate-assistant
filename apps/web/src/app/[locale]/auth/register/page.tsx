'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useLocale, useTranslations } from 'next-intl';
import { Loader2, AlertCircle } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { AuthCard, AuthField, AuthHeading, AuthLinks, AuthNote } from '@/components/auth/auth-shell';
import { OAuthButtons } from '@/components/auth/OAuthButtons';
import { register } from '@/lib/auth';
import { useAuth } from '@/hooks/useAuth';

export default function RegisterPage() {
  const router = useRouter();
  const locale = useLocale();
  const t = useTranslations('auth');
  // The example name and the example address are shared labels of the
  // catalogue — they are read from there instead of being written out again.
  const tContactForm = useTranslations('agents.contactForm');
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
    const consentGiven = data.get('consent') === 'on';

    // The consent is what the backend writes `gdpr_consent_at` from, so a
    // form without it would create an account with no record of it. The box
    // is required in the markup too - this check is the belt to that braces.
    if (!consentGiven) {
      setError(t('register.consentRequired'));
      setIsLoading(false);
      return;
    }

    try {
      await register(email, password, fullName, consentGiven);
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
    <AuthCard>
      <AuthHeading title={t('register.title')} description={t('register.description')} />
      <OAuthButtons isLoading={isLoading} />
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
        <AuthField label={t('register.fullNameLabel')} htmlFor="fullName">
          <Input
            id="fullName"
            name="fullName"
            placeholder={tContactForm('namePlaceholder')}
            disabled={isLoading}
          />
        </AuthField>
        <AuthField label={t('register.emailLabel')} htmlFor="email">
          <Input
            id="email"
            name="email"
            type="email"
            placeholder={t('login.emailPlaceholder')}
            required
            disabled={isLoading}
          />
        </AuthField>
        <AuthField
          label={t('register.passwordLabel')}
          htmlFor="password"
          hint={t('resetPassword.passwordHint')}
        >
          <Input
            id="password"
            name="password"
            type="password"
            required
            disabled={isLoading}
            minLength={8}
          />
        </AuthField>
        <div className="flex items-start gap-2.5">
          <input
            id="consent"
            name="consent"
            type="checkbox"
            required
            disabled={isLoading}
            className="mt-0.5 size-4 shrink-0 accent-[hsl(var(--action))]"
          />
          <Label htmlFor="consent" className="text-[13px] leading-5 text-muted-foreground">
            {t('register.consentLabel')}
          </Label>
        </div>
        <Button className="mt-1 h-[42px] w-full" type="submit" disabled={isLoading}>
          {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
          {t('register.submit')}
        </Button>
      </form>
      <AuthLinks>
        <Link
          href={`/${locale}/auth/login`}
          data-testid="auth-login-link"
          className="font-medium text-foreground underline underline-offset-4 hover:text-primary"
        >
          {t('register.haveAccount')}
        </Link>
        <Link
          href={`/${locale}`}
          className="text-muted-foreground underline underline-offset-4 hover:text-foreground"
        >
          {t('demo.exploreDemoFirst')}
        </Link>
      </AuthLinks>
      <AuthNote>{t('note')}</AuthNote>
    </AuthCard>
  );
}
