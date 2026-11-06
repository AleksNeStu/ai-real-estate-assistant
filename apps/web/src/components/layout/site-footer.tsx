'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';
import { AlertCircle, CheckCircle2, Loader2, Mail } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { getOrCreateVisitorId } from '@/lib/visitor-tracking';

type SubmitState = 'idle' | 'loading' | 'success' | 'error';

/**
 * Site-wide lead capture surface.
 *
 * Posts the visitor's email to the public `POST /api/v1/leads/visitor`
 * endpoint, which creates (or updates) the visitor lead and feeds the lead
 * scoring pipeline. Tracking must never break the page, so every failure is
 * reported in the UI instead of thrown.
 */
export function SiteFooter() {
  const t = useTranslations('footer');
  const [email, setEmail] = useState('');
  const [state, setState] = useState<SubmitState>('idle');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    const trimmedEmail = email.trim();
    if (!trimmedEmail) {
      setState('error');
      setErrorMessage(t('errorInvalidEmail'));
      return;
    }

    setState('loading');
    setErrorMessage(null);

    try {
      const response = await fetch('/api/v1/leads/visitor', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          visitor_id: getOrCreateVisitorId(),
          email: trimmedEmail,
          source: 'organic',
          consent_given: true,
        }),
      });

      if (!response.ok) {
        throw new Error(`lead capture failed with status ${response.status}`);
      }

      setState('success');
      setEmail('');
    } catch {
      setState('error');
      setErrorMessage(t('errorGeneric'));
    }
  };

  return (
    <footer className="border-t bg-background" aria-labelledby="site-footer-heading">
      <div className="container mx-auto px-4 py-10">
        <div className="mx-auto max-w-xl text-center">
          <h2 id="site-footer-heading" className="text-xl font-semibold">
            {t('title')}
          </h2>
          <p className="mt-2 text-sm text-muted-foreground">{t('description')}</p>

          {state === 'success' ? (
            <p
              className="mt-6 flex items-center justify-center gap-2 text-sm font-medium text-green-600"
              role="status"
            >
              <CheckCircle2 className="h-4 w-4" aria-hidden="true" />
              {t('success')}
            </p>
          ) : (
            <form onSubmit={handleSubmit} className="mt-6" noValidate>
              <div className="flex flex-col gap-2 sm:flex-row sm:items-start">
                <div className="flex-1 text-left">
                  <label htmlFor="site-footer-email" className="sr-only">
                    {t('emailLabel')}
                  </label>
                  <div className="relative">
                    <Mail
                      className="pointer-events-none absolute left-3 top-3 h-4 w-4 text-muted-foreground"
                      aria-hidden="true"
                    />
                    <Input
                      id="site-footer-email"
                      name="email"
                      type="email"
                      autoComplete="email"
                      required
                      value={email}
                      onChange={(event) => setEmail(event.target.value)}
                      placeholder={t('emailPlaceholder')}
                      aria-label={t('emailLabel')}
                      aria-invalid={state === 'error' ? 'true' : undefined}
                      className="pl-9"
                      disabled={state === 'loading'}
                    />
                  </div>
                </div>
                <Button type="submit" disabled={state === 'loading'} className="sm:mt-0">
                  {state === 'loading' ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />
                      {t('submitting')}
                    </>
                  ) : (
                    t('submit')
                  )}
                </Button>
              </div>

              {state === 'error' && errorMessage && (
                <p
                  className="mt-3 flex items-center justify-center gap-2 text-sm text-destructive"
                  role="alert"
                >
                  <AlertCircle className="h-4 w-4" aria-hidden="true" />
                  {errorMessage}
                </p>
              )}

              <p className="mt-3 text-xs text-muted-foreground">{t('consent')}</p>
            </form>
          )}
        </div>
      </div>
    </footer>
  );
}
