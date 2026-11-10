'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useLocale, useTranslations } from 'next-intl';
import { Loader2, ArrowLeft } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { AuthCard, AuthField, AuthHeading, AuthLinks, AuthNote, AuthStatus } from '@/components/auth/auth-shell';
import { useCapabilities } from '@/hooks/useCapabilities';
import { forgotPassword } from '@/lib/auth';

export default function ForgotPasswordPage() {
  const t = useTranslations('auth');
  const locale = useLocale();
  const { capabilities } = useCapabilities();
  const [isLoading, setIsLoading] = useState(false);
  const [email, setEmail] = useState('');
  const [isSuccess, setIsSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // The deployment that cannot send mail cannot promise a mail. The
  // capabilities endpoint knows, so the line under the heading follows it
  // instead of the build flag.
  const emailEnabled = capabilities?.email.enabled ?? true;
  const demoMode = process.env.NEXT_PUBLIC_DEMO_MODE === 'true';
  // In demo mode the mail never leaves the API: the console mail provider
  // prints it, link and all, into the API log. A deployment without a mail
  // service says the same thing.
  const mailNote = demoMode ? t('forgotPassword.demoNote') : t('forgotPassword.noMailNote');

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsLoading(true);
    setError(null);

    try {
      await forgotPassword(email);
      setIsSuccess(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : t('errors.resetEmailFailed'));
    } finally {
      setIsLoading(false);
    }
  }

  if (isSuccess) {
    return (
      <AuthCard>
        <AuthHeading title={t('forgotPassword.checkEmail')} />
        {/* The success line tells the truth: a deployment without a mail
            service did not mail anything, and the link is in the API log. */}
        <AuthStatus tone={emailEnabled && !demoMode ? 'success' : 'warning'}>
          {emailEnabled && !demoMode
            ? t('forgotPassword.resetSent')
            : demoMode
              ? t('forgotPassword.demoNote')
              : t('forgotPassword.resetSentNoMail')}
        </AuthStatus>
        {emailEnabled && !demoMode && (
          <p className="text-sm text-muted-foreground">{t('forgotPassword.checkInbox')}</p>
        )}
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
        <AuthLinks>
          <Link
            href={`/${locale}/auth/login`}
            className="font-medium text-foreground underline underline-offset-4 hover:text-primary"
          >
            {t('forgotPassword.backToLogin')}
          </Link>
        </AuthLinks>
        <AuthNote>{t('note')}</AuthNote>
      </AuthCard>
    );
  }

  return (
    <AuthCard>
      <AuthHeading
        title={t('forgotPassword.title')}
        description={t('forgotPassword.description')}
      />
      {(!emailEnabled || demoMode) && <AuthStatus tone="warning">{mailNote}</AuthStatus>}
      <form onSubmit={onSubmit} className="flex flex-col gap-3">
        {error && (
          <div className="rounded-md bg-destructive/15 p-3 text-sm text-destructive" role="alert">
            {error}
          </div>
        )}
        <AuthField label={t('forgotPassword.emailLabel')} htmlFor="email">
          <Input
            id="email"
            name="email"
            type="email"
            placeholder={t('login.emailPlaceholder')}
            required
            disabled={isLoading}
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
        </AuthField>
        <Button className="mt-1 h-[42px] w-full" type="submit" disabled={isLoading || !email}>
          {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
          {t('forgotPassword.submit')}
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
